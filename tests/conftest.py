"""Common fixtures for Siseli integration tests."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fake python-siseli module — installed before any integration code is loaded
# ---------------------------------------------------------------------------


class _AuthenticationError(Exception):
    """Fake authentication error."""


class _NetworkError(Exception):
    """Fake network error."""


class _StateAttribute:
    """Fake StateAttribute with a value."""

    def __init__(self, value) -> None:
        self.value = value


class _DeviceState:
    """Fake DeviceState with a fields mapping."""

    def __init__(self, fields: dict) -> None:
        self.fields = {k: _StateAttribute(v) for k, v in fields.items()}


class _Device:
    """Fake Device with an id."""

    def __init__(self, device_id: str) -> None:
        self.id = device_id


class _SiseliClient:
    """Fake Siseli client."""

    def __init__(self, account: str, password: str) -> None:
        self.account = account
        self.password = password
        self.authenticate = AsyncMock()
        self.get_all_devices = AsyncMock(return_value=[_Device("device-001")])
        self.get_device_state = AsyncMock(
            return_value=_DeviceState(_DEFAULT_DATA.copy())
        )


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
_fake_siseli.AuthenticationError = _AuthenticationError
_fake_siseli.NetworkError = _NetworkError
_fake_siseli.SiseliClient = _SiseliClient
sys.modules.setdefault("siseli", _fake_siseli)

# The fake "siseli" above is a plain ModuleType (not a real package), so Python
# cannot resolve sub-imports like "siseli.const" or "siseli.open_auth".
# Import the real SDK submodules while the real package is still importable
# (the parent entry may already be the fake, but the submodule files are on-disk)
# and pin them directly in sys.modules so test_open_auth.py can use them.
import importlib as _importlib

for _submod in ("siseli.const", "siseli.open_auth"):
    if _submod not in sys.modules:
        try:
            # Temporarily remove the fake parent so the importer sees the real package.
            _saved = sys.modules.pop("siseli", None)
            sys.modules[_submod] = _importlib.import_module(_submod)
        except ImportError:
            pass
        finally:
            if _saved is not None:
                sys.modules["siseli"] = _saved

# Re-export types so tests can import from this module
AuthenticationError = _AuthenticationError
NetworkError = _NetworkError
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
MOCK_PASSWORD = "secret"


@pytest.fixture
def mock_siseli_client():
    """Return a fresh mock SiseliClient."""
    client = MagicMock(spec=_SiseliClient)
    client.authenticate = AsyncMock()
    client.get_all_devices = AsyncMock(return_value=[_Device("device-001")])
    client.get_device_state = AsyncMock(return_value=_DeviceState(_DEFAULT_DATA.copy()))
    return client


@pytest.fixture
def mock_config_entry_data():
    """Return standard config entry data."""
    return {"username": MOCK_USERNAME, "password": MOCK_PASSWORD}


@pytest.fixture
def mock_config_entry_options():
    """Return standard config entry options."""
    return {}
