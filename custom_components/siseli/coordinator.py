"""DataUpdateCoordinator for the Siseli integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from siseli import SiseliAuthError, SiseliClient, SiseliConnectionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SiseliCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches data from the Siseli cloud via python-siseli."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        creds = entry.data
        self.client = SiseliClient(
            username=creds[CONF_USERNAME],
            password=creds[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Siseli cloud."""
        try:
            return await self.client.get_data()
        except SiseliAuthError as err:
            # Trigger a reauthentication flow — permanent failure.
            raise ConfigEntryAuthFailed(err) from err
        except SiseliConnectionError as err:
            raise UpdateFailed(f"Error communicating with Siseli API: {err}") from err
