"""The Siseli integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .config_coordinator import SiseliConfigCoordinator
from .const import (
    CONF_BATTERY_NOMINAL_VOLTAGE,
    CONF_CONFIG_ACCESS,
    DEFAULT_BATTERY_NOMINAL_VOLTAGE,
    DEFAULT_CONFIG_ACCESS,
)
from .coordinator import SiseliCoordinator

type SiseliConfigEntry = ConfigEntry[SiseliCoordinator]

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Set up Siseli from a config entry."""
    coordinator = SiseliCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    access = entry.options.get(CONF_CONFIG_ACCESS, DEFAULT_CONFIG_ACCESS)
    if access != DEFAULT_CONFIG_ACCESS:
        config_coordinator = SiseliConfigCoordinator(
            hass,
            entry,
            coordinator,
            access,
            entry.options.get(
                CONF_BATTERY_NOMINAL_VOLTAGE, DEFAULT_BATTERY_NOMINAL_VOLTAGE
            ),
        )
        coordinator.config_coordinator = config_coordinator
    else:
        coordinator.config_coordinator = None
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if coordinator.config_coordinator is not None:
        hass.async_create_task(coordinator.config_coordinator.async_refresh())
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Unload a Siseli config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: SiseliConfigEntry) -> None:
    """Reload integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
