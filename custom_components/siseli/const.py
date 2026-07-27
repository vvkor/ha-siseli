"""Constants for the Siseli integration."""

DOMAIN = "siseli"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10  # seconds
MAX_SCAN_INTERVAL = 300  # seconds

CONF_SCAN_INTERVAL = "scan_interval"

# Application identifier sent as the IOT-Open-AppID header on every request,
# including the login call.  The Siseli Cloud API returns error code 36
# ("IOT-Open-AppID missing") when this header is absent.
SISELI_APP_ID = "ha-siseli"

TO_REDACT = {"username", "password", "token", "access_token", "refresh_token"}
