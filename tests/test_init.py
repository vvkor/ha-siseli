"""Tests for integration setup, unload and options reload."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.siseli.const import CONF_CONFIG_ACCESS, DOMAIN

from .conftest import MOCK_PASSWORD, MOCK_USERNAME


def _entry(options: dict | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_USERNAME,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options=options or {},
    )


@pytest.fixture
def patched_client(mock_siseli_client):
    """Make the coordinator use the mocked SDK client."""
    with patch(
        "custom_components.siseli.coordinator.SiseliClient",
        return_value=mock_siseli_client,
    ):
        yield mock_siseli_client


async def test_setup_without_configuration_access(
    hass: HomeAssistant, patched_client
) -> None:
    """Telemetry sensors load and no configuration coordinator is created."""
    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.config_coordinator is None
    assert hass.states.get("sensor.siseli_inverter_battery_voltage") is not None
    assert hass.states.async_entity_ids("switch") == []
    patched_client.get_cached_device_configs.assert_not_awaited()


async def test_setup_with_configuration_access_loads_controls(
    hass: HomeAssistant, patched_client
) -> None:
    """Configuration entities are created and filled by the background refresh."""
    entry = _entry({CONF_CONFIG_ACCESS: "safe"})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.config_coordinator is not None
    state = hass.states.get("switch.siseli_inverter_buzzer")
    assert state is not None
    assert state.state == "off"


async def test_unload_entry(hass: HomeAssistant, patched_client) -> None:
    """The entry unloads cleanly."""
    entry = _entry({CONF_CONFIG_ACCESS: "safe"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_options_update_reloads_entry(
    hass: HomeAssistant, patched_client
) -> None:
    """Changing options reloads the integration with the new access level."""
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(entry, options={CONF_CONFIG_ACCESS: "safe"})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.config_coordinator is not None
    assert hass.states.get("switch.siseli_inverter_buzzer") is not None


async def test_deprecated_apparent_power_unique_id_is_migrated(
    hass: HomeAssistant, patched_client
) -> None:
    """The renamed telemetry key keeps its entity ID and history."""
    entry = _entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_load_apparent_power",
        config_entry=entry,
        suggested_object_id="siseli_inverter_rated_apparent_power",
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    migrated = registry.async_get(old.entity_id)
    assert migrated is not None
    assert migrated.unique_id == f"{entry.entry_id}_rated_apparent_power"
    assert registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_load_apparent_power"
    ) is None
    assert hass.states.get(old.entity_id).state == "5000.0"
