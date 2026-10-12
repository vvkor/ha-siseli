"""Tests for the Siseli sensor entities."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry, SOURCE_USER
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    EntityCategory,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant

from custom_components.siseli.const import DOMAIN
from custom_components.siseli.coordinator import SiseliCoordinator
from custom_components.siseli.sensor import SENSORS, SiseliSensorEntity

from .conftest import DEFAULT_DATA, MOCK_PASSWORD, MOCK_USERNAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator_with_data(
    hass: HomeAssistant, data: dict | None = None
) -> SiseliCoordinator:
    """Return a coordinator pre-loaded with data."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={},
        source=SOURCE_USER,
        entry_id="sensor_test_id",
        unique_id=MOCK_USERNAME,
        discovery_keys={},
    )
    mock_client = MagicMock()
    mock_client.get_data = AsyncMock(return_value=(data or DEFAULT_DATA).copy())
    with patch("custom_components.siseli.coordinator.SiseliClient", return_value=mock_client):
        coordinator = SiseliCoordinator(hass, entry)
    coordinator.data = data if data is not None else DEFAULT_DATA.copy()
    return coordinator


# ---------------------------------------------------------------------------
# Entity descriptor checks
# ---------------------------------------------------------------------------


def test_sensor_descriptors_have_keys() -> None:
    """All sensor descriptors must define a key."""
    for desc in SENSORS:
        assert desc.key, f"Sensor descriptor missing key: {desc}"


def test_sensor_descriptors_have_translation_keys() -> None:
    """All sensor descriptors must define a translation_key."""
    for desc in SENSORS:
        assert desc.translation_key, f"Sensor descriptor missing translation_key: {desc}"


def test_sensor_descriptor_count() -> None:
    """The descriptor set covers all normalized SDK fields plus lifetime energy."""
    assert len(SENSORS) == 27
    assert {desc.key for desc in SENSORS} == set(DEFAULT_DATA)


def test_pv_generated_energy_is_energy_dashboard_compatible() -> None:
    """Lifetime PV energy exposes kWh and total_increasing metadata."""
    desc = next(d for d in SENSORS if d.key == "pv_generated_energy_total")
    assert desc.device_class == SensorDeviceClass.ENERGY
    assert desc.state_class == SensorStateClass.TOTAL_INCREASING
    assert desc.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR


def test_inverter_state_entity_key_is_stable() -> None:
    """The raw state sensor keeps its key; the readable mode is a new sensor."""
    keys = {desc.key for desc in SENSORS}
    assert {"inverter_state", "inverter_mode"} <= keys


def test_rated_apparent_power_is_not_labelled_as_live_load() -> None:
    """ratedApparentPower is a rating, so it must not look like live apparent power."""
    desc = next(d for d in SENSORS if d.key == "load_apparent_power")
    assert desc.entity_category == EntityCategory.DIAGNOSTIC
    translations = json.loads(
        (Path(__file__).parents[1] / "custom_components/siseli/strings.json").read_text(
            encoding="utf-8"
        )
    )
    assert "Rated" in translations["entity"]["sensor"]["load_apparent_power"]["name"]


def test_translations_match_descriptors() -> None:
    """strings.json and en.json list exactly the sensor descriptors."""
    base = Path(__file__).parents[1] / "custom_components/siseli"
    expected = {desc.translation_key for desc in SENSORS}
    for name in ("strings.json", "translations/en.json"):
        data = json.loads((base / name).read_text(encoding="utf-8"))
        assert set(data["entity"]["sensor"]) == expected, name


# ---------------------------------------------------------------------------
# Entity value mapping
# ---------------------------------------------------------------------------


async def test_native_value_maps_api_fields_and_units(hass: HomeAssistant) -> None:
    """Sensor values map real API fields and convert kW to W."""
    coordinator = _make_coordinator_with_data(hass)
    expected_values = {
        "battery_soc": 85.0,
        "battery_voltage": 52.1,
        "battery_current": 10.5,
        "battery_power": 547.05,
        "pv_voltage": 380.0,
        "pv_current": 3.2,
        "pv_power": 1216.0,
        "grid_voltage": 230.0,
        "grid_frequency": 50.0,
        "output_voltage": 230.0,
        "output_frequency": 50.0,
        "load_power": 420.0,
        **{k: v for k, v in DEFAULT_DATA.items() if k not in (
            "battery_soc", "battery_voltage", "battery_current", "battery_power",
            "pv_voltage", "pv_current", "pv_power", "grid_voltage", "grid_frequency",
            "output_voltage", "output_frequency", "load_power",
        )},
    }

    for desc in SENSORS:
        entity = SiseliSensorEntity(coordinator, desc)
        expected = expected_values[desc.key]
        actual = entity.native_value
        if isinstance(expected, float):
            assert actual == pytest.approx(expected), (
                f"Sensor {desc.key}: expected {expected}, got {actual}"
            )
        else:
            assert actual == expected, (
                f"Sensor {desc.key}: expected {expected}, got {actual}"
            )


async def test_battery_current_is_negative_when_discharging(hass: HomeAssistant) -> None:
    """Battery current uses positive for charging and negative for discharging."""
    data = DEFAULT_DATA.copy()
    data["battery_current"] = -4.2
    data["battery_power"] = -52.1 * 4.2
    coordinator = _make_coordinator_with_data(hass, data=data)

    entity = SiseliSensorEntity(
        coordinator, next(desc for desc in SENSORS if desc.key == "battery_current")
    )
    assert entity.native_value == pytest.approx(-4.2)

    power = SiseliSensorEntity(
        coordinator, next(desc for desc in SENSORS if desc.key == "battery_power")
    )
    assert power.native_value == pytest.approx(-52.1 * 4.2)


async def test_derived_battery_values_return_none_when_inputs_missing(hass: HomeAssistant) -> None:
    """Derived battery sensors do not invent values when source fields are absent."""
    coordinator = _make_coordinator_with_data(
        hass, data={"battery_voltage": 12.8}
    )
    for key in ("battery_current", "battery_power"):
        entity = SiseliSensorEntity(
            coordinator, next(desc for desc in SENSORS if desc.key == key)
        )
        assert entity.native_value is None


async def test_native_value_none_when_no_data(hass: HomeAssistant) -> None:
    """native_value returns None when coordinator.data is None."""
    coordinator = _make_coordinator_with_data(hass)
    coordinator.data = None

    for desc in SENSORS:
        entity = SiseliSensorEntity(coordinator, desc)
        assert entity.native_value is None, f"Expected None for {desc.key}"


async def test_native_value_none_for_missing_key(hass: HomeAssistant) -> None:
    """native_value returns None when key is absent from data."""
    coordinator = _make_coordinator_with_data(hass, data={})

    for desc in SENSORS:
        entity = SiseliSensorEntity(coordinator, desc)
        assert entity.native_value is None, f"Expected None for missing key {desc.key}"


# ---------------------------------------------------------------------------
# Unique ID and device info
# ---------------------------------------------------------------------------


async def test_unique_id_format(hass: HomeAssistant) -> None:
    """unique_id is constructed from entry_id and sensor key."""
    coordinator = _make_coordinator_with_data(hass)

    for desc in SENSORS:
        entity = SiseliSensorEntity(coordinator, desc)
        expected = f"{coordinator.config_entry.entry_id}_{desc.key}"
        assert entity.unique_id == expected


async def test_device_info_identifiers(hass: HomeAssistant) -> None:
    """Device info contains the expected domain/entry_id identifier."""
    coordinator = _make_coordinator_with_data(hass)
    entity = SiseliSensorEntity(coordinator, SENSORS[0])
    identifiers = entity.device_info["identifiers"]
    assert (DOMAIN, coordinator.config_entry.entry_id) in identifiers


async def test_device_info_uses_model_and_firmware(hass: HomeAssistant) -> None:
    """Model and firmware come from the SDK device info; identifiers stay stable."""
    coordinator = _make_coordinator_with_data(hass)
    coordinator.device_info = {
        "machine_type": "SLP-5K",
        "firmware_version": "1.2.3",
    }
    info = SiseliSensorEntity(coordinator, SENSORS[0]).device_info
    assert info["model"] == "SLP-5K"
    assert info["sw_version"] == "1.2.3"
    assert (DOMAIN, coordinator.config_entry.entry_id) in info["identifiers"]


async def test_device_info_without_identification(hass: HomeAssistant) -> None:
    """Before identification is known, model/firmware are simply unset."""
    coordinator = _make_coordinator_with_data(hass)
    info = SiseliSensorEntity(coordinator, SENSORS[0]).device_info
    assert info["model"] is None
    assert info["sw_version"] is None
