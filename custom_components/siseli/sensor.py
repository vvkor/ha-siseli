"""Sensor platform for the Siseli integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SiseliConfigEntry
from .const import DOMAIN
from .coordinator import SiseliCoordinator


class SiseliSensorEntityDescription(SensorEntityDescription):
    """Describes a Siseli sensor entity."""


SENSORS: tuple[SiseliSensorEntityDescription, ...] = (
    SiseliSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SiseliSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="battery_current",
        translation_key="battery_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    SiseliSensorEntityDescription(
        key="battery_power",
        translation_key="battery_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="pv_voltage",
        translation_key="pv_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="pv_current",
        translation_key="pv_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    SiseliSensorEntityDescription(
        key="pv_power",
        translation_key="pv_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SiseliSensorEntityDescription(
        key="output_voltage",
        translation_key="output_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SiseliSensorEntityDescription(
        key="output_frequency",
        translation_key="output_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SiseliSensorEntityDescription(
        key="load_power",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    SiseliSensorEntityDescription(
        key="inverter_state",
        translation_key="inverter_state",
    ),
    SiseliSensorEntityDescription(
        key="inverter_mode",
        translation_key="inverter_mode",
    ),
    SiseliSensorEntityDescription(
        key="pv_generated_energy_total",
        translation_key="pv_generated_energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    SiseliSensorEntityDescription(
        key="load_percent",
        translation_key="load_percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SiseliSensorEntityDescription(
        key="load_apparent_power",
        translation_key="load_apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SiseliSensorEntityDescription(
        key="heat_sink_temperature",
        translation_key="heat_sink_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SiseliSensorEntityDescription(
        key="bus_voltage",
        translation_key="bus_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
) + tuple(
    SiseliSensorEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for key in (
        "charging_status",
        "scc_charging_status",
        "ac_charging_status",
        "mains_status",
        "load_status",
        "charger_source_priority",
        "output_source_priority",
        "battery_type",
    )
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

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info, enriched with model/firmware once known."""
        info = self.coordinator.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="Siseli Inverter",
            manufacturer="Siseli",
            model=info.get("machine_type"),
            sw_version=info.get("firmware_version"),
        )

    @property
    def native_value(self) -> Any:
        """Return the normalized semantic value provided by python-siseli."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.key)
