"""The BragerConnect integration."""
from __future__ import annotations
import asyncio
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_CLOSE
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant, Event
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.bragerconnect.brager.bragerconnect import BragerConnect

from .const import (
    CONF_DEVICES_DEFAULT,
    CONF_DEVICES_SELECTED,
    DOMAIN,
    PLATFORMS,
    CONF_USERNAME,
    CONF_PASSWORD,
    STARTUP_MESSAGE,
)
from .api import BragerApiClient
from .coordinator import BragerCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BragerConnect from a config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    client = BragerApiClient(username, password)
    client.reconnect = True
    await client.connect()

    coordinator = BragerCoordinator(hass, client=client, entry=entry)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator
    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_setup_platforms(entry, platform)
            )

    async def disconnect(event: Event):  # pylint: disable=unused-argument
        return await client.disconnect()

    coordinator.close_connection_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_CLOSE, disconnect
    )

    entry.async_on_unload(entry.add_update_listener(async_unload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: BragerCoordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_unload_platforms(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ],
        )
    )

    coordinator.close_connection_listener()
    await coordinator.api.disconnect()

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
