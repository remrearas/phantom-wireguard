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

BridgeClient — high-level Python interface to bridge-db.
Manages WireGuard device lifecycle, client CRUD, multihop tunnels,
server config, and stats sync through the Go FFI bridge.
"""

import ctypes
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from dataclasses import fields

from ._ffi import get_lib, LOG_CALLBACK_TYPE
from .types import WireGuardError, ErrorCode, check_error

import wireguard_go_bridge._ffi as _ffi_mod

bridge_logger = logging.getLogger("wireguard_go_bridge.native")


@dataclass
class ClientInfo:
    id: int = 0
    public_key: str = ""
    preshared_key: str = ""
    private_key: str = ""
    allowed_ip: str = ""
    allowed_ip_v6: str = ""
    keepalive: int = 25
    enabled: bool = True
    created_at: int = 0
    endpoint: Optional[str] = None
    last_handshake: Optional[int] = None
    rx_bytes: int = 0
    tx_bytes: int = 0


@dataclass
class DeviceInfo:
    name: str = ""
    public_key: str = ""
    listen_port: int = 0
    peer_count: int = 0
    started_at: Optional[int] = None


@dataclass
class ServerConfig:
    device_id: int = 1
    endpoint: str = ""
    endpoint_v6: str = ""
    network: str = "10.8.0.0/24"
    network_v6: str = ""
    dns_primary: str = "1.1.1.1"
    dns_secondary: str = "9.9.9.9"
    dns_v6: str = ""
    mtu: int = 1420
    fwmark: int = 0
    post_up: str = ""
    post_down: str = ""


@dataclass
class MultihopTunnel:
    id: int = 0
    name: str = ""
    enabled: bool = False
    interface_name: str = ""
    listen_port: int = 0
    private_key: str = ""
    public_key: str = ""
    remote_endpoint: str = ""
    remote_public_key: str = ""
    remote_preshared_key: str = ""
    remote_allowed_ips: str = "0.0.0.0/0"
    remote_keepalive: int = 25
    fwmark: int = 0
    routing_table: str = "phantom_multihop"
    routing_table_id: int = 100
    priority: int = 100
    status: str = "stopped"
    error_msg: str = ""
    started_at: Optional[int] = None
    created_at: int = 0


@dataclass
class ClientList:
    clients: list = field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 50


def _decode_and_free(result) -> str:
    """Decode a C string result and free the Go-allocated memory."""
    if not result:
        return ""
    if isinstance(result, int):
        # c_void_p returns int — cast to read, then free
        ptr = ctypes.cast(result, ctypes.c_char_p)
        text = ptr.value.decode("utf-8") if ptr.value else ""
        get_lib().FreeString(ptr)
        return text
    if isinstance(result, bytes):
        return result.decode("utf-8")
    return str(result)


def _parse_json(result) -> dict:
    raw = _decode_and_free(result)
    if not raw:
        raise WireGuardError(ErrorCode.INTERNAL)
    return json.loads(raw)


def _to_dataclass(cls, data: dict):
    """Create a dataclass instance from dict, ignoring unknown keys."""
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


def _encode(s: str) -> bytes:
    return s.encode("utf-8") if s else b""


class BridgeClient:
    """High-level Python interface to wireguard-go-bridge v2 (bridge-db)."""

    def __init__(self, db_path: str, ifname: str = "wg0",
                 listen_port: int = 51820, log_level: int = 1):
        self._lib = get_lib()
        self._setup_log_callback()
        result = self._lib.BridgeInit(
            _encode(db_path), _encode(ifname), listen_port, log_level
        )
        check_error(result)

    @staticmethod
    def _setup_log_callback():
        """Route Go bridge logs to Python logging."""
        if _ffi_mod._active_log_callback is not None:
            return

        def _on_log(level, message, _context):
            msg = message.decode("utf-8", errors="replace") if message else ""
            if level == 1:
                bridge_logger.error(msg)
            elif level == 2:
                bridge_logger.debug(msg)

        cb = LOG_CALLBACK_TYPE(_on_log)
        _ffi_mod._active_log_callback = cb  # prevent GC
        get_lib().BridgeSetLogCallback(cb, None)

    def close(self) -> None:
        check_error(self._lib.BridgeClose())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- Status & Setup ----

    def get_status(self) -> dict:
        return _parse_json(self._lib.BridgeGetStatus())

    def setup(self, endpoint: str = "", network: str = "",
              dns_primary: str = "", dns_secondary: str = "",
              mtu: int = 0, fwmark: int = 0) -> None:
        check_error(self._lib.BridgeSetup(
            _encode(endpoint), _encode(network),
            _encode(dns_primary), _encode(dns_secondary),
            mtu, fwmark
        ))

    # ---- Device Lifecycle ----

    def start(self) -> None:
        check_error(self._lib.BridgeStart())

    def stop(self) -> None:
        check_error(self._lib.BridgeStop())

    def get_device_info(self) -> DeviceInfo:
        data = _parse_json(self._lib.BridgeGetDeviceInfo())
        return DeviceInfo(**data)

    # ---- Client Management ----

    def add_client(self, allowed_ip: str = "") -> ClientInfo:
        data = _parse_json(self._lib.BridgeAddClient(_encode(allowed_ip)))
        return _to_dataclass(ClientInfo, data)

    def remove_client(self, pub_key: str) -> None:
        check_error(self._lib.BridgeRemoveClient(_encode(pub_key)))

    def enable_client(self, pub_key: str) -> None:
        check_error(self._lib.BridgeEnableClient(_encode(pub_key)))

    def disable_client(self, pub_key: str) -> None:
        check_error(self._lib.BridgeDisableClient(_encode(pub_key)))

    def get_client(self, pub_key: str) -> ClientInfo:
        data = _parse_json(self._lib.BridgeGetClient(_encode(pub_key)))
        return _to_dataclass(ClientInfo, data)

    def list_clients(self, page: int = 1, limit: int = 50) -> ClientList:
        data = _parse_json(self._lib.BridgeListClients(page, limit))
        clients = [_to_dataclass(ClientInfo, c)
                    for c in data.get("clients", [])]
        return ClientList(clients=clients, total=data["total"], page=data["page"], limit=data["limit"])

    def export_client_config(self, pub_key: str,
                              server_endpoint: str = "",
                              dns: str = "") -> str:
        result = self._lib.BridgeExportClientConfig(
            _encode(pub_key), _encode(server_endpoint), _encode(dns)
        )
        text = _decode_and_free(result)
        if not text:
            raise WireGuardError(ErrorCode.NOT_FOUND)
        return text

    # ---- Server Config ----

    def get_server_config(self) -> ServerConfig:
        data = _parse_json(self._lib.BridgeGetServerConfig())
        return _to_dataclass(ServerConfig, data)

    def set_server_config(self, config: ServerConfig) -> None:
        from dataclasses import asdict
        check_error(self._lib.BridgeSetServerConfig(
            json.dumps(asdict(config)).encode("utf-8")
        ))

    # ---- Stats Sync ----

    def start_stats_sync(self, interval_sec: int = 30) -> None:
        check_error(self._lib.BridgeStartStatsSync(interval_sec))

    def stop_stats_sync(self) -> None:
        check_error(self._lib.BridgeStopStatsSync())

    # ---- Multihop Tunnels ----

    def create_multihop_tunnel(self, name: str, iface_name: str,
                                remote_endpoint: str, remote_pub_key: str,
                                fwmark: int = 0) -> MultihopTunnel:
        data = _parse_json(self._lib.BridgeCreateMultihopTunnel(
            _encode(name), _encode(iface_name),
            _encode(remote_endpoint), _encode(remote_pub_key), fwmark
        ))
        return _to_dataclass(MultihopTunnel, data)

    def start_multihop_tunnel(self, name: str) -> None:
        check_error(self._lib.BridgeStartMultihopTunnel(_encode(name)))

    def stop_multihop_tunnel(self, name: str) -> None:
        check_error(self._lib.BridgeStopMultihopTunnel(_encode(name)))

    def disable_multihop_tunnel(self, name: str) -> None:
        check_error(self._lib.BridgeDisableMultihopTunnel(_encode(name)))

    def delete_multihop_tunnel(self, name: str) -> None:
        check_error(self._lib.BridgeDeleteMultihopTunnel(_encode(name)))

    def list_multihop_tunnels(self) -> list[MultihopTunnel]:
        data = _parse_json(self._lib.BridgeListMultihopTunnels())
        if isinstance(data, list):
            return [_to_dataclass(MultihopTunnel, t)
                    for t in data]
        return []

    def get_multihop_tunnel(self, name: str) -> MultihopTunnel:
        data = _parse_json(self._lib.BridgeGetMultihopTunnel(_encode(name)))
        return _to_dataclass(MultihopTunnel, data)
