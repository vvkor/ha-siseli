"""Tests for the Siseli DataUpdateCoordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry
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
    AuthenticationError,
    NetworkError,
    _Device,
    _DeviceState,
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
    mock_client.get_all_devices = AsyncMock(return_value=[_Device("device-001")])
    mock_client.get_device_state = AsyncMock(return_value=_DeviceState(DEFAULT_DATA.copy()))
    coordinator = SiseliCoordinator(hass, entry)
    coordinator.client = mock_client
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
    coordinator, _ = _make_coordinator(hass)
    coordinator._consecutive_failures = 3  # simulate prior failures

    data = await coordinator._async_update_data()

    assert data == DEFAULT_DATA
    assert coordinator._consecutive_failures == 0


async def test_async_update_data_fetches_device_id_once(hass: HomeAssistant) -> None:
    """get_all_devices is called only on the first update."""
    coordinator, mock_client = _make_coordinator(hass)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    mock_client.get_all_devices.assert_called_once()
    assert mock_client.get_device_state.call_count == 2


async def test_async_update_data_creates_client_in_executor(
    hass: HomeAssistant,
) -> None:
    """Client is created via executor job when missing."""
    coordinator, mock_client = _make_coordinator(hass)
    coordinator.client = None
    hass.async_add_executor_job = AsyncMock(return_value=mock_client)

    await coordinator._async_update_data()

    hass.async_add_executor_job.assert_awaited_once()
    assert coordinator.client is mock_client


async def test_async_update_data_no_devices(hass: HomeAssistant) -> None:
    """UpdateFailed is raised when no devices are found."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_all_devices.return_value = []

    with pytest.raises(UpdateFailed, match="No devices found"):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Auth failure
# ---------------------------------------------------------------------------


async def test_async_update_data_auth_failure(hass: HomeAssistant) -> None:
    """AuthenticationError raises ConfigEntryAuthFailed."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_all_devices.side_effect = AuthenticationError("token expired")

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Connection failure and consecutive failure counter
# ---------------------------------------------------------------------------


async def test_async_update_data_connection_failure(hass: HomeAssistant) -> None:
    """NetworkError raises UpdateFailed."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_all_devices.side_effect = NetworkError("timeout")

    with pytest.raises(UpdateFailed, match="Error communicating with Siseli API"):
        await coordinator._async_update_data()


async def test_consecutive_failures_increment(hass: HomeAssistant) -> None:
    """Consecutive failures are tracked correctly."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_all_devices.side_effect = NetworkError("timeout")

    for expected in range(1, 4):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._consecutive_failures == expected


async def test_failure_counter_resets_on_success(hass: HomeAssistant) -> None:
    """Failure counter resets to 0 after a successful update."""
    coordinator, mock_client = _make_coordinator(hass)
    mock_client.get_all_devices.side_effect = NetworkError("timeout")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 1

    mock_client.get_all_devices.side_effect = None
    data = await coordinator._async_update_data()
    assert data == DEFAULT_DATA
    assert coordinator._consecutive_failures == 0
