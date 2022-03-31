"""Constans for BragerConnect."""

from typing import Optional, Union

HOST: str = "wss://cloud.bragerconnect.com"
TIMEOUT: int = 10


POOLS_TO_PROCESS: set[int] = (4, 5, 6, 7, 8, 10, 11)


JSON_TYPE = Optional[dict[str, Union[list, dict, str]]]  # pylint: disable=invalid-name
DEVICE_INFO_TYPE = Optional[  # pylint: disable=invalid-name
    dict[str, Optional[Union[str, int, bool]]]
]
POOL_DATA = dict[int, dict[int, dict[str, Union[int, float, str]]]]
