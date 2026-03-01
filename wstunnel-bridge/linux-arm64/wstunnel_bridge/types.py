"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge types — Error codes, log levels, exceptions.
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    # v1 codes (FFI)
    OK = 0
    ALREADY_RUNNING = -1
    INVALID_PARAM = -2
    RUNTIME = -3
    START_FAILED = -4
    NOT_RUNNING = -5
    CONFIG_NULL = -6

    # v2 codes (DB/state)
    DB_OPEN = -10
    DB_QUERY = -11
    DB_WRITE = -12
    INVALID_STATE = -13
    NOT_INITIALIZED = -14


class LogLevel(IntEnum):
    ERROR = 0
    WARN = 1
    INFO = 2
    DEBUG = 3
    TRACE = 4


_ERROR_MESSAGES = {
    ErrorCode.ALREADY_RUNNING: "Client is already running",
    ErrorCode.INVALID_PARAM: "Invalid parameter",
    ErrorCode.RUNTIME: "Tokio runtime error",
    ErrorCode.START_FAILED: "Client start failed",
    ErrorCode.NOT_RUNNING: "Client is not running",
    ErrorCode.CONFIG_NULL: "Config handle is null",
    ErrorCode.DB_OPEN: "Database open failed",
    ErrorCode.DB_QUERY: "Database query failed",
    ErrorCode.DB_WRITE: "Database write failed",
    ErrorCode.INVALID_STATE: "Invalid state transition",
    ErrorCode.NOT_INITIALIZED: "Not initialized",
}


class WstunnelError(Exception):
    """Exception raised by wstunnel bridge operations."""

    def __init__(self, code: int, detail: str = ""):
        try:
            self.code = ErrorCode(code)
        except ValueError:
            self.code = code
        self.detail = detail
        msg = _ERROR_MESSAGES.get(self.code, f"Unknown error ({code})")
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


def check_error(result: int) -> None:
    """Raise WstunnelError if result is non-zero."""
    if result != ErrorCode.OK:
        raise WstunnelError(result)