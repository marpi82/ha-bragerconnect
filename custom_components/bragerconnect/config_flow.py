"""Config Flow for the BragerConnect integration."""
from homeassistant import config_entries
from .const import DOMAIN


class BragerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""
