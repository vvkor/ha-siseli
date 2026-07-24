"""Common fixtures for Siseli integration tests."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fake python-siseli module — installed before any integration code is loaded
# ---------------------------------------------------------------------------

class _SiseliAuthError(Exception):
    """Fake authentication error."""


class _SiseliConnectionError(Exception):
    """Fake connection error."""


class _SiseliClient:
    """Fake Siseli client."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        # noqa: S105 — intentional test fixture, not a real credential
        self.password = password
        self.authenticate = AsyncMock()
        self.get_data = AsyncMock(return_value=_DEFAULT_DATA.copy())


_DEFAULT_DATA: dict = {
    "battery_soc": 85,
    "battery_voltage": 52.1,
    "battery_current": 10.5,
    "battery_power": 547,
    "pv_voltage": 380.0,
    "pv_current": 3.2,
    "pv_power": 1216,
    "grid_voltage": 230.0,
    "grid_frequency": 50.0,
    "grid_power": 0,
    "output_voltage": 230.0,
    "output_frequency": 50.0,
    "load_power": 420,
    "inverter_state": "online",
}

_fake_siseli = ModuleType("siseli")
_fake_siseli.SiseliAuthError = _SiseliAuthError
_fake_siseli.SiseliConnectionError = _SiseliConnectionError
_fake_siseli.SiseliClient = _SiseliClient
sys.modules.setdefault("siseli", _fake_siseli)

# Re-export types so tests can import from this module
SiseliAuthError = _SiseliAuthError
SiseliConnectionError = _SiseliConnectionError
SiseliClient = _SiseliClient
DEFAULT_DATA = _DEFAULT_DATA


# ---------------------------------------------------------------------------
# Ensure custom integrations are enabled for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ensure the siseli custom integration is discoverable."""
    return


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_USERNAME = "test@example.com"
MOCK_PASSWORD = "secret"  # noqa: S105


@pytest.fixture
def mock_siseli_client():
    """Return a fresh mock SiseliClient."""
    client = MagicMock(spec=_SiseliClient)
    client.authenticate = AsyncMock()
    client.get_data = AsyncMock(return_value=_DEFAULT_DATA.copy())
    return client


@pytest.fixture
def mock_config_entry_data():
    """Return standard config entry data."""
    return {"username": MOCK_USERNAME, "password": MOCK_PASSWORD}


@pytest.fixture
def mock_config_entry_options():
    """Return standard config entry options."""
    return {}

