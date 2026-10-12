"""Constants for the Siseli integration."""

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

TO_REDACT = {"username", "password", "token", "access_token", "refresh_token"}
