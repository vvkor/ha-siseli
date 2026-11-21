"""Binary sensor for the inverter's connectivity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SiseliConfigEntry
from .coordinator import SiseliCoordinator
from .device import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the online indicator."""
    async_add_entities([SiseliOnlineBinarySensor(entry.runtime_data)])


class SiseliOnlineBinarySensor(CoordinatorEntity[SiseliCoordinator], BinarySensorEntity):
    """Whether the inverter is currently reporting to the Siseli cloud."""

    _attr_has_entity_name = True
    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: SiseliCoordinator) -> None:
        """Initialise the online indicator."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_online"

    @property
    def available(self) -> bool:
        """Report "off" for an offline inverter; only unknown connectivity is unavailable."""
        return self.coordinator.device_online is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the inverter is online."""
        return self.coordinator.device_online

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return when the cloud last heard from the inverter."""
        data = self.coordinator.data or {}
        last_data = data.get("last_data_received")
        last_online = self.coordinator.last_online_at
        return {
            "last_data_received": last_data.isoformat() if last_data else None,
            "last_online": last_online.isoformat() if last_online else None,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared inverter device."""
        return build_device_info(self.coordinator)
