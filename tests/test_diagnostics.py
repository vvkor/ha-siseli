"""Tests for the Siseli diagnostics endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.siseli.const import DOMAIN
from custom_components.siseli.coordinator import SiseliCoordinator
from custom_components.siseli.diagnostics import async_get_config_entry_diagnostics

from .conftest import DEFAULT_DATA, MOCK_PASSWORD, MOCK_USERNAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry_with_coordinator(hass: HomeAssistant) -> ConfigEntry:
    """Create a config entry with a mocked coordinator attached."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={"scan_interval": 60},
        source=SOURCE_USER,
        entry_id="diag_test_id",
        unique_id=MOCK_USERNAME,
        discovery_keys={},
    )
    mock_client = MagicMock()
    mock_client.get_data = AsyncMock(return_value=DEFAULT_DATA.copy())
    with patch("custom_components.siseli.coordinator.SiseliClient", return_value=mock_client):
        coordinator = SiseliCoordinator(hass, entry)
    coordinator.data = DEFAULT_DATA.copy()
    coordinator._consecutive_failures = 0
    entry.runtime_data = coordinator
    return entry


# ---------------------------------------------------------------------------
# Diagnostics content
# ---------------------------------------------------------------------------


async def test_diagnostics_structure(hass: HomeAssistant) -> None:
    """Diagnostics output has the expected top-level keys."""
    entry = _make_entry_with_coordinator(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert "entry" in diag
    assert "coordinator" in diag
    assert "data" in diag


async def test_diagnostics_redacts_username(hass: HomeAssistant) -> None:
    """Username is redacted in diagnostics output."""
    entry = _make_entry_with_coordinator(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    entry_data = diag["entry"]["data"]
    assert entry_data.get("username") != MOCK_USERNAME, (
        "Username must be redacted in diagnostics"
    )


async def test_diagnostics_redacts_password(hass: HomeAssistant) -> None:
    """Password is redacted in diagnostics output."""
    entry = _make_entry_with_coordinator(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    entry_data = diag["entry"]["data"]
    assert entry_data.get("password") != MOCK_PASSWORD, (
        "Password must be redacted in diagnostics"
    )


async def test_diagnostics_coordinator_state(hass: HomeAssistant) -> None:
    """Coordinator state fields are present in diagnostics."""
    entry = _make_entry_with_coordinator(hass)
    entry.runtime_data.last_update_success = True
    entry.runtime_data._consecutive_failures = 2

    diag = await async_get_config_entry_diagnostics(hass, entry)
    coord_diag = diag["coordinator"]

    assert coord_diag["last_update_success"] is True
    assert coord_diag["consecutive_failures"] == 2


async def test_diagnostics_data_is_included(hass: HomeAssistant) -> None:
    """The most recent coordinator data is included in diagnostics."""
    entry = _make_entry_with_coordinator(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["data"] == DEFAULT_DATA


async def test_diagnostics_options_included(hass: HomeAssistant) -> None:
    """Entry options are included in diagnostics."""
    entry = _make_entry_with_coordinator(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["entry"]["options"] == {"scan_interval": 60}
