"""BragerConnect API Client."""
import logging

from .brager import BragerConnect

_LOGGER: logging.Logger = logging.getLogger(__package__)


class BragerApiClient(BragerConnect):
    """BragerConnect API Client."""

    @property
    async def available_devices(self) -> list:
        """Available devices ID list"""
        return [info.get("devid") for info in await self.wrkfnc_get_device_id_list()]

    @property
    async def active_device(self) -> str:
        """Active device ID"""
        return await self.wrkfnc_get_active_device_id()

    async def __aenter__(self):
        return self
