"""BragerConnect API Client."""
import logging
import asyncio
from typing import Optional

from .brager import BragerConnect

_LOGGER: logging.Logger = logging.getLogger(__package__)


class BragerApiClient(BragerConnect):
    """BragerConnect API Client."""

    def __init__(self, username: str, password: str) -> None:
        """BragerConnect API Client."""
        self._username = username
        self._password = password

        super().__init__(asyncio.get_running_loop())

    async def async_connect(self) -> None:
        """Connect to BragerConnect service."""
        # TODO: if it possible to get default lang from hass UI use it to connect function
        return await self.connect(self._username, self._password)

    @property
    def available_devices(self) -> list:
        """Available devices ID list"""
        return [repr(device) for device in self._device] if not None else []

    @property
    async def active_device(self) -> str:
        """Active device ID"""
        return await self.wrkfnc_get_active_device_id()

    async def __aenter__(self):
        return self
