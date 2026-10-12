"""Switch controls for two-state inverter configuration settings."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SiseliConfigEntry
from .config_entity import SiseliConfigEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up safe two-state configuration switches."""
    coordinator = entry.runtime_data.config_coordinator
    if coordinator is None:
        return
    async_add_entities(
        SiseliConfigSwitch(coordinator, spec)
        for spec in coordinator.specs
        if spec.kind.value == "enum"
        and dict(spec.options) == {"0": "Disable", "1": "Enable"}
    )


class SiseliConfigSwitch(SiseliConfigEntity, SwitchEntity):
    """Represent a boolean inverter setting."""

    _attr_icon = "mdi:cog"

    @property
    def is_on(self) -> bool | None:
        """Return whether the inverter setting is enabled."""
        value = self.raw_value
        if value is None:
            return None
        if str(value) == "1":
            return True
        if str(value) == "0":
            return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the inverter setting."""
        await self.async_write_value("1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the inverter setting."""
        await self.async_write_value("0")
