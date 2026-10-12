"""Shared entity behavior for inverter configuration controls."""

from __future__ import annotations

from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from siseli import ConfigSpec

from .config_coordinator import SiseliConfigCoordinator
from .const import DOMAIN


class SiseliConfigEntity(CoordinatorEntity[SiseliConfigCoordinator]):
    """Base class for editable inverter configuration entities."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SiseliConfigCoordinator, spec: ConfigSpec
    ) -> None:
        """Initialize a configuration entity."""
        super().__init__(coordinator)
        self.spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{spec.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared inverter device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Siseli Inverter",
            manufacturer="Siseli",
        )

    @property
    def raw_value(self) -> Any:
        """Return the last confirmed value from the configuration coordinator."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.spec.key)

    async def async_write_value(self, value: Any) -> None:
        """Write a value through the guarded SDK API."""
        await self.coordinator.async_write(self.spec.key, value)


def normalized_config_value(value: Any) -> str | None:
    """Convert wire values to the string representation used by enum options."""
    if value is None:
        return None
    return str(value)
