"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Error codes, log levels, and exception types.
Mirrors C error codes from wireguard_go_bridge.h (v2).
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    INVALID_PARAM = -1
    TUN_CREATE = -2
    DEVICE_CREATE = -3
    IPC_SET = -4
    NOT_FOUND = -5
    ALREADY_EXISTS = -6
    DEVICE_UP = -7
    DEVICE_DOWN = -8
    BIND = -9
    KEY_PARSE = -10
    PEER_CREATE = -11
    SESSION = -12
    HANDSHAKE = -13
    COOKIE = -14
    # v2 error codes
    DB_OPEN = -20
    DB_QUERY = -21
    DB_WRITE = -22
    IP_EXHAUSTED = -23
    NOT_INITIALIZED = -24
    STATS_RUNNING = -25
    INTERNAL = -99


class LogLevel(IntEnum):
    SILENT = 0
    ERROR = 1
    VERBOSE = 2


class WireGuardError(Exception):
    _messages = {
        ErrorCode.INVALID_PARAM: "Invalid parameter",
        ErrorCode.TUN_CREATE: "TUN device creation failed",
        ErrorCode.DEVICE_CREATE: "Device creation failed",
        ErrorCode.IPC_SET: "IPC set operation failed",
        ErrorCode.NOT_FOUND: "Handle not found",
        ErrorCode.ALREADY_EXISTS: "Already exists",
        ErrorCode.DEVICE_UP: "Device up failed",
        ErrorCode.DEVICE_DOWN: "Device down failed",
        ErrorCode.BIND: "Bind operation failed",
        ErrorCode.KEY_PARSE: "Key parse failed",
        ErrorCode.PEER_CREATE: "Peer creation failed",
        ErrorCode.SESSION: "Symmetric session failed",
        ErrorCode.HANDSHAKE: "Handshake failed",
        ErrorCode.COOKIE: "Cookie operation failed",
        ErrorCode.DB_OPEN: "Database open failed",
        ErrorCode.DB_QUERY: "Database query failed",
        ErrorCode.DB_WRITE: "Database write failed",
        ErrorCode.IP_EXHAUSTED: "IP pool exhausted",
        ErrorCode.NOT_INITIALIZED: "Bridge not initialized",
        ErrorCode.STATS_RUNNING: "Stats sync already running",
        ErrorCode.INTERNAL: "Internal error",
    }

    def __init__(self, code: int):
        self.code = ErrorCode(code) if code in ErrorCode._value2member_map_ else code
        msg = self._messages.get(self.code, f"Unknown error: {code}")
        super().__init__(msg)


def check_error(result: int) -> None:
    if result != ErrorCode.OK:
        raise WireGuardError(result)
