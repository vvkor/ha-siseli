"""Shared device registry information for Siseli entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import SiseliCoordinator


def build_device_info(coordinator: SiseliCoordinator) -> DeviceInfo:
    """Return the inverter device, enriched with model/firmware once known."""
    info = coordinator.device_info
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="Siseli Inverter",
        manufacturer="Siseli",
        model=info.get("machine_type"),
        sw_version=info.get("firmware_version"),
    )
