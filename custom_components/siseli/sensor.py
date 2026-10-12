"""Sensor platform for the Siseli integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SiseliConfigEntry
from .const import DOMAIN
from .coordinator import SiseliCoordinator


@dataclass(frozen=True, kw_only=True)
class SiseliSensorEntityDescription(SensorEntityDescription):
    """Describes a Siseli sensor entity."""

    api_key: str | None = None
    multiplier: float = 1.0
    derived_value: str | None = None


SENSORS: tuple[SiseliSensorEntityDescription, ...] = (
    SiseliSensorEntityDescription(
        key="battery_soc",
        api_key="batteryCapacity",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SiseliSensorEntityDescription(
        key="battery_voltage",
        api_key="batteryVoltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="battery_current",
        derived_value="battery_current",
        translation_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    SiseliSensorEntityDescription(
        key="battery_power",
        derived_value="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="pv_voltage",
        api_key="pvInputVoltage1",
        translation_key="pv_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="pv_current",
        api_key="pv1InputCurrentForBattery",
        translation_key="pv_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    SiseliSensorEntityDescription(
        key="pv_power",
        api_key="generationPower",
        multiplier=1000,
        translation_key="pv_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="grid_voltage",
        api_key="gridVoltage",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="grid_frequency",
        api_key="gridFrequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SiseliSensorEntityDescription(
        key="output_voltage",
        api_key="acOutputVoltage",
        translation_key="output_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="output_frequency",
        api_key="acOutputFrequency",
        translation_key="output_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SiseliSensorEntityDescription(
        key="load_power",
        api_key="acOutputActivePower",
        multiplier=1000,
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="inverter_state",
        api_key="workingMode",
        translation_key="inverter_state",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Siseli sensor entities from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        SiseliSensorEntity(coordinator, description) for description in SENSORS
    )


class SiseliSensorEntity(CoordinatorEntity[SiseliCoordinator], SensorEntity):
    """Represents a Siseli sensor entity."""

    _attr_has_entity_name = True
    entity_description: SiseliSensorEntityDescription

    def __init__(
        self,
        coordinator: SiseliCoordinator,
        description: SiseliSensorEntityDescription,
    ) -> None:
        """Initialise the sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        # Keep existing unique IDs stable while mapping them to the API's field names.
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Siseli Inverter",
            manufacturer="Siseli",
        )

    @property
    def native_value(self) -> Any:
        """Return a mapped or derived value from coordinator data."""
        data = self.coordinator.data
        if data is None:
            return None

        description = self.entity_description
        if description.derived_value == "battery_current":
            charging = _number(data.get("batteryChargingCurrent"))
            discharging = _number(data.get("batteryDischargeCurrent"))
            if charging is None or discharging is None:
                return None
            # Positive means charging; negative means discharging.
            return charging - discharging

        if description.derived_value == "battery_power":
            voltage = _number(data.get("batteryVoltage"))
            charging = _number(data.get("batteryChargingCurrent"))
            discharging = _number(data.get("batteryDischargeCurrent"))
            if voltage is None or charging is None or discharging is None:
                return None
            return voltage * (charging - discharging)

        if description.api_key is None:
            return None
        value = data.get(description.api_key)
        if value is None:
            return None
        number = _number(value)
        if number is not None:
            return number * description.multiplier
        return value


def _number(value: Any) -> float | None:
    """Convert a numeric API value to float, preserving missing values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
