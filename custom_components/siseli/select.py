"""Select controls for enumerated inverter configuration settings."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SiseliConfigEntry
from .config_entity import SiseliConfigEntity, normalized_config_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up selectable inverter configuration settings."""
    coordinator = entry.runtime_data.config_coordinator
    if coordinator is None:
        return
    async_add_entities(
        SiseliConfigSelect(coordinator, spec)
        for spec in coordinator.specs
        if spec.kind.value == "enum"
        and dict(spec.options) != {"0": "Disable", "1": "Enable"}
    )


class SiseliConfigSelect(SiseliConfigEntity, SelectEntity):
    """Represent an enumerated inverter setting."""

    _attr_icon = "mdi:form-dropdown"

    @property
    def options(self) -> list[str]:
        """Return the human-readable options from the SDK specification."""
        return list(self.spec.options.values())

    @property
    def current_option(self) -> str | None:
        """Return the label for the last confirmed wire value."""
        value = normalized_config_value(self.raw_value)
        return self.spec.options.get(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Write the selected option's wire value."""
        wire_value = next(
            value for value, label in self.spec.options.items() if label == option
        )
        await self.async_write_value(wire_value)
