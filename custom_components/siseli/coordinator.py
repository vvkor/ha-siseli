"""DataUpdateCoordinator for the Siseli integration."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import datetime, timedelta
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from siseli import AuthenticationError, NetworkError, SiseliClient
from siseli.open_auth import attach_open_auth

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Lifetime counters change slowly, so they are fetched far less often than live state.
ENERGY_TOTALS_INTERVAL = timedelta(minutes=15)
PV_GENERATED_ENERGY_KEY = "pvGeneratedEnergy"


class SiseliCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches data from the Siseli cloud via python-siseli."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )
        creds = entry.data
        self._account = creds[CONF_USERNAME]
        self._password = creds[CONF_PASSWORD]
        # Created lazily in _async_update_data to avoid blocking SSL setup on the event loop.
        self.client: SiseliClient | None = None
        self._client_lock = Lock()
        self._consecutive_failures = 0
        self._device_id: str | None = None
        self.device_info: dict[str, str | None] = {}
        self._energy_totals: dict[str, float | None] = {}
        self._energy_totals_at: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Siseli cloud."""
        _LOGGER.debug("Fetching data from Siseli cloud")
        try:
            if self.client is None:
                async with self._client_lock:
                    if self.client is None:
                        self.client = await self.hass.async_add_executor_job(
                            partial(
                                SiseliClient,
                                account=self._account, password=self._password,
                            )
                        )
                        attach_open_auth(self.client)
            if self._device_id is None:
                devices = await self.client.get_all_devices()
                if not devices:
                    raise UpdateFailed("No devices found in Siseli account")
                self._device_id = devices[0].id
            state = await self.client.get_device_state(self._device_id)
            await self._async_refresh_energy_totals()
        except AuthenticationError as err:
            _LOGGER.warning("Siseli authentication failed; reauthentication required")
            raise ConfigEntryAuthFailed(err) from err
        except NetworkError as err:
            self._consecutive_failures += 1
            if self._consecutive_failures == 1:
                _LOGGER.warning(
                    "Error communicating with Siseli API (attempt %d): %s",
                    self._consecutive_failures,
                    err,
                )
            else:
                _LOGGER.debug(
                    "Siseli API still unreachable (consecutive failures: %d): %s",
                    self._consecutive_failures,
                    err,
                )
            raise UpdateFailed(f"Error communicating with Siseli API: {err}") from err

        if self._consecutive_failures > 0:
            _LOGGER.info(
                "Siseli API connection restored after %d consecutive failure(s)",
                self._consecutive_failures,
            )
        self._consecutive_failures = 0
        _LOGGER.debug("Siseli data updated successfully")
        # The SDK owns API field mapping, unit conversion, and derived telemetry.
        self.device_info = state.to_device_info()
        data = state.to_sensor_data()
        data["pv_generated_energy_total"] = self._energy_totals.get(
            PV_GENERATED_ENERGY_KEY
        )
        return data

    async def _async_refresh_energy_totals(self) -> None:
        """Refresh lifetime energy counters at most once per ENERGY_TOTALS_INTERVAL."""
        now = dt_util.utcnow()
        if (
            self._energy_totals_at is not None
            and now - self._energy_totals_at < ENERGY_TOTALS_INTERVAL
        ):
            return
        # Authentication errors propagate to the caller; a transient network
        # failure keeps the last known counters and is retried next interval.
        self._energy_totals_at = now
        try:
            self._energy_totals = await self.client.get_device_energy_totals(
                self._device_id
            )
        except NetworkError as err:
            _LOGGER.warning("Could not refresh Siseli lifetime energy totals: %s", err)
