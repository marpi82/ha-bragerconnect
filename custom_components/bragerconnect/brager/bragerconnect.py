"""Asynchronous Python client for BragerConnect."""
from __future__ import annotations

import asyncio
import json
import socket
import logging
import threading
from typing import Any, Optional

from pprint import pformat
import backoff  # pylint: disable=unused-import
import websockets

from .const import HOST, TIMEOUT
from .exceptions import (
    BragerConnectionError,
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

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Main class for handling connections with BragerConnect.

        Args:
            loop (Optional[asyncio.AbstractEventLoop], optional): Event loop. Defaults to None.
        """
        self.host: str = HOST

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

        self._language: Optional[str] = None
        self._active_device_id: Optional[str] = None

    @property
    def connected(self) -> bool:
        """Return if we are connect to the WebSocket of a BragerConnect service.

        Returns:
            bool: True if we are connected to the WebSocket of a BragerConnect service, False otherwise.
        """
        return self._client is not None and not self._client.closed

    @property
    def logged_in(self) -> bool:
        """Returns if we are logged in

        Returns:
            bool: True if we are logged in, otherwise False
        """
        return self._logged_in

    async def connect(self, username: str, password: str, language: str = "en") -> None:
        """Connect to the WebSocket of a BragerConnect service.
        Authenticate user with given credentials, and sets default language

        Args:
            username (str): Username used to login
            password (str): Password used to login
            language (str, optional): language used to get messages / two letter country code. Defaults to "en".

        Raises:
            BragerConnectionError: Error occurred while communicating with the BragerConnect service via the WebSocket.
            BragerAuthError: Error occurred on logging in (wrong username and/or password).
            BragerError: Error occured while setting language.
        """
        if self.connected:
            return

        _LOGGER.info("Connecting to BragerConnect service via WebSocket.")
        try:
            self._client = await websockets.connect(  # pylint: disable=no-member
                uri=self.host
            )
        except (
            websockets.exceptions.InvalidURI,
            websockets.exceptions.InvalidHandshake,
            asyncio.TimeoutError,
            socket.gaierror,
        ) as exception:
            _LOGGER.exception("Error connecting to BragerConnect.")
            raise BragerConnectionError(
                "Error occurred while communicating with BragerConnect service"
                f" on WebSocket at {self.host}"
            ) from exception

        _LOGGER.debug("Waiting for READY_SIGNAL.")
        message = await asyncio.wait_for(self._client.recv(), TIMEOUT)
        _LOGGER.debug("Message received.")
        wrkfnc: dict[str, Any] = json.loads(message)

        if wrkfnc is not None and wrkfnc.get("type") == MessageType.READY_SIGNAL:
            _LOGGER.debug("Got READY_SIGNAL, sending back, connection ready.")
            await self._client.send(message)
        else:
            _LOGGER.exception("Received message is not a READY_SIGNAL, exiting")
            raise BragerConnectionError(
                "Error occurred while communicating with BragerConnect service."
                "READY_SIGNAL was expected."
            )

        _LOGGER.debug("Creating task for received messages processing")
        self._loop.create_task(self._process_messages())

        await self._login(username, password)

        if not self._language:
            if not (
                _language := await self.wrkfnc_set_user_variable(
                    "preffered_lang", language
                )
            ):
                raise BragerError(
                    f"Error setting language ({language}) on BragerConnect service."
                )

            self._language = _language

        if not self._active_device_id:
            await self.wrkfnc_get_active_device_id()

        if not self._device:
            await self.update()

        for device in self._device:
            _LOGGER.debug(
                "Device info: %s, pool(P4.v0=%s), len(task)=%d, len(alarm)=%d",
                device.info.devid,
                device.pool.get_field(4, 0, "v"),
                len(device.task),
                len(device.alarm),
            )
            print(pformat(device.status.get(), indent=4, depth=6))

    async def update(self) -> list[BragerDevice]:
        """Updates all devices existing on BragerConnect service. If the device does not exist, it will be created.

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
        self, device_id: str, device_info: Optional[dict[str, Any]] = None
    ) -> BragerDevice:
        """Updates the device with the given identifier. If the device does not exist, it will be created.

        Args:
            device_id (str): Brager DeviceID
            device_info (Optional[dict[str, Any]], optional): Device info dictionary. Defaults to None.

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

            _data: dict[str, Any] = {"info": _info}
        else:
            _data: dict[str, Any] = {}

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
            self._logged_in = (
                await self.wrkfnc_execute(
                    "s_login",
                    [
                        username,
                        password,
                        None,
                        None,
                        "bc_web",  # IDEA: could be a `bc_web` or `ht_app - what does it mean?
                    ],
                )
                == 1
            )
        except BragerError as exception:
            raise BragerAuthError(
                "Error when logging in (wrong username/password)"
            ) from exception

        return self._logged_in

    async def _process_messages(self) -> None:
        """Main function that processes incoming messages from Websocket."""
        async for message in self._client:
            try:
                wrkfnc: dict[str, Any] = json.loads(message)
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
            except websockets.exceptions.ConnectionClosed:
                continue

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
        """Function to send message. JSON formatted

        Args:
            wrkfnc_name (str): Function name to execute on server
            wrkfnc_args (Optional[list], optional): Function parameters list. Defaults to None.
            wrkfnc_type (MessageType, optional): Message type. Defaults to MessageType.FUNCTION_EXEC.

        Returns:
            int: _description_
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

    async def _wait_wrkfnc(self, message_id: int) -> Any:
        """Function waiting to receive the response to the message with the `message_id`

        Args:
            message_id (int): Message ID number.

        Raises:
            BragerError: Raised when received message is an exception from server.
            BragerError: Raised when timeout was occured.

        Returns:
            Any: (str)      When received message type is MessageType.FUNCTION_RESP,
                 (NoneType) When received message type is not a MessageType.FUNCTION_RESP
        """

        try:
            result: Any = await asyncio.wait_for(
                self._responses.setdefault(message_id, self._loop.create_future()),
                TIMEOUT,
            )
        except asyncio.TimeoutError as exception:
            _LOGGER.exception("Timed out while processing request response.")
            raise BragerError(
                "Timed out while processing request response from BragerConnect service."
            ) from exception
        else:
            wrkfnc_type = result.get("type")
            wrkfnc_resp = result.get("resp")
            if wrkfnc_type == MessageType.EXCEPTION:
                _LOGGER.exception("Error while processing request response.")
                raise BragerError(
                    "Error while processing request response from BragerConnect service."
                )
            elif wrkfnc_type == MessageType.FUNCTION_RESP:
                return wrkfnc_resp
            else:
                return None

    async def wrkfnc_execute(
        self,
        wrkfnc_name: str,
        wrkfnc_args: Optional[list[str]] = None,
        wrkfnc_type: MessageType = MessageType.FUNCTION_EXEC,
    ) -> Any:
        """Function which sends a request to perform request on server side and waits for the response.

        Args:
            wrkfnc_name (str): Function name to execute.
            wrkfnc_args (Optional[list], optional): Function parameters list. Defaults to None.
            wrkfnc_type (MessageType, optional): Message type. Defaults to MessageType.FUNCTION_EXEC.

        Returns:
            Any: Server response
        """
        return await self._wait_wrkfnc(
            await self._send_wrkfnc(wrkfnc_name, wrkfnc_args, wrkfnc_type),
        )

    async def wrkfnc_get_device_id_list(self) -> list[dict[str, Any]]:
        """The function that gets a list of dictionaries with information about devices from the server.

        Returns:
            list[dict[str, Any]]: list of dictionaries with information about devices.
        """
        return await self.wrkfnc_execute(
            "s_getMyDevIdList",
            [],
        )

    async def wrkfnc_get_active_device_id(self) -> str:
        """Function gets the ID of the active device on the server

        Returns:
            str: Active device ID
        """
        _LOGGER.debug("Getting active device id.")
        _device_id = await self.wrkfnc_execute(
            "s_getActiveDevid",
            [],
        )
        device_id = str(_device_id)
        self._active_device_id = device_id
        return device_id

    async def wrkfnc_set_active_device_id(self, device_id: str) -> bool:
        """Function sets the ID of the active device on the server

        Args:
            device_id (str): Device ID to set active

        Returns:
            bool: True if setting was successfull, otherwise False
        """
        _LOGGER.debug("Setting active device id to: %s.", device_id)
        result = (
            await self.wrkfnc_execute(
                "s_setActiveDevid",
                [device_id],
            )
            is True
        )
        self._active_device_id = device_id
        return result

    async def wrkfnc_get_user_variable(self, variable_name: str) -> str:
        """TODO: docstring"""
        return await self.wrkfnc_execute(
            "s_getUserVariable",
            [variable_name],
        )

    async def wrkfnc_set_user_variable(self, variable_name: str, value: str) -> bool:
        """TODO: docstring"""
        return (
            await self.wrkfnc_execute(
                "s_setUserVariable",
                [variable_name, value],
            )
            is None
        )

    async def wrkfnc_get_all_pool_data(self) -> dict[str, Any]:
        """TODO: docstring"""
        _LOGGER.debug("Getting pool data for %s.", self._active_device_id)
        return await self.wrkfnc_execute(
            "s_getAllPoolData",
            [],
        )

    async def wrkfnc_get_task_queue(self) -> dict[str, Any]:
        """TODO: docstring"""
        _LOGGER.debug("Getting tasks data for %s.", self._active_device_id)
        return await self.wrkfnc_execute(
            "s_getTaskQueue",
            [],
        )

    async def wrkfnc_get_alarm_list(self) -> dict[str, Any]:
        """TODO: docstring"""
        _LOGGER.debug("Getting alarms data for %s.", self._active_device_id)
        return await self.wrkfnc_execute(
            "s_getAlarmListExtended",
            [],
        )

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
            _LOGGER.info("disconnecting from BragerConnect service.")
            return

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
