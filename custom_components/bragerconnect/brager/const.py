"""Asynchronous Python client for BragerConnect."""

HOST: str = "wss://cloud.bragerconnect.com"
TIMEOUT: int = 10


POOLS_TO_PROCESS: set[int] = (4, 5, 6, 7, 8, 10, 11)
