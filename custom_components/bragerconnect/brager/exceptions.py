"""Exceptions for BragerConnect."""


class BragerConnectionError(Exception):
    """Raised when something is wrong with WebSocket connection"""


class BragerAuthError(Exception):
    """Raised when authentication fails"""


class BragerError(Exception):
    """Raised when error with API occurs"""
