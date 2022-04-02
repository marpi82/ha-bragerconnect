"""BragerConnect coordinator."""
from __future__ import annotations
import logging
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICES_DEFAULT,
    CONF_DEVICES_SELECTED,
    DOMAIN,
)
from .api import BragerApiClient


_LOGGER: logging.Logger = logging.getLogger(__package__)


class BragerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, client: BragerApiClient, entry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []
        self.close_connection_listener: Callable | None = None

        self.device_filter = entry.options.get(
            CONF_DEVICES_SELECTED,
            entry.data.get(CONF_DEVICES_SELECTED, CONF_DEVICES_DEFAULT),
        )

        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.update()
        except Exception as exception:
            raise UpdateFailed() from exception
