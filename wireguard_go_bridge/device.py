"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
WireGuardDevice — High-level Python wrapper for wireguard-go Device.

Mirrors the wstunnel WstunnelBridge.Config pattern:
- Swift OpaquePointer  → Python int64 handle
- Swift deinit         → Python __del__ / __exit__
- Swift @discardableResult method chaining → Python fluent API
"""

from typing import Optional, List

from ._ffi import get_lib
from .types import WireGuardError, LogLevel, ErrorCode, check_error


class WireGuardPeer:
    """Handle to a wireguard-go Peer object."""

    def __init__(self, handle: int, device: "WireGuardDevice"):
        self._handle = handle
        self._device = device

    @property
    def handle(self) -> int:
        return self._handle

    def start(self) -> None:
        check_error(get_lib().PeerStart(self._handle))

    def stop(self) -> None:
        check_error(get_lib().PeerStop(self._handle))

    def string(self) -> str:
        result = get_lib().PeerString(self._handle)
        return result.decode("utf-8") if result else ""

    def send_handshake_initiation(self, is_retry: bool = False) -> None:
        check_error(get_lib().PeerSendHandshakeInitiation(self._handle, is_retry))

    def send_handshake_response(self) -> None:
        check_error(get_lib().PeerSendHandshakeResponse(self._handle))

    def begin_symmetric_session(self) -> None:
        check_error(get_lib().PeerBeginSymmetricSession(self._handle))

    def send_keepalive(self) -> None:
        check_error(get_lib().PeerSendKeepalive(self._handle))

    def send_staged_packets(self) -> None:
        check_error(get_lib().PeerSendStagedPackets(self._handle))

    def expire_current_keypairs(self) -> None:
        check_error(get_lib().PeerExpireCurrentKeypairs(self._handle))

    def flush_staged_packets(self) -> None:
        check_error(get_lib().PeerFlushStagedPackets(self._handle))

    def zero_and_flush_all(self) -> None:
        check_error(get_lib().PeerZeroAndFlushAll(self._handle))

    def free(self) -> None:
        if self._handle:
            get_lib().PeerFree(self._handle)
            self._handle = 0

    def __repr__(self) -> str:
        return f"WireGuardPeer(handle={self._handle})"


class WireGuardDevice:
    """
    WireGuard device managed via wireguard-go native bridge.

    Usage:
        with WireGuardDevice("wg0", mtu=1420) as dev:
            dev.ipc_set("private_key=...\\nlisten_port=51820\\n")
            dev.up()
            config = dev.ipc_get()

    Or without context manager:
        dev = WireGuardDevice("wg0")
        try:
            dev.up()
        finally:
            dev.close()
    """

    def __init__(
        self,
        interface_name: str,
        mtu: int = 1420,
        log_level: LogLevel = LogLevel.ERROR,
        log_prepend: str = "",
    ):
        lib = get_lib()
        self._lib = lib

        # Create logger
        self._logger_handle = lib.NewLogger(
            int(log_level), log_prepend.encode("utf-8")
        )

        # Create device (TUN + bind created internally)
        self._handle = lib.NewDevice(
            interface_name.encode("utf-8"),
            mtu,
            self._logger_handle,
        )
        if self._handle < 0:
            lib.LoggerFree(self._logger_handle)
            raise WireGuardError(self._handle)

        self._interface_name = interface_name
        self._closed = False

    @property
    def handle(self) -> int:
        return self._handle

    @property
    def interface_name(self) -> str:
        return self._interface_name

    # --- Lifecycle ---

    def up(self) -> None:
        check_error(self._lib.DeviceUp(self._handle))

    def down(self) -> None:
        check_error(self._lib.DeviceDown(self._handle))

    def close(self) -> None:
        if not self._closed and self._handle > 0:
            self.uapi_close()
            self._lib.DeviceClose(self._handle)
            self._lib.LoggerFree(self._logger_handle)
            self._closed = True

    def wait(self) -> None:
        """Block until device is closed."""
        check_error(self._lib.DeviceWait(self._handle))

    # --- UAPI Socket ---

    def uapi_listen(self) -> None:
        """Start UAPI socket listener. wg tool communicates via this socket."""
        check_error(
            self._lib.DeviceUAPIListen(self._handle, self._interface_name.encode("utf-8"))
        )

    def uapi_close(self) -> None:
        """Stop UAPI socket listener and remove socket file."""
        self._lib.DeviceUAPIClose(self._handle, self._interface_name.encode("utf-8"))

    # --- IPC (UAPI Protocol) ---

    def ipc_set(self, config: str) -> None:
        check_error(self._lib.DeviceIpcSet(self._handle, config.encode("utf-8")))

    def ipc_get(self) -> str:
        result = self._lib.DeviceIpcGet(self._handle)
        if result is None:
            raise WireGuardError(ErrorCode.NOT_FOUND)
        return result.decode("utf-8")

    def ipc_set_operation(self, config: str) -> int:
        """IpcSet with detailed IPC error code return."""
        return self._lib.DeviceIpcSetOperation(
            self._handle, config.encode("utf-8")
        )

    # --- Bind ---

    def bind_close(self) -> None:
        check_error(self._lib.DeviceBindClose(self._handle))

    def bind_update(self) -> None:
        check_error(self._lib.DeviceBindUpdate(self._handle))

    def bind_set_mark(self, mark: int) -> None:
        check_error(self._lib.DeviceBindSetMark(self._handle, mark))

    # --- State ---

    def batch_size(self) -> int:
        return self._lib.DeviceBatchSize(self._handle)

    def is_under_load(self) -> bool:
        return self._lib.DeviceIsUnderLoad(self._handle)

    # --- Key Management ---

    def set_private_key(self, hex_key: str) -> None:
        check_error(
            self._lib.DeviceSetPrivateKey(self._handle, hex_key.encode("utf-8"))
        )

    # --- Peer Management ---

    def new_peer(self, public_key_hex: str) -> WireGuardPeer:
        handle = self._lib.DeviceNewPeer(
            self._handle, public_key_hex.encode("utf-8")
        )
        if handle < 0:
            raise WireGuardError(handle)
        return WireGuardPeer(handle, self)

    def lookup_peer(self, public_key_hex: str) -> Optional[WireGuardPeer]:
        handle = self._lib.DeviceLookupPeer(
            self._handle, public_key_hex.encode("utf-8")
        )
        if handle <= 0:
            return None
        return WireGuardPeer(handle, self)

    def remove_peer(self, public_key_hex: str) -> None:
        check_error(
            self._lib.DeviceRemovePeer(self._handle, public_key_hex.encode("utf-8"))
        )

    def remove_all_peers(self) -> None:
        check_error(self._lib.DeviceRemoveAllPeers(self._handle))

    # --- AllowedIPs ---

    def allowed_ips_insert(self, peer: WireGuardPeer, prefix: str) -> None:
        check_error(
            self._lib.AllowedIpsInsert(
                self._handle, peer.handle, prefix.encode("utf-8")
            )
        )

    def allowed_ips_remove_by_peer(self, peer: WireGuardPeer) -> None:
        check_error(
            self._lib.AllowedIpsRemoveByPeer(self._handle, peer.handle)
        )

    def allowed_ips_entries_for_peer(self, peer: WireGuardPeer) -> List[str]:
        result = self._lib.AllowedIpsGetForPeer(self._handle, peer.handle)
        if not result:
            return []
        text = result.decode("utf-8")
        return text.split("\n") if text else []

    # --- Miscellaneous ---

    def populate_pools(self) -> None:
        check_error(self._lib.DevicePopulatePools(self._handle))

    def disable_roaming(self) -> None:
        check_error(self._lib.DeviceDisableRoaming(self._handle))

    def send_keepalives_to_peers(self) -> None:
        check_error(self._lib.DeviceSendKeepalivesToPeers(self._handle))

    # --- Context Manager (RAII) ---

    def __enter__(self) -> "WireGuardDevice":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "closed" if self._closed else "open"
        return f"WireGuardDevice('{self._interface_name}', handle={self._handle}, {state})"