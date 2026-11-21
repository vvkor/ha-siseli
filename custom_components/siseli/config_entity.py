"""Shared entity behavior for inverter configuration controls."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from siseli import ConfigSpec

from .config_coordinator import SiseliConfigCoordinator
from .device import build_device_info

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def translation_key_for(spec_key: str) -> str:
    """Return the Home Assistant translation key for an SDK setting key.

    Home Assistant only allows ``[a-z0-9_-]`` in translation keys, while the SDK
    uses the API's camelCase names. Unique IDs keep using the SDK key.
    """
    return _CAMEL_BOUNDARY.sub("_", spec_key).lower()


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
        self._attr_translation_key = translation_key_for(spec.key)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{spec.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared inverter device."""
        return build_device_info(self.coordinator.telemetry_coordinator)

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
