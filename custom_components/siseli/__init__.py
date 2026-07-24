"""The Siseli integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SiseliCoordinator

type SiseliConfigEntry = ConfigEntry[SiseliCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Set up Siseli from a config entry."""
    coordinator = SiseliCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Unload a Siseli config entry."""
    return True
