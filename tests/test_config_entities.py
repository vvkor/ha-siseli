"""Tests for inverter configuration controls and guarded writes."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

from custom_components.siseli.config_coordinator import (
    CONFIG_REFRESH_INTERVAL,
    SiseliConfigCoordinator,
)
from custom_components.siseli.const import (
    CONF_BATTERY_NOMINAL_VOLTAGE,
    CONF_CONFIG_ACCESS,
    DOMAIN,
)
from custom_components.siseli.coordinator import SiseliCoordinator
from custom_components.siseli.number import SiseliConfigNumber, async_setup_entry as setup_numbers
from custom_components.siseli.select import (
    SiseliConfigSelect,
    async_setup_entry as setup_selects,
)
from custom_components.siseli.switch import (
    SiseliConfigSwitch,
    async_setup_entry as setup_switches,
)

from .conftest import (
    _CONFIG_DEFAULTS,
    _CONFIG_SPECS,
    _ConfigAccess,
    _ConfigAccessDenied,
    _ApiError,
    _ConfigRejected,
    _NetworkError,
    _ConfigValidationError,
    _ConfigWriteResult,
    _ConfigWriteStatus,
    AuthenticationError,
    MOCK_PASSWORD,
    MOCK_USERNAME,
)


def _make_config_coordinator(
    hass: HomeAssistant,
    mock_siseli_client,
    access: str = "safe",
    voltage: int = 12,
) -> tuple[ConfigEntry, SiseliCoordinator, SiseliConfigCoordinator]:
    """Build telemetry and config coordinators around a test client."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={
            CONF_CONFIG_ACCESS: access,
            CONF_BATTERY_NOMINAL_VOLTAGE: voltage,
        },
        source=SOURCE_USER,
        entry_id="config_test_id",
        unique_id=MOCK_USERNAME,
        discovery_keys={},
    )
    telemetry = SiseliCoordinator(hass, entry)
    telemetry.client = mock_siseli_client
    telemetry._device_id = "device-001"
    config = SiseliConfigCoordinator(hass, entry, telemetry, access, voltage)
    telemetry.config_coordinator = config
    entry.runtime_data = telemetry
    config.data = dict(_CONFIG_DEFAULTS)
    return entry, telemetry, config


async def _setup_entities(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, list]:
    """Run platform setup and collect created entities."""
    entities: dict[str, list] = {"switch": [], "select": [], "number": []}
    await setup_switches(hass, entry, entities["switch"].extend)
    await setup_selects(hass, entry, entities["select"].extend)
    await setup_numbers(hass, entry, entities["number"].extend)
    return entities


async def test_disabled_access_creates_no_configuration_entities(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Disabled access exposes no writable configuration entities."""
    entry, telemetry, _ = _make_config_coordinator(
        hass, mock_siseli_client, access="safe"
    )
    telemetry.config_coordinator = None

    entities = await _setup_entities(hass, entry)

    assert entities == {"switch": [], "select": [], "number": []}


@pytest.mark.parametrize(
    ("access", "expected_count"),
    [("safe", 5), ("advanced", 13), ("critical", len(_CONFIG_SPECS))],
)
async def test_entity_set_matches_access_level(
    hass: HomeAssistant, mock_siseli_client, access: str, expected_count: int
) -> None:
    """Only settings at or below the configured risk tier become entities."""
    entry, _, config = _make_config_coordinator(
        hass, mock_siseli_client, access=access
    )

    entities = await _setup_entities(hass, entry)
    all_entities = sum(entities.values(), [])

    assert len(all_entities) == expected_count
    assert all(entity.entity_category is EntityCategory.CONFIG for entity in all_entities)
    assert all(
        spec.risk <= config.access
        for entity in all_entities
        for spec in (entity.spec,)
    )
    if access == "safe":
        assert len(entities["switch"]) == 5
        assert not entities["select"] and not entities["number"]


def test_configuration_translations_match_sdk_specs() -> None:
    """Every SDK setting has a platform translation in both English files."""
    base = Path(__file__).parents[1] / "custom_components" / "siseli"
    switches = {
        key
        for key, spec in _CONFIG_SPECS.items()
        if spec.kind.value == "enum"
        and spec.options == {"0": "Disable", "1": "Enable"}
    }
    selects = {
        key
        for key, spec in _CONFIG_SPECS.items()
        if spec.kind.value == "enum" and key not in switches
    }
    numbers = {
        key for key, spec in _CONFIG_SPECS.items() if spec.kind.value == "number"
    }

    for filename in ("strings.json", "translations/en.json"):
        translations = json.loads((base / filename).read_text(encoding="utf-8"))
        entity_translations = translations["entity"]
        assert set(entity_translations["switch"]) == switches
        assert set(entity_translations["select"]) == selects
        assert set(entity_translations["number"]) == numbers


async def test_config_refresh_is_separate_slow_and_never_writes(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Initial configuration refresh reads values without issuing writes."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)

    data = await coordinator._async_update_data()

    assert coordinator.update_interval == CONFIG_REFRESH_INTERVAL
    assert data["buzzerEnabled"] == "0"
    mock_siseli_client.get_cached_device_configs.assert_awaited_once()
    mock_siseli_client.get_device_config.assert_not_awaited()
    mock_siseli_client.safe_set_device_config.assert_not_awaited()


async def test_config_refresh_omits_keys_missing_from_cache(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Keys absent from the cache are omitted without extra remote reads."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    full = await mock_siseli_client.get_cached_device_configs("device-001")
    full.pop("buzzerEnabled")
    mock_siseli_client.get_cached_device_configs.side_effect = None
    mock_siseli_client.get_cached_device_configs.return_value = full

    data = await coordinator._async_update_data()

    assert "buzzerEnabled" not in data
    mock_siseli_client.get_device_config.assert_not_awaited()


async def test_switch_write_uses_sdk_and_updates_confirmed_value(
    hass: HomeAssistant, mock_siseli_client, caplog: pytest.LogCaptureFixture
) -> None:
    """A switch submits a wire enum and takes state from the SDK read-back."""
    entry, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    spec = _CONFIG_SPECS["buzzerEnabled"]
    entity = SiseliConfigSwitch(coordinator, spec)
    mock_siseli_client.safe_set_device_config.side_effect = None
    mock_siseli_client.safe_set_device_config.return_value = _ConfigWriteResult(
        spec.key,
        _ConfigWriteStatus.APPLIED,
        "1",
        "0",
        "1",
    )
    caplog.set_level(logging.INFO)

    await entity.async_turn_on()

    mock_siseli_client.safe_set_device_config.assert_awaited_once_with(
        "device-001",
        key=spec.key,
        value="1",
        access=_ConfigAccess.SAFE,
        battery_nominal_voltage=12,
    )
    assert coordinator.data[spec.key] == "1"
    assert entity.is_on is True
    assert "key=buzzerEnabled old='0' new='1' status=applied" in caplog.text


async def test_select_write_uses_sdk_wire_value(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Select labels are mapped back to their exact wire values."""
    _, _, coordinator = _make_config_coordinator(
        hass, mock_siseli_client, access="advanced"
    )
    spec = _CONFIG_SPECS["settingDeviceOutputSourcePriority"]
    entity = SiseliConfigSelect(coordinator, spec)
    mock_siseli_client.safe_set_device_config.side_effect = None
    mock_siseli_client.safe_set_device_config.return_value = _ConfigWriteResult(
        spec.key,
        _ConfigWriteStatus.APPLIED,
        "1",
        "0",
        "1",
    )

    await entity.async_select_option("Solar first")

    mock_siseli_client.safe_set_device_config.assert_awaited_once()
    assert mock_siseli_client.safe_set_device_config.await_args.kwargs["value"] == "1"
    assert entity.current_option == "Solar first"


async def test_number_write_and_battery_scaling(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Voltage number limits scale by nominal battery voltage and writes stay numeric."""
    _, _, coordinator = _make_config_coordinator(
        hass, mock_siseli_client, access="critical", voltage=48
    )
    spec = _CONFIG_SPECS["setBatteryCutOffVoltage"]
    entity = SiseliConfigNumber(coordinator, spec)
    mock_siseli_client.safe_set_device_config.side_effect = None
    mock_siseli_client.safe_set_device_config.return_value = _ConfigWriteResult(
        spec.key,
        _ConfigWriteStatus.APPLIED,
        46.0,
        40.0,
        46.0,
    )

    assert entity.native_min_value == pytest.approx(40)
    assert entity.native_max_value == pytest.approx(50)
    assert entity.native_step == pytest.approx(0.4)
    await entity.async_set_native_value(46.0)

    assert mock_siseli_client.safe_set_device_config.await_args.kwargs["value"] == 46.0
    assert coordinator.data[spec.key] == 46.0


async def test_unknown_write_surfaces_home_assistant_error_without_assuming_state(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """An unknown outcome is reported and does not update the displayed value."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    original = coordinator.data["buzzerEnabled"]
    mock_siseli_client.safe_set_device_config.side_effect = None
    mock_siseli_client.safe_set_device_config.return_value = _ConfigWriteResult(
        "buzzerEnabled",
        _ConfigWriteStatus.UNKNOWN,
        "1",
        "0",
        None,
    )
    with patch.object(
        coordinator, "async_request_refresh", new=AsyncMock()
    ) as refresh:
        with pytest.raises(HomeAssistantError, match="result is unknown"):
            await coordinator.async_write("buzzerEnabled", "1")
        await hass.async_block_till_done()

    assert coordinator.data["buzzerEnabled"] == original
    coordinator.client.safe_set_device_config.assert_awaited_once()
    refresh.assert_awaited_once()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (_ConfigValidationError("sensitive validation payload"), "Invalid value"),
        (_ConfigAccessDenied("sensitive access payload"), "Writes are not enabled"),
        (_ConfigRejected(20210, "sensitive rejection payload"), "rejected this"),
        (_NetworkError("sensitive network payload"), "Could not communicate"),
        (_ApiError("sensitive api payload"), "Could not communicate"),
    ],
)
async def test_sdk_write_errors_surface_as_short_home_assistant_errors(
    hass: HomeAssistant,
    mock_siseli_client,
    error: Exception,
    message: str,
) -> None:
    """SDK validation/access/rejection details are not exposed to Home Assistant."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    mock_siseli_client.safe_set_device_config.side_effect = error

    with pytest.raises(HomeAssistantError, match=message) as exc_info:
        await coordinator.async_write("buzzerEnabled", "1")

    assert "sensitive" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__
    assert mock_siseli_client.safe_set_device_config.await_count == 1


async def test_authentication_error_triggers_reauthentication(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Authentication failures from configuration writes request reauth."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    mock_siseli_client.safe_set_device_config.side_effect = AuthenticationError(
        "expired token"
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_write("buzzerEnabled", "1")

    assert mock_siseli_client.safe_set_device_config.await_count == 1


async def test_writes_are_serialized_per_entry(
    hass: HomeAssistant, mock_siseli_client
) -> None:
    """Only one safe SDK write for this entry can be active at a time."""
    _, _, coordinator = _make_config_coordinator(hass, mock_siseli_client)
    active_writes = 0
    max_active_writes = 0

    async def safe_write(device_id, *, key, value, **kwargs):
        nonlocal active_writes, max_active_writes
        active_writes += 1
        max_active_writes = max(max_active_writes, active_writes)
        await asyncio.sleep(0)
        active_writes -= 1
        return _ConfigWriteResult(
            key,
            _ConfigWriteStatus.APPLIED,
            value,
            _CONFIG_DEFAULTS[key],
            value,
        )

    mock_siseli_client.safe_set_device_config.side_effect = safe_write

    await asyncio.gather(
        coordinator.async_write("buzzerEnabled", "1"),
        coordinator.async_write("lcdBackLightControlSetting", "1"),
    )

    assert max_active_writes == 1
