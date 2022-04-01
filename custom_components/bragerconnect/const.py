"""Constants for the BragerConnect integration."""

# Base component constants
NAME = "BragerConnect"
DOMAIN = "bragerconnect"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ATTRIBUTION = "Data provided by https://cloud.bragerconnect.com"
ISSUE_URL = "https://github.com/marpi82/ha-bragerconnect/issues"

# Platforms
PLATFORMS: list[str] = []

# Configuration and options
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEVICES = "devices_id"
CONF_DEVICES_SELECTED = "selected_devices_id"
CONF_DEVICES_DEFAULT = "default_device_id"

# Defaults
DEFAULT_NAME = DOMAIN

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
