"""Common fixtures for Siseli integration tests."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Mapping
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


class _ApiError(Exception):
    """Fake SDK API error."""


class _ConfigAccess(IntEnum):
    READ_ONLY = 0
    SAFE = 1
    ADVANCED = 2
    CRITICAL = 3


class _ConfigKind(str, Enum):
    ENUM = "enum"
    NUMBER = "number"


class _ConfigWriteStatus(str, Enum):
    APPLIED = "applied"
    UNKNOWN = "unknown"
    DRY_RUN = "dry_run"


class _ConfigError(Exception):
    pass


class _ConfigValidationError(_ConfigError):
    pass


class _ConfigAccessDenied(_ConfigError):
    pass


class _ConfigRejected(_ConfigError):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Configuration write rejected ({code}): {message}")


@dataclass(frozen=True)
class _ConfigSpec:
    key: str
    name: str
    kind: _ConfigKind
    risk: _ConfigAccess
    options: Mapping[str, str] | None = None
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    scales_with_battery: bool = False
    wire_as_string: bool = True


@dataclass(frozen=True)
class _ConfigWriteResult:
    key: str
    status: _ConfigWriteStatus
    requested: str | int | float
    previous: str | int | float | None
    current: str | int | float | None
    error_code: int | None = None
    message: str | None = None

    @property
    def applied(self) -> bool:
        return self.status is _ConfigWriteStatus.APPLIED


class _AttributeMetadata:
    """Fake configuration metadata with a normalized value property."""

    def __init__(self, value) -> None:
        self.value = value


_ON_OFF = {"0": "Disable", "1": "Enable"}
_CONFIG_SPECS = {
    spec.key: spec
    for spec in (
        *(
            _ConfigSpec(key, name, _ConfigKind.ENUM, _ConfigAccess.SAFE, _ON_OFF)
            for key, name in (
                ("buzzerEnabled", "Buzzer"),
                ("lcdBackLightControlSetting", "LCD backlight"),
                ("lcdReturnToDefaultPageSetting", "LCD return to default page"),
                ("faultCodeRecordSetting", "Fault code record"),
                (
                    "alarmOnWhenPrimarySourceInterruptSetting",
                    "Alarm on primary source interruption",
                ),
            )
        ),
        *(
            _ConfigSpec(
                key, name, _ConfigKind.ENUM, _ConfigAccess.ADVANCED, _ON_OFF
            )
            for key, name in (
                ("overTemperatureRestartSetting", "Over temperature restart"),
                ("overLoadRestartSetting", "Overload restart"),
                ("overloadBypass", "Overload bypass"),
                ("powerSavingEnable", "Power saving"),
                ("setBatteryEqualizationEnable", "Battery equalization"),
            )
        ),
        _ConfigSpec(
            "settingDeviceOutputSourcePriority",
            "Output source priority",
            _ConfigKind.ENUM,
            _ConfigAccess.ADVANCED,
            {"0": "Utility first", "1": "Solar first", "2": "SBU"},
        ),
        _ConfigSpec(
            "settingDeviceChargerPriority",
            "Charger source priority",
            _ConfigKind.ENUM,
            _ConfigAccess.ADVANCED,
            {
                "0": "Utility first",
                "1": "Solar first",
                "2": "Solar and utility",
                "3": "Solar only",
            },
        ),
        _ConfigSpec(
            "settingDeviceGridWorkingRange",
            "Grid working range",
            _ConfigKind.ENUM,
            _ConfigAccess.ADVANCED,
            {"0": "Appliance", "1": "UPS"},
        ),
        _ConfigSpec(
            "settingBatteryType",
            "Battery type",
            _ConfigKind.ENUM,
            _ConfigAccess.CRITICAL,
            {"0": "AGM", "1": "Flooded", "2": "User"},
        ),
        _ConfigSpec(
            "setACOutputRatedVoltage",
            "AC output rated voltage",
            _ConfigKind.ENUM,
            _ConfigAccess.CRITICAL,
            {"220": "220 V", "230": "230 V", "240": "240 V"},
            unit="V",
        ),
        _ConfigSpec(
            "settingInverterOutputRatingFrequency",
            "AC output rated frequency",
            _ConfigKind.ENUM,
            _ConfigAccess.CRITICAL,
            {"50": "50 Hz", "60": "60 Hz"},
            unit="Hz",
        ),
        *(
            _ConfigSpec(
                key,
                name,
                _ConfigKind.NUMBER,
                _ConfigAccess.CRITICAL,
                unit=unit,
                minimum=minimum,
                maximum=maximum,
                step=step,
                scales_with_battery=scales,
                wire_as_string=False,
            )
            for key, name, unit, minimum, maximum, step, scales in (
                ("setMaxChargingCurrent", "Max charging current", "A", 10, 80, 10, False),
                (
                    "setUtilityMaxChargingCurrent",
                    "Max utility charging current",
                    "A",
                    10,
                    80,
                    10,
                    False,
                ),
                (
                    "setBatteryCutOffVoltage",
                    "Battery cut-off voltage",
                    "V",
                    10.0,
                    12.5,
                    0.1,
                    True,
                ),
                (
                    "setBatteryRechargingVoltage",
                    "Battery recharge voltage",
                    "V",
                    11.0,
                    13.0,
                    0.1,
                    True,
                ),
                (
                    "setBatteryRedischargingVoltage",
                    "Battery re-discharge voltage",
                    "V",
                    12.0,
                    14.5,
                    0.1,
                    True,
                ),
                (
                    "setBatteryCVChargeVoltage",
                    "Battery bulk (CV) voltage",
                    "V",
                    13.5,
                    15.0,
                    0.1,
                    True,
                ),
                (
                    "setBatteryFloatChargingVoltage",
                    "Battery float voltage",
                    "V",
                    13.0,
                    14.6,
                    0.1,
                    True,
                ),
                (
                    "setBatteryEqualizationVoltage",
                    "Equalization voltage",
                    "V",
                    13.5,
                    15.0,
                    0.1,
                    True,
                ),
                (
                    "setBatteryEqualizationTime",
                    "Equalization time",
                    "min",
                    5,
                    900,
                    5,
                    False,
                ),
                (
                    "setBatteryEqualizationOverTime",
                    "Equalization timeout",
                    "min",
                    5,
                    900,
                    5,
                    False,
                ),
                (
                    "setBatteryEqualizationPeriod",
                    "Equalization period",
                    "day",
                    0,
                    90,
                    1,
                    False,
                ),
            )
        ),
    )
}
_CONFIG_DEFAULTS = {
    key: (
        next(iter(spec.options))
        if spec.options is not None
        else spec.minimum
    )
    for key, spec in _CONFIG_SPECS.items()
}


def _config_value(meta: _AttributeMetadata):
    return meta.value


class _StateAttribute:
    """Fake StateAttribute with a value."""

    def __init__(self, value) -> None:
        self.value = value


class _DeviceState:
    """Fake DeviceState with a fields mapping."""

    def __init__(self, fields: dict) -> None:
        self.fields = {k: _StateAttribute(v) for k, v in fields.items()}

    def to_sensor_data(self) -> dict:
        """Stand-in for the SDK normalized telemetry contract."""
        return {k: attr.value for k, attr in self.fields.items()}

    def to_device_info(self) -> dict:
        """Stand-in for the SDK device identification contract."""
        return dict(_DEVICE_INFO)


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
        self.get_device_energy_totals = AsyncMock(return_value=dict(_ENERGY_TOTALS))
        self._config_values = dict(_CONFIG_DEFAULTS)
        self.get_device_config = AsyncMock(side_effect=self._get_device_config)
        self.get_cached_device_configs = AsyncMock(
            side_effect=self._get_cached_device_configs
        )
        self.safe_set_device_config = AsyncMock(side_effect=self._safe_set_device_config)

    async def _get_device_config(self, device_id: str, *, key: str):
        return _AttributeMetadata(self._config_values[key])

    async def _get_cached_device_configs(self, device_id: str):
        return {
            key: _AttributeMetadata(value)
            for key, value in self._config_values.items()
        }

    async def _safe_set_device_config(
        self,
        device_id: str,
        *,
        key: str,
        value,
        access: _ConfigAccess = _ConfigAccess.SAFE,
        battery_nominal_voltage: int | None = None,
        dry_run: bool = False,
    ):
        previous = self._config_values[key]
        self._config_values[key] = value
        return _ConfigWriteResult(
            key,
            _ConfigWriteStatus.APPLIED,
            value,
            previous,
            value,
        )


_DEVICE_INFO: dict = {
    "protocol": "P1",
    "machine_type": "SLP-5K",
    "firmware_version": "1.2.3",
    "secondary_firmware_version": "4.5.6",
}

# Lifetime counters (kWh) keyed by the API property key.
_ENERGY_TOTALS: dict = {"pvGeneratedEnergy": 1234.5}

_DEFAULT_DATA: dict = {
    # Stable semantic fields returned by DeviceState.to_sensor_data().
    "battery_soc": 85.0,
    "battery_voltage": 52.1,
    "battery_current": 10.5,
    "battery_power": 547.05,
    "pv_voltage": 380.0,
    "pv_current": 3.2,
    "pv_power": 1216.0,
    "grid_voltage": 230.0,
    "grid_frequency": 50.0,
    "output_voltage": 230.0,
    "output_frequency": 50.0,
    "load_power": 420.0,
    "inverter_state": "B",
    "inverter_mode": "Battery mode",
    "load_percent": 14.0,
    "load_apparent_power": 5000.0,
    "heat_sink_temperature": 41.0,
    "bus_voltage": 390.0,
    "charging_status": "Charging",
    "scc_charging_status": "Charging",
    "ac_charging_status": "Not charging",
    "mains_status": "Normal",
    "load_status": "Connected",
    "charger_source_priority": "Solar first",
    "output_source_priority": "SBU",
    "battery_type": "Lithium",
    # Added by the coordinator from get_device_energy_totals().
    "pv_generated_energy_total": 1234.5,
}

_fake_siseli = ModuleType("siseli")
_fake_siseli.AuthenticationError = _AuthenticationError
_fake_siseli.NetworkError = _NetworkError
_fake_siseli.ApiError = _ApiError
_fake_siseli.SiseliClient = _SiseliClient
_fake_siseli.CONFIG_SPECS = _CONFIG_SPECS
_fake_siseli.ConfigAccess = _ConfigAccess
_fake_siseli.ConfigKind = _ConfigKind
_fake_siseli.ConfigSpec = _ConfigSpec
_fake_siseli.ConfigError = _ConfigError
_fake_siseli.ConfigAccessDenied = _ConfigAccessDenied
_fake_siseli.ConfigRejected = _ConfigRejected
_fake_siseli.ConfigValidationError = _ConfigValidationError
_fake_siseli.ConfigWriteResult = _ConfigWriteResult
_fake_siseli.ConfigWriteStatus = _ConfigWriteStatus
_fake_siseli.config_value = _config_value
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
DEVICE_INFO = _DEVICE_INFO
ENERGY_TOTALS = _ENERGY_TOTALS


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
    client.get_device_energy_totals = AsyncMock(return_value=dict(_ENERGY_TOTALS))
    client.get_device_config = AsyncMock(
        side_effect=lambda device_id, *, key: _AttributeMetadata(
            _CONFIG_DEFAULTS[key]
        )
    )
    client.get_cached_device_configs = AsyncMock(
        return_value={
            key: _AttributeMetadata(value)
            for key, value in _CONFIG_DEFAULTS.items()
        }
    )
    client.safe_set_device_config = AsyncMock(
        side_effect=lambda device_id, *, key, value, **kwargs: _ConfigWriteResult(
            key,
            _ConfigWriteStatus.APPLIED,
            value,
            _CONFIG_DEFAULTS[key],
            value,
        )
    )
    return client


@pytest.fixture
def mock_config_entry_data():
    """Return standard config entry data."""
    return {"username": MOCK_USERNAME, "password": MOCK_PASSWORD}


@pytest.fixture
def mock_config_entry_options():
    """Return standard config entry options."""
    return {}
