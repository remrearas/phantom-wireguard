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

Exception types for wireguard-go-bridge v2.1.0.
Native Python exception hierarchy — no C error code mirroring.
"""


class BridgeError(Exception):
    """Base exception for all bridge operations."""


class TunCreateError(BridgeError):
    """TUN device creation failed."""


class DeviceCreateError(BridgeError):
    """WireGuard device creation failed."""


class IpcError(BridgeError):
    """IPC set/get operation failed."""


class DeviceNotFoundError(BridgeError):
    """Device handle not found."""


class DeviceUpError(BridgeError):
    """Device activation (up) failed."""


class DeviceDownError(BridgeError):
    """Device deactivation (down) failed."""


# Go error code → Python exception mapping
_ERROR_MAP = {
    -2: TunCreateError,
    -3: DeviceCreateError,
    -4: IpcError,
    -5: DeviceNotFoundError,
    -7: DeviceUpError,
    -8: DeviceDownError,
    -99: BridgeError,
}


def check_result(code: int) -> None:
    """Raise appropriate exception if code indicates an error."""
    if code >= 0:
        return
    exc_cls = _ERROR_MAP.get(code, BridgeError)
    raise exc_cls(f"FFI error code: {code}")
