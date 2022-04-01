"""Config Flow for the BragerConnect integration."""
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .api import BragerApiClient
from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_DEVICES,
    CONF_DEVICES_DEFAULT,
    CONF_DEVICES_SELECTED,
    DOMAIN,
    PLATFORMS,
)


_LOGGER: logging.Logger = logging.getLogger(__package__)


class BragerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """BragerConnect config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def __init__(self):
        """Initialize."""
        self._errors: dict = {}
        self._init_info: dict = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Uncomment the next 2 lines if only a single instance of the integration is allowed:
        # if self._async_current_entries():
        #     return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            _LOGGER.debug("Credentials valid: %s", valid)
            if valid:
                self._init_info.update(user_input)
                return await self.async_step_settings()
            else:
                self._errors["base"] = "auth"

            return await self._show_config_form(user_input)

        user_input = {}
        # Provide defaults for form
        user_input[CONF_USERNAME] = ""
        user_input[CONF_PASSWORD] = ""

        return await self._show_config_form(user_input)

    async def async_step_settings(self, user_input=None):
        """Handle a flow settings"""
        self._errors = {}
        if user_input is not None:
            self._init_info.update(user_input)
            _LOGGER.debug("Creating entry with data %s", self._init_info)
            return self.async_create_entry(
                title=self._init_info[CONF_USERNAME], data=self._init_info
            )
        return await self._show_settings_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BragerOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD, default=user_input[CONF_PASSWORD]): str,
                }
            ),
            errors=self._errors,
        )

    async def _show_settings_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit settings data."""
        return self.async_show_form(
            step_id="settings",
            last_step=True,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICES_SELECTED,
                        default=[self._init_info[CONF_DEVICES_DEFAULT]],
                    ): cv.multi_select(self._init_info[CONF_DEVICES])
                },
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            async with BragerApiClient(username, password) as client:
                await client.async_connect()
                self._init_info.update(
                    {
                        CONF_DEVICES_DEFAULT: await client.active_device,
                        CONF_DEVICES: client.available_devices,
                    }
                )
                _LOGGER.info("Found device ID's: %s", self._init_info[CONF_DEVICES])
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class BragerOptionsFlowHandler(config_entries.OptionsFlow):
    """BragerConnect config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.api = None

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        self.api = self.hass.data[DOMAIN][self.config_entry.entry_id]
        return await self.async_step_device_options()

    async def async_step_device_options(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        username = self.config_entry.data.get(CONF_USERNAME)
        password = self.config_entry.data.get(CONF_PASSWORD)
        async with BragerApiClient(username, password) as client:
            await client.async_connect()
            # device_id = await client.active_device
            devices = client.available_devices
            _LOGGER.info("Found device ID's: %s", devices)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICES_SELECTED,
                        default=self.config_entry.data.get(CONF_DEVICES_SELECTED) or [],
                    ): cv.multi_select(devices),
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title="", data=self.options)
