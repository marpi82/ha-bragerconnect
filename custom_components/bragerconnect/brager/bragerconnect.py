"""Asynchronous Python client for BragerConnect."""
from __future__ import annotations

import asyncio
import json
import socket
import logging
import threading
from typing import Any, Optional

import backoff  # pylint: disable=unused-import
import websockets

from .const import JSON_TYPE, HOST, TIMEOUT
from .exceptions import (
    BragerConnectionError,
    BragerMessageException,
    BragerAuthError,
    BragerError,
)
from .models import (
    MessageType,
    BragerDevice,
)

_LOGGER = logging.getLogger(__package__)


class BragerConnect:
    """Main class for handling connections with BragerConnect."""

    def __init__(
        self,
        username: str,
        password: str,
        language: str = "en",
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Main class for handling connections with BragerConnect.

        Args:
            loop (Optional[asyncio.AbstractEventLoop], optional): Event loop. Defaults to None.
        """
        self._host: str = HOST

        self._loop: asyncio.AbstractEventLoop = (
            loop if loop is not None else asyncio.get_event_loop()
        )
        self._responses: dict[int, asyncio.Future[Any]] = {}
        self._messages_counter: int = -1
        self._messages_counter_thread_lock: threading.Lock = threading.Lock()

        self._client: Optional[websockets.client.WebSocketClientProtocol] = None
        self._device: Optional[list[BragerDevice]] = None
        self._device_message: Optional[dict[str, asyncio.Queue]] = None

        self._logged_in: bool = False

        self._username: str = username
        self._password: str = password
        self._language: str = language
        self._active_device_id: Optional[str] = None
        self._reconnect: bool = False

    @property
    def connected(self) -> bool:
        """Return if we are connect to the WebSocket of a BragerConnect service.

        Returns:
            bool: True if we are connected, False otherwise.
        """
        return self._client and not self._client.closed

    @property
    def logged_in(self) -> bool:
        """Returns if we are logged in

        Returns:
            bool: True if we are logged in, otherwise False
        """
        return self._logged_in

    @property
    def reconnect(self) -> bool:
        """TODO: docstring"""
        return self._reconnect

    @reconnect.setter
    def reconnect(self, value: bool) -> None:
        """TODO: docstring"""
        self._reconnect = bool(value)

    async def connect(self) -> None:
        """Connect to the WebSocket of a BragerConnect service.
        Authenticate user with given credentials, and sets default language

        Raises:
            BragerConnectionError: Error occurred while communicating with the BragerConnect.
            BragerAuthError: Error occurred on logging in (wrong username and/or password).
            BragerError: Error occured while setting language.
        """
        if self.connected:
            return

        _LOGGER.info("Connecting to BragerConnect service via WebSocket.")
        try:
            self._client = await websockets.connect(  # pylint: disable=no-member
                uri=self._host
            )
        except (
            websockets.InvalidURI,  # pylint: disable=no-member
            websockets.InvalidHandshake,  # pylint: disable=no-member
            asyncio.TimeoutError,
            socket.gaierror,
        ) as exception:
            _LOGGER.exception("Error connecting to BragerConnect.")
            raise BragerConnectionError(
                "Error occurred while communicating with BragerConnect service"
                f" on WebSocket at {self._host}"
            ) from exception

        _LOGGER.debug("Waiting for READY_SIGNAL.")
        message = await asyncio.wait_for(self._client.recv(), TIMEOUT)
        _LOGGER.debug("Message received.")
        wrkfnc: JSON_TYPE = json.loads(message)

        if isinstance(wrkfnc, dict) and wrkfnc.get("type") == MessageType.READY_SIGNAL:
            _LOGGER.debug("Got READY_SIGNAL, sending back, connection ready.")
            await self._client.send(message)
        else:
            _LOGGER.exception("Received message is not a READY_SIGNAL, exiting")
            raise BragerConnectionError(
                "Error occurred while communicating with BragerConnect service."
                "READY_SIGNAL was expected."
            )

        _LOGGER.info("Creating task for received messages processing")
        self._loop.create_task(self._process_messages())

        await self._login(self._username, self._password)

        if self._language:
            if not await self.wrkfnc_set_user_variable(
                "preffered_lang", self._language
            ):
                raise BragerError("Error setting language on BragerConnect service.")

        if not self._active_device_id:
            await self.wrkfnc_get_active_device_id()

        # if not self._device:
        #    await self.update()

    async def update(self) -> list[BragerDevice]:
        """Updates all devices existing on BragerConnect service.
        If the device does not exist, it will be created.

        Raises:
            BragerError: Raised when was error updating devices

        Returns:
            list[BragerDevice]: Updated BragerDevice's list
        """

        # Run update_device for each device existing on BragerConnect service.
        if not (
            _device := [
                await self.update_device(info.get("devid"), info)
                for info in await self.wrkfnc_get_device_id_list()
            ]
        ):
            raise BragerError("Failed to update devices from BragerConnect service.")

        return _device

    async def update_device(
        self, device_id: str, device_info: JSON_TYPE = None
    ) -> BragerDevice:
        """Updates the device with the given identifier.
        If the device does not exist, it will be created.

        Args:
            device_id (str): Brager DeviceID
            device_info (JSON_TYPE], optional): Device info dictionary. Defaults to None.

        Raises:
            BragerError: Raised when was error updating device

        Returns:
            BragerDevice: Updated BragerDevice object
        """
        # Check BragerDevice object is created for specified device_id, if not set _full_update
        if not (_full_update := self._device is None):
            _full_update = not any(
                device.info.devid == device_id for device in self._device
            )

        _LOGGER.debug("Making full update? %s", _full_update)

        if _full_update:
            if device_info is None:
                if not (
                    _info := next(
                        info
                        for info in await self.wrkfnc_get_device_id_list()
                        if info.get("devid") == device_id
                    )
                ):
                    raise BragerError(
                        "Failed to get devices list from BragerConnect service or list is empty."
                    )
            else:
                if device_info.get("devid") != device_id:
                    raise BragerError(
                        "Given device_id and device_info are for different devices."
                    )
                else:
                    _info = device_info

            _data: JSON_TYPE = {"info": _info}
        else:
            _data: JSON_TYPE = {}

        if self._active_device_id != device_id:
            await self.wrkfnc_set_active_device_id(device_id)

        if not (_pool := await self.wrkfnc_get_all_pool_data()):
            raise BragerError(
                "Failed to get pool data from BragerConnect service or pool data is empty."
            )

        _task = await self.wrkfnc_get_task_queue()
        _alarm = await self.wrkfnc_get_alarm_list()
        _data.update({"pool": _pool, "task": _task, "alarm": _alarm})

        if _full_update:
            _device = BragerDevice(_data)
            self._device = [_device]
        else:
            _device = next(
                device for device in self._device if device.info.devid == device_id
            ).update_from_dict(_data)

        return _device

    async def _login(self, username: str, password: str) -> bool:
        """Authenticate user with given credentials

        Args:
            username (str): Username used to login
            password (str): Password used to login

        Returns:
            bool: True if logged in, otherwise False
        """
        if self.logged_in:
            return True

        _LOGGER.debug("Logging in.")
        try:
            result = await self.wrkfnc_execute(
                "s_login",
                [
                    username,
                    password,
                    None,
                    None,
                    "bc_web",  # IDEA: could be a `bc_web` or `ht_app - what does it mean?
                ],
            )
        except BragerMessageException as exception:
            raise BragerAuthError(
                "Error when logging in (wrong username/password)"
            ) from exception
        else:
            self._logged_in = result == 1
            return self._logged_in

    async def _process_messages(self) -> None:
        """Main function that processes incoming messages from Websocket."""
        try:
            async for message in self._client:
                wrkfnc: JSON_TYPE = json.loads(message)
                if wrkfnc is not None and wrkfnc.get("wrkfnc"):
                    _LOGGER.debug("Received response: %s", message)
                    message_id = wrkfnc.get("nr")
                    if message_id is not None:
                        # It is a response for request sent
                        if len(self._responses) > 0:
                            self._responses.pop(message_id).set_result(wrkfnc)
                    else:
                        # It is a request
                        await self._process_request(wrkfnc)
                else:
                    _LOGGER.error("Received message type is not known, skipping.")
                    continue
        except (
            websockets.ConnectionClosed,  # pylint: disable=no-member
            websockets.ConnectionClosedError,  # pylint: disable=no-member
        ):
            _LOGGER.info("BragerConnect connection lost.")
            if self.reconnect:
                self._logged_in = False
                await self.connect()
            else:
                await self.disconnect()

    async def _process_request(self, wrkfnc: dict) -> None:
        """Function that processes messages containing the actions to be performed (requests)

        Args:
            wrkfnc (dict): Dictionary containing message variables
        """
        _LOGGER.debug(
            "Received request to execute: %s(args=%s)",
            wrkfnc["name"],
            wrkfnc["args"],
        )

    async def _send_wrkfnc(
        self,
        wrkfnc_name: str,
        wrkfnc_args: Optional[list] = None,
        wrkfnc_type: MessageType = MessageType.FUNCTION_EXEC,
    ) -> int:
        """Sends message. JSON formatted

        Args:
            wrkfnc_name (str): Function name to execute on server side
            wrkfnc_args (Optional[list], optional): Function parameters list. Defaults to None.
            wrkfnc_type (MessageType, optional): Message type. Defaults to FUNCTION_EXEC.

        Returns:
            int: Sent messade ID
        """
        message_id = self._generate_message_id()
        message = json.dumps(
            {
                "wrkfnc": True,
                "type": wrkfnc_type,
                "name": f"{wrkfnc_name}",
                "nr": message_id,
                "args": wrkfnc_args if wrkfnc_args is not None else [],
            }
        )

        _LOGGER.debug("Sending function to execute: %s", message)
        await self._client.send(message)

        return message_id

    async def _wait_wrkfnc(self, message_id: int) -> JSON_TYPE:
        """Waiting to receive the response to the message with the `message_id`

        Args:
            message_id (int): Message ID number.

        Raises:
            BragerError: When timeout occurs.

        Returns:
            JSON_TYPE: (str) Received message
        """

        try:
            result: JSON_TYPE = await asyncio.wait_for(
                self._responses.setdefault(message_id, self._loop.create_future()),
                TIMEOUT,
            )
        except asyncio.TimeoutError as exception:
            _LOGGER.exception("Timed out while processing request response.")
            raise BragerError(
                "Timed out while processing request response from BragerConnect service."
            ) from exception
        else:
            if result.get("type") == MessageType.EXCEPTION:
                _LOGGER.exception("Exception response received.")
                raise BragerMessageException(
                    "Exception occured while processing request response."
                )
            return result.get("resp")

    async def wrkfnc_execute(
        self,
        wrkfnc_name: str,
        wrkfnc_args: Optional[list[str]] = None,
        wrkfnc_type: MessageType = MessageType.FUNCTION_EXEC,
    ) -> JSON_TYPE:
        """Sends a request to perform request on server side and waits for the response.

        Args:
            wrkfnc_name (str): Function name to execute.
            wrkfnc_args (Optional[list], optional): Function parameters list. Defaults to None.
            wrkfnc_type (MessageType, optional): Message type. Defaults to FUNCTION_EXEC.

        Returns:
            JSON_TYPE: Server response
        """
        return await self._wait_wrkfnc(
            await self._send_wrkfnc(wrkfnc_name, wrkfnc_args, wrkfnc_type),
        )

    async def wrkfnc_get_device_id_list(self) -> list[JSON_TYPE]:
        """Gets a list of dictionaries with information about devices from the server.

        Returns:
            list[JSON_TYPE]: list of dictionaries with information about devices.
        """
        return await self.wrkfnc_execute("s_getMyDevIdList", []) or []

    async def wrkfnc_get_active_device_id(self) -> str:
        """Gets the ID of the active device on the server

        Returns:
            str: Active device ID
        """
        _LOGGER.debug("Getting active device id.")
        _device_id = await self.wrkfnc_execute("s_getActiveDevid", [])
        device_id = str(_device_id)
        self._active_device_id = device_id
        return device_id

    async def wrkfnc_set_active_device_id(self, device_id: str) -> bool:
        """Sets the ID of the active device on the server

        Args:
            device_id (str): Device ID to set active

        Returns:
            bool: True if setting was successfull, otherwise False
        """
        _LOGGER.debug("Setting active device id to: %s.", device_id)
        result = await self.wrkfnc_execute("s_setActiveDevid", [device_id]) is True
        self._active_device_id = device_id
        return result

    async def wrkfnc_get_user_variable(self, variable_name: str) -> str:
        """TODO: docstring"""
        return await self.wrkfnc_execute("s_getUserVariable", [variable_name])

    async def wrkfnc_set_user_variable(self, variable_name: str, value: str) -> bool:
        """TODO: docstring"""
        return (
            await self.wrkfnc_execute("s_setUserVariable", [variable_name, value])
            is None
        )

    async def wrkfnc_get_all_pool_data(self) -> JSON_TYPE:
        """TODO: docstring"""
        _LOGGER.debug("Getting pool data for %s.", self._active_device_id)
        return await self.wrkfnc_execute("s_getAllPoolData", [])

    async def wrkfnc_get_task_queue(self) -> JSON_TYPE:
        """TODO: docstring"""
        _LOGGER.debug("Getting tasks data for %s.", self._active_device_id)
        return await self.wrkfnc_execute("s_getTaskQueue", [])

    async def wrkfnc_get_alarm_list(self) -> JSON_TYPE:
        """TODO: docstring"""
        _LOGGER.debug("Getting alarms data for %s.", self._active_device_id)
        return await self.wrkfnc_execute("s_getAlarmListExtended", [])

    def _generate_message_id(self) -> int:
        """Generates the next message ID number to sent request

        Returns:
            int: Message ID number.
        """
        with self._messages_counter_thread_lock:
            self._messages_counter += 1
            return self._messages_counter

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket of a BragerConnect service."""
        if not self._client or not self.connected:
            return
        _LOGGER.info("Disconnecting from BragerConnect service.")
        self._reconnect = False
        self._logged_in = False
        await self._client.close()

    async def __aenter__(self) -> BragerConnect:
        """Async enter.
        Returns:
            The BragerConnect object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.
        Args:
            _exc_info: Exec type.
        """
        await self.disconnect()
