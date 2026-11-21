"""Constants for the Siseli integration."""

from datetime import timedelta

DOMAIN = "siseli"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10  # seconds
MAX_SCAN_INTERVAL = 300  # seconds

CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONFIG_ACCESS = "config_access"
CONF_BATTERY_NOMINAL_VOLTAGE = "battery_nominal_voltage"

DEFAULT_CONFIG_ACCESS = "disabled"
DEFAULT_BATTERY_NOMINAL_VOLTAGE = 12
CONFIG_ACCESS_LEVELS = ("disabled", "safe", "advanced", "critical")
BATTERY_NOMINAL_VOLTAGES = (12, 24, 48)

# The cloud reports "Device is offline" with this API error code.
OFFLINE_API_CODE = 71000
# The inverter reports to the cloud about every 5 minutes. If the newest telemetry
# snapshot is older than this, the inverter is treated as offline even if the cloud
# has not flagged it yet, so stale values are not shown as current.
STALE_AFTER = timedelta(minutes=10)

TO_REDACT = {"username", "password", "token", "access_token", "refresh_token"}
