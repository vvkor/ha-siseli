"""Tests for the inverter online indicator and stale-value handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.siseli.const import (
    CONF_CONFIG_ACCESS,
    DOMAIN,
    OFFLINE_API_CODE,
    STALE_AFTER,
)
from custom_components.siseli.coordinator import SiseliCoordinator

from .conftest import (
    DEFAULT_DATA,
    MOCK_PASSWORD,
    MOCK_USERNAME,
    NetworkError,
    _ApiError,
    _Device,
    _DeviceState,
)

ONLINE = "binary_sensor.siseli_inverter_online"
VOLTAGE = "sensor.siseli_inverter_battery_voltage"
LAST_DATA = "sensor.siseli_inverter_last_data_received"
BUZZER = "switch.siseli_inverter_buzzer"


def _entry(options: dict | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_USERNAME,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options=options or {},
    )


def _coordinator(hass: HomeAssistant) -> tuple[SiseliCoordinator, MagicMock]:
    client = MagicMock()
    client.get_all_devices = AsyncMock(return_value=[_Device("device-001")])
    client.get_device_state = AsyncMock(return_value=_DeviceState(DEFAULT_DATA.copy()))
    client.get_device = AsyncMock(return_value=_Device("device-001"))
    client.get_device_energy_totals = AsyncMock(return_value={})
    coordinator = SiseliCoordinator(hass, _entry())
    coordinator.client = client
    return coordinator, client


def _stale_state() -> _DeviceState:
    old = dt_util.utcnow() - STALE_AFTER - timedelta(minutes=1)
    return _DeviceState(DEFAULT_DATA.copy(), time=old)


async def _poll(hass: HomeAssistant) -> None:
    """Run the next scheduled coordinator refresh."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()


# ---------------------------------------------------------------------------
# Coordinator logic
# ---------------------------------------------------------------------------


async def test_online_when_cloud_flag_and_snapshot_are_fresh(hass: HomeAssistant) -> None:
    """A fresh snapshot and an online flag mean the inverter is online."""
    coordinator, _ = _coordinator(hass)

    data = await coordinator._async_update_data()

    assert coordinator.device_online is True
    assert coordinator.last_online_at == datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    assert data["last_data_received"] == DEFAULT_DATA["last_data_received"]


async def test_offline_when_cloud_flags_the_device_offline(hass: HomeAssistant) -> None:
    """The cloud's own flag wins even when the last snapshot is recent."""
    coordinator, client = _coordinator(hass)
    client.get_device.return_value = _Device("device-001", is_online=False)

    await coordinator._async_update_data()

    assert coordinator.device_online is False


async def test_offline_when_snapshot_is_stale(hass: HomeAssistant) -> None:
    """Old telemetry is not shown as current even if the cloud has not noticed yet."""
    coordinator, client = _coordinator(hass)
    client.get_device_state.return_value = _stale_state()

    await coordinator._async_update_data()

    assert coordinator.device_online is False


async def test_missing_cloud_flag_is_not_treated_as_offline(hass: HomeAssistant) -> None:
    """The SDK defaults a missing isOnline to False; that must not mean offline."""
    coordinator, client = _coordinator(hass)
    device = _Device("device-001", is_online=False)
    device.raw = {}
    client.get_device.return_value = device

    await coordinator._async_update_data()

    assert coordinator.device_online is True


async def test_device_status_failure_falls_back_to_the_snapshot(hass: HomeAssistant) -> None:
    """If only the device record cannot be read, telemetry freshness decides."""
    coordinator, client = _coordinator(hass)
    client.get_device.side_effect = _ApiError("boom", code=1)

    await coordinator._async_update_data()

    assert coordinator.device_online is True


async def test_device_offline_error_marks_offline(hass: HomeAssistant) -> None:
    """The cloud's "Device is offline" error is a known offline state."""
    coordinator, client = _coordinator(hass)
    client.get_device_state.side_effect = _ApiError(
        "Device is offline", code=OFFLINE_API_CODE
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.device_online is False


async def test_network_error_leaves_connectivity_unknown(hass: HomeAssistant) -> None:
    """Without cloud access nothing is known about the inverter."""
    coordinator, client = _coordinator(hass)
    await coordinator._async_update_data()
    client.get_device_state.side_effect = NetworkError("down")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator.device_online is None


async def test_returning_online_refreshes_configuration(hass: HomeAssistant) -> None:
    """A stale-then-fresh transition refreshes configuration like an API outage does."""
    coordinator, client = _coordinator(hass)
    config = MagicMock()
    config.async_request_refresh = AsyncMock()
    coordinator.config_coordinator = config
    client.get_device_state.return_value = _stale_state()
    await coordinator._async_update_data()
    client.get_device_state.return_value = _DeviceState(DEFAULT_DATA.copy())

    await coordinator._async_update_data()
    await hass.async_block_till_done()

    config.async_request_refresh.assert_awaited_once()
    assert config.async_update_listeners.call_count == 2


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = _entry(options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_online_indicator_and_values_while_online(
    hass: HomeAssistant, patched_client
) -> None:
    """An online inverter shows on, with live values and timestamps."""
    await _setup(hass)

    online = hass.states.get(ONLINE)
    assert online.state == "on"
    assert online.attributes["device_class"] == "connectivity"
    assert online.attributes["last_online"] == "2026-11-21T12:00:00+00:00"
    assert hass.states.get(VOLTAGE).state == "52.1"
    assert hass.states.get(LAST_DATA).state != "unavailable"


async def test_values_become_unavailable_when_the_cloud_flags_offline(
    hass: HomeAssistant, patched_client
) -> None:
    """Stale values are hidden, the indicator turns off and the timestamp remains."""
    await _setup(hass, {CONF_CONFIG_ACCESS: "safe"})
    assert hass.states.get(BUZZER).state == "off"

    patched_client.get_device.return_value = _Device("device-001", is_online=False)
    await _poll(hass)

    assert hass.states.get(ONLINE).state == "off"
    assert hass.states.get(VOLTAGE).state == "unavailable"
    assert hass.states.get(BUZZER).state == "unavailable"
    assert hass.states.get(LAST_DATA).state != "unavailable"

    patched_client.get_device.return_value = _Device("device-001")
    await _poll(hass)

    assert hass.states.get(ONLINE).state == "on"
    assert hass.states.get(VOLTAGE).state == "52.1"
    assert hass.states.get(BUZZER).state == "off"


async def test_values_become_unavailable_when_telemetry_goes_stale(
    hass: HomeAssistant, patched_client
) -> None:
    """The cloud keeps serving the last snapshot of a powered-off inverter."""
    await _setup(hass)

    patched_client.get_device_state.return_value = _stale_state()
    await _poll(hass)

    assert hass.states.get(ONLINE).state == "off"
    assert hass.states.get(VOLTAGE).state == "unavailable"


async def test_offline_error_turns_the_indicator_off_not_unavailable(
    hass: HomeAssistant, patched_client
) -> None:
    """"Device is offline" is a definite answer, so the indicator reads off."""
    await _setup(hass)

    patched_client.get_device_state.side_effect = _ApiError(
        "Device is offline", code=OFFLINE_API_CODE
    )
    await _poll(hass)

    assert hass.states.get(ONLINE).state == "off"
    assert hass.states.get(VOLTAGE).state == "unavailable"
    assert hass.states.get(LAST_DATA).state != "unavailable"


async def test_indicator_is_unavailable_when_the_cloud_is_unreachable(
    hass: HomeAssistant, patched_client
) -> None:
    """With no cloud access the connectivity of the inverter is unknown."""
    await _setup(hass)

    patched_client.get_device_state.side_effect = NetworkError("down")
    await _poll(hass)

    assert hass.states.get(ONLINE).state == "unavailable"
