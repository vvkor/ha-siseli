"""Tests for the Siseli sensor entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
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
    """There should be exactly 14 sensor descriptors."""
    assert len(SENSORS) == 14


# ---------------------------------------------------------------------------
# Entity value mapping
# ---------------------------------------------------------------------------


async def test_native_value_returns_coordinator_data(hass: HomeAssistant) -> None:
    """native_value returns the matching value from coordinator.data."""
    coordinator = _make_coordinator_with_data(hass)

    for desc in SENSORS:
        entity = SiseliSensorEntity(coordinator, desc)
        expected = DEFAULT_DATA.get(desc.key)
        assert entity.native_value == expected, (
            f"Sensor {desc.key}: expected {expected}, got {entity.native_value}"
        )


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
