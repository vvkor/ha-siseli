"""The Siseli integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .config_coordinator import SiseliConfigCoordinator
from .const import (
    CONF_BATTERY_NOMINAL_VOLTAGE,
    CONF_CONFIG_ACCESS,
    DEFAULT_BATTERY_NOMINAL_VOLTAGE,
    DEFAULT_CONFIG_ACCESS,
    DOMAIN,
)
from .coordinator import SiseliCoordinator

type SiseliConfigEntry = ConfigEntry[SiseliCoordinator]

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


# python-siseli 0.3.0 deprecates the ``load_apparent_power`` telemetry key (it is the
# *rated* value) in favour of ``rated_apparent_power``.
_RENAMED_SENSOR_KEYS = {"load_apparent_power": "rated_apparent_power"}


@callback
def _async_migrate_unique_id(
    entry: ConfigEntry, entity_entry: er.RegistryEntry
) -> dict[str, str] | None:
    """Move entities from deprecated telemetry keys to their replacements."""
    for old, new in _RENAMED_SENSOR_KEYS.items():
        if entity_entry.unique_id == f"{entry.entry_id}_{old}":
            return {"new_unique_id": f"{entry.entry_id}_{new}"}
    return None


async def async_setup_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Set up Siseli from a config entry."""
    await er.async_migrate_entries(
        hass, entry.entry_id, lambda entity_entry: _async_migrate_unique_id(entry, entity_entry)
    )
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
        # Configuration values are slow and optional; never delay entity setup.
        entry.async_create_background_task(
            hass,
            coordinator.config_coordinator.async_refresh(),
            f"{DOMAIN} initial configuration refresh",
        )
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SiseliConfigEntry) -> bool:
    """Unload a Siseli config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: SiseliConfigEntry) -> None:
    """Reload integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
