"""
Error types and enums for firewall_bridge.
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    ALREADY_INITIALIZED = -1
    NOT_INITIALIZED = -2
    NFT_FAILED = -3
    NETLINK_FAILED = -4
    INVALID_PARAM = -5
    IO_ERROR = -6
    PERMISSION_DENIED = -7


class AddressFamily(IntEnum):
    INET = 2     # AF_INET  (IPv4)
    INET6 = 10   # AF_INET6 (IPv6)


class FirewallBridgeError(Exception):
    """Raised when a firewall bridge operation fails."""

    def __init__(self, code: int, detail: str = ""):
        try:
            self.code = ErrorCode(code)
        except ValueError:
            self.code = code  # type: ignore[assignment]
        self.detail = detail

    def __str__(self) -> str:
        msg = f"FirewallBridgeError({self.code.name if isinstance(self.code, ErrorCode) else self.code})"
        if self.detail:
            msg += f": {self.detail}"
        return msg


def check_error(rc: int) -> None:
    """Raise FirewallBridgeError if rc is not OK."""
    if rc != 0:
        from ._ffi import get_lib
        lib = get_lib()
        detail_ptr = lib.firewall_bridge_get_last_error()
        detail = detail_ptr.decode("utf-8") if detail_ptr else ""
        raise FirewallBridgeError(rc, detail)