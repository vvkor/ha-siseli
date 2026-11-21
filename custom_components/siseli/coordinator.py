"""DataUpdateCoordinator for the Siseli integration."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from siseli import (
    ApiError,
    AuthenticationError,
    InvalidResponseError,
    NetworkError,
    SiseliClient,
)

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OFFLINE_API_CODE,
    STALE_AFTER,
)

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .config_coordinator import SiseliConfigCoordinator

def _aware(value: datetime | None) -> datetime | None:
    """Treat naive API timestamps as UTC, like the SDK does."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


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
        self.config_coordinator: SiseliConfigCoordinator | None = None
        # True/False once the inverter's connectivity is known, None when unknown
        # (for example while the cloud itself cannot be reached).
        self.device_online: bool | None = None
        self.last_online_at: datetime | None = None
        self._energy_totals: dict[str, float | None] = {}
        self._energy_totals_at: datetime | None = None

    @property
    def device_id(self) -> str | None:
        """Return the monitored device id once it has been discovered."""
        return self._device_id

    @property
    def consecutive_failures(self) -> int:
        """Return how many polls in a row have failed."""
        return self._consecutive_failures

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
                                account=self._account,
                                password=self._password,
                                open_auth=True,
                            )
                        )
            if self._device_id is None:
                devices = await self.client.get_all_devices()
                if not devices:
                    raise UpdateFailed("No devices found in Siseli account")
                if len(devices) > 1:
                    _LOGGER.warning(
                        "Siseli account has %d devices; only the first one (%s) is monitored",
                        len(devices),
                        devices[0].id,
                    )
                self._device_id = devices[0].id
            state = await self.client.get_device_state(self._device_id)
            device = await self._async_get_device()
            await self._async_refresh_energy_totals()
        except AuthenticationError as err:
            _LOGGER.warning("Siseli authentication failed; reauthentication required")
            raise ConfigEntryAuthFailed(err) from err
        except (NetworkError, ApiError, InvalidResponseError) as err:
            # ApiError covers cloud-side conditions such as "Device is offline" (71000);
            # NetworkError includes HTTP 429 throttling (RateLimitError).
            self._consecutive_failures += 1
            # "Device is offline" means the cloud is fine and only the inverter is
            # gone; anything else leaves its connectivity unknown.
            offline = isinstance(err, ApiError) and err.code == OFFLINE_API_CODE
            self._set_online(False if offline else None)
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

        recovering = self._consecutive_failures > 0 or self.device_online is False
        if self._consecutive_failures > 0:
            _LOGGER.info(
                "Siseli API connection restored after %d consecutive failure(s)",
                self._consecutive_failures,
            )
        online = self._is_online(state, device)
        self._set_online(online)
        if device is not None:
            self.last_online_at = device.last_online_at
        if online and recovering and self.config_coordinator is not None:
            # Configuration is refreshed on a slow timer; do not make its entities
            # wait for it after the inverter comes back.
            self.hass.async_create_task(self.config_coordinator.async_request_refresh())
        self._consecutive_failures = 0
        _LOGGER.debug("Siseli data updated successfully")
        # The SDK owns API field mapping, unit conversion, and derived telemetry.
        self.device_info = state.to_device_info()
        self._async_sync_device_registry()
        data = state.to_sensor_data()
        data["pv_generated_energy_total"] = self._energy_totals.get(
            PV_GENERATED_ENERGY_KEY
        )
        data["last_data_received"] = _aware(state.time)
        return data

    async def _async_get_device(self) -> Any:
        """Return the cloud's device record, or None if it cannot be read."""
        try:
            return await self.client.get_device(self._device_id)
        except (NetworkError, ApiError, InvalidResponseError) as err:
            # The telemetry request already succeeded; the flag is only a hint.
            _LOGGER.debug("Could not read the Siseli device status: %s", err)
            return None

    @staticmethod
    def _is_online(state: Any, device: Any) -> bool:
        """Combine the cloud's online flag with the age of the newest telemetry."""
        snapshot = _aware(state.time)
        if snapshot is not None and dt_util.utcnow() - snapshot > STALE_AFTER:
            return False
        # The SDK defaults a missing flag to False, so trust it only when present.
        raw = getattr(device, "raw", None) or {}
        return not (device is not None and "isOnline" in raw and not device.is_online)

    def _set_online(self, online: bool | None) -> None:
        """Record connectivity and refresh the configuration entities on change."""
        if online == self.device_online:
            return
        if online is False:
            _LOGGER.warning("Siseli inverter is offline")
        elif online and self.device_online is False:
            _LOGGER.info("Siseli inverter is back online")
        self.device_online = online
        if self.config_coordinator is not None:
            # Configuration entities depend on connectivity for their availability.
            self.config_coordinator.async_update_listeners()

    def _async_sync_device_registry(self) -> None:
        """Fill in model/firmware when they only become known after entity setup."""
        if self.hass.config_entries.async_get_entry(self.config_entry.entry_id) is None:
            return
        registry = dr.async_get(self.hass)
        identifier = (DOMAIN, self.config_entry.entry_id)
        device = next(
            (
                device
                for device in dr.async_entries_for_config_entry(
                    registry, self.config_entry.entry_id
                )
                if identifier in device.identifiers
            ),
            None,
        )
        model = self.device_info.get("machine_type")
        sw_version = self.device_info.get("firmware_version")
        if device is None or (
            (not model or device.model == model)
            and (not sw_version or device.sw_version == sw_version)
        ):
            return
        registry.async_update_device(
            device.id,
            model=model or device.model,
            sw_version=sw_version or device.sw_version,
        )

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
        except (NetworkError, ApiError, InvalidResponseError) as err:
            _LOGGER.warning("Could not refresh Siseli lifetime energy totals: %s", err)
