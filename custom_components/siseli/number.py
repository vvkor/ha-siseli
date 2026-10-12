"""Number controls for numeric inverter configuration settings."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from siseli import ConfigSpec

from . import SiseliConfigEntry
from .config_coordinator import SiseliConfigCoordinator
from .config_entity import SiseliConfigEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up numeric inverter configuration settings."""
    coordinator = entry.runtime_data.config_coordinator
    if coordinator is None:
        return
    async_add_entities(
        SiseliConfigNumber(coordinator, spec)
        for spec in coordinator.specs
        if spec.kind.value == "number"
    )


class SiseliConfigNumber(SiseliConfigEntity, NumberEntity):
    """Represent a numeric inverter setting."""

    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:knob"

    def __init__(
        self, coordinator: SiseliConfigCoordinator, spec: ConfigSpec
    ) -> None:
        """Initialize a number entity with battery-scaled limits when required."""
        super().__init__(coordinator, spec)
        scale = coordinator.battery_nominal_voltage / 12 if spec.scales_with_battery else 1
        assert spec.minimum is not None
        assert spec.maximum is not None
        assert spec.step is not None
        self._attr_native_min_value = spec.minimum * scale
        self._attr_native_max_value = spec.maximum * scale
        self._attr_native_step = spec.step * scale
        self._attr_native_unit_of_measurement = spec.unit

    @property
    def native_value(self) -> float | None:
        """Return the last confirmed numeric value."""
        value = self.raw_value
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write the requested numeric setting."""
        await self.async_write_value(value)
