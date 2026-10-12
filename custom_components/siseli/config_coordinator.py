"""Slow coordinator and serialized writes for inverter configuration."""

from __future__ import annotations

import logging
from asyncio import Lock
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from siseli import (
    CONFIG_SPECS,
    ApiError,
    AuthenticationError,
    ConfigAccess,
    ConfigAccessDenied,
    ConfigRejected,
    ConfigValidationError,
    ConfigWriteStatus,
    NetworkError,
    config_value,
)

from .const import DOMAIN
from .coordinator import SiseliCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_REFRESH_INTERVAL = timedelta(minutes=15)

_ACCESS_BY_NAME = {
    "safe": ConfigAccess.SAFE,
    "advanced": ConfigAccess.ADVANCED,
    "critical": ConfigAccess.CRITICAL,
}


class SiseliConfigCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Refresh configuration independently from fast telemetry polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        telemetry_coordinator: SiseliCoordinator,
        access_name: str,
        battery_nominal_voltage: int,
    ) -> None:
        """Initialize the configuration coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} configuration",
            update_interval=CONFIG_REFRESH_INTERVAL,
            config_entry=entry,
        )
        assert telemetry_coordinator.client is not None
        assert telemetry_coordinator._device_id is not None
        self.client = telemetry_coordinator.client
        self.device_id = telemetry_coordinator._device_id
        self.access = _ACCESS_BY_NAME[access_name]
        self.battery_nominal_voltage = battery_nominal_voltage
        self._write_lock = Lock()
        self.specs = tuple(
            spec for spec in CONFIG_SPECS.values() if spec.risk <= self.access
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh readable configuration values at the slower interval."""
        try:
            cached = await self.client.get_cached_device_configs(self.device_id)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(err) from err
        except (NetworkError, ApiError) as err:
            raise UpdateFailed(f"Could not refresh inverter configuration: {err}") from err

        # Keys missing from the cache are omitted so their entities show no value
        # instead of triggering a burst of individual inverter reads.
        return {
            spec.key: config_value(cached[spec.key])
            for spec in self.specs
            if spec.key in cached
        }

    async def async_write(self, key: str, value: Any) -> None:
        """Write one configuration value without retries or optimistic updates."""
        if not any(spec.key == key for spec in self.specs):
            raise HomeAssistantError("Writes are not enabled for this inverter setting.")
        async with self._write_lock:
            try:
                result = await self.client.safe_set_device_config(
                    self.device_id,
                    key=key,
                    value=value,
                    access=self.access,
                    battery_nominal_voltage=self.battery_nominal_voltage,
                )
            except AuthenticationError as err:
                self._log_write(key, self._current_value(key), value, "authentication_error")
                raise ConfigEntryAuthFailed(err) from err
            except ConfigValidationError:
                self._log_write(key, self._current_value(key), value, "validation_error")
                raise HomeAssistantError(
                    "Invalid value for inverter setting."
                ) from None
            except ConfigAccessDenied:
                self._log_write(key, self._current_value(key), value, "access_denied")
                raise HomeAssistantError(
                    "Writes are not enabled for this inverter setting."
                ) from None
            except ConfigRejected:
                self._log_write(key, self._current_value(key), value, "rejected")
                raise HomeAssistantError(
                    "The inverter rejected this configuration change."
                ) from None

            status = result.status
            self._log_write(key, result.previous, result.requested, status.value)
            if status is ConfigWriteStatus.UNKNOWN:
                self.hass.async_create_task(self.async_request_refresh())
                raise HomeAssistantError(
                    "The write result is unknown; the configured value was not assumed."
                )
            if status is not ConfigWriteStatus.APPLIED:
                raise HomeAssistantError("The inverter configuration was not changed.")

            updated = dict(self.data or {})
            updated[key] = result.current
            self.async_set_updated_data(updated)

    def _current_value(self, key: str) -> Any:
        """Return the last confirmed value for write logging."""
        return self.data.get(key) if self.data else None

    @staticmethod
    def _log_write(key: str, old_value: Any, new_value: Any, status: str) -> None:
        """Log a write attempt without including SDK error payloads."""
        _LOGGER.info(
            "Inverter configuration write key=%s old=%r new=%r status=%s",
            key,
            old_value,
            new_value,
            status,
        )
