"""Diagnostics support for the Siseli integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SiseliConfigEntry
from .const import TO_REDACT


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SiseliConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "domain": entry.domain,
            "state": entry.state.value,
            "options": dict(entry.options),
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "consecutive_failures": coordinator._consecutive_failures,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "data": coordinator.data,
    }
