"""DataUpdateCoordinator for the Siseli integration."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import timedelta
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from siseli import AuthenticationError, NetworkError, SiseliClient

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, SISELI_APP_ID

_LOGGER = logging.getLogger(__name__)


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
                        if not SISELI_APP_ID:
                            _LOGGER.error(
                                "SISELI_APP_ID constant is empty; IOT-Open-AppID"
                                " header will be missing and authentication will"
                                " fail with error code 36"
                            )
                        else:
                            self.client._http.headers.update(
                                {"IOT-Open-AppID": SISELI_APP_ID}
                            )
            if self._device_id is None:
                devices = await self.client.get_all_devices()
                if not devices:
                    raise UpdateFailed("No devices found in Siseli account")
                self._device_id = devices[0].id
            state = await self.client.get_device_state(self._device_id)
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
        # state.fields is a dict[str, StateAttribute]; each StateAttribute has a .value
        return {key: attr.value for key, attr in state.fields.items()}
