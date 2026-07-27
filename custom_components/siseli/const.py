"""Constants for the Siseli integration."""

DOMAIN = "siseli"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10  # seconds
MAX_SCAN_INTERVAL = 300  # seconds

CONF_SCAN_INTERVAL = "scan_interval"

# Production Siseli Open API application credentials from the official web client.
SISELI_APP_ID = "rBrTRfAPXz"
SISELI_APP_SECRET_ENCRYPTED = "I4D0KRr2339z3pQ/at91V9BpFAOe54DaTafwSm6suIQ="

TO_REDACT = {"username", "password", "token", "access_token", "refresh_token"}
