"""Tests for the Siseli DataUpdateCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.siseli.const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.siseli.coordinator import SiseliCoordinator

from .conftest import (
    DEFAULT_DATA,
    MOCK_PASSWORD,
    MOCK_USERNAME,
    SiseliAuthError,
    SiseliConnectionError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(hass: HomeAssistant, options: dict | None = None) -> ConfigEntry:
    """Create a minimal ConfigEntry for testing."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options=options or {},
        source=SOURCE_USER,
        entry_id="coordinator_test_id",
        unique_id=MOCK_USERNAME,
        discovery_keys={},
    )
    return entry


def _make_coordinator(hass: HomeAssistant, options: dict | None = None) -> tuple[SiseliCoordinator, MagicMock]:
    """Create a coordinator with a mocked SiseliClient."""
    entry = _make_entry(hass, options)
    mock_client = MagicMock()
    mock_client.get_data = AsyncMock(return_value=DEFAULT_DATA.copy())
    with patch("custom_components.siseli.coordinator.SiseliClient", return_value=mock_client):
        coordinator = SiseliCoordinator(hass, entry)
    return coordinator, mock_client


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


async def test_coordinator_uses_default_scan_interval(hass: HomeAssistant) -> None:
    """Coordinator uses DEFAULT_SCAN_INTERVAL when no options are set."""
    coordinator, _ = _make_coordinator(hass)
    assert coordinator.update_interval.total_seconds() == DEFAULT_SCAN_INTERVAL


async def test_coordinator_uses_options_scan_interval(hass: HomeAssistant) -> None:
    """Coordinator uses the interval from entry.options when available."""
    coordinator, _ = _make_coordinator(hass, options={CONF_SCAN_INTERVAL: 120})
    assert coordinator.update_interval.total_seconds() == 120


# ---------------------------------------------------------------------------
# Successful update
# ---------------------------------------------------------------------------


async def test_async_update_data_success(hass: HomeAssistant) -> None:
    """Successful update returns the data dict and resets failure counter."""
    coordinator, mock_client = _make_coordinator(hass)
    coordinator._consecutive_failures = 3  # simulate prior failures

    data = await coordinator._async_update_data()

    assert data == DEFAULT_DATA
    assert coordinator._consecutive_failures == 0


# ---------------------------------------------------------------------------
# Auth failure
# ---------------------------------------------------------------------------


async def test_async_update_data_auth_failure(hass: HomeAssistant) -> None:
    """SiseliAuthError raises ConfigEntryAuthFailed."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_data.side_effect = SiseliAuthError("token expired")

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Connection failure and consecutive failure counter
# ---------------------------------------------------------------------------


async def test_async_update_data_connection_failure(hass: HomeAssistant) -> None:
    """SiseliConnectionError raises UpdateFailed."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_data.side_effect = SiseliConnectionError("timeout")

    with pytest.raises(UpdateFailed, match="Error communicating with Siseli API"):
        await coordinator._async_update_data()


async def test_consecutive_failures_increment(hass: HomeAssistant) -> None:
    """Consecutive failures are tracked correctly."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_data.side_effect = SiseliConnectionError("timeout")

    for expected in range(1, 4):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._consecutive_failures == expected


async def test_failure_counter_resets_on_success(hass: HomeAssistant) -> None:
    """Failure counter resets to 0 after a successful update."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_data.side_effect = SiseliConnectionError("timeout")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 1

    mock_client.get_data.side_effect = None
    mock_client.get_data.return_value = DEFAULT_DATA.copy()
    data = await coordinator._async_update_data()
    assert data == DEFAULT_DATA
    assert coordinator._consecutive_failures == 0
