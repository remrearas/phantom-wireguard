"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge.state — State machine for wstunnel-bridge v2.

Mirrors firewall-bridge state.rs pattern but implemented in Python.
State: uninitialized → initialized → started ⇄ stopped → closed

DB is source of truth. Rust FFI is pure runtime (no state).
"""

import logging
import sqlite3
from typing import Optional

from .db import WstunnelDB
from .types import WstunnelError, ErrorCode, LogLevel

_log = logging.getLogger("wstunnel_bridge")


class WstunnelState:
    """DB-backed lifecycle state machine for wstunnel."""

    def __init__(self):
        self._db: Optional[WstunnelDB] = None
        self._client = None  # WstunnelClient instance
        self._server = None  # WstunnelServer instance
        self._status = "uninitialized"
        self._last_error = ""

    # ---- Lifecycle ----

    def init(self, db_path: str, mode: str = "client") -> None:
        """Open DB, create config, state → initialized."""
        if self._status not in ("uninitialized", "closed"):
            self._close_internal()

        try:
            self._db = WstunnelDB(db_path)
        except (OSError, sqlite3.Error) as e:
            raise WstunnelError(ErrorCode.DB_OPEN, str(e))

        self._db.init_config(mode=mode)
        self._db.set_state("initialized")
        self._status = "initialized"
        self._last_error = ""
        _log.info("Initialized: %s (mode=%s)", db_path, mode)

    def start(self, log_level: LogLevel = LogLevel.INFO) -> None:
        """Read config from DB → create client/server → start."""
        if self._status not in ("initialized", "stopped"):
            raise WstunnelError(
                ErrorCode.INVALID_STATE,
                f"Cannot start from '{self._status}'",
            )

        db = self._require_db()
        config = db.get_config()
        mode = config["mode"]

        try:
            if mode == "client":
                self._start_client(db, log_level)
            elif mode == "server":
                self._start_server(db, log_level)
            else:
                raise WstunnelError(ErrorCode.INVALID_PARAM, f"Unknown mode: {mode}")
        except WstunnelError:
            raise
        except (RuntimeError, OSError, ValueError) as e:
            self._last_error = str(e)
            raise WstunnelError(ErrorCode.START_FAILED, str(e))

        db.set_state("started")
        self._status = "started"
        _log.info("Started: mode=%s", mode)

    def stop(self) -> None:
        """Stop client/server → state = stopped."""
        if self._status != "started":
            raise WstunnelError(
                ErrorCode.INVALID_STATE,
                f"Cannot stop from '{self._status}'",
            )

        if self._client is not None:
            try:
                self._client.stop()
            except (WstunnelError, OSError) as e:
                _log.warning("Client stop error: %s", e)
            self._client.free()
            self._client = None

        if self._server is not None:
            try:
                self._server.stop()
            except (WstunnelError, OSError) as e:
                _log.warning("Server stop error: %s", e)
            self._server.free()
            self._server = None

        db = self._require_db()
        db.set_state("stopped")
        self._status = "stopped"
        _log.info("Stopped")

    def close(self) -> None:
        """Stop if started → close DB → state = closed."""
        self._close_internal()

    # ---- Status ----

    def get_status(self) -> dict[str, object]:
        result: dict[str, object] = {
            "status": self._status,
            "last_error": self._last_error,
        }
        if self._db is not None:
            try:
                config = self._db.get_config()
                result["mode"] = config["mode"]
                result["tunnels_count"] = len(self._db.list_tunnels())
                result["restrictions_count"] = len(self._db.list_restrictions())
            except (LookupError, OSError, sqlite3.Error):
                pass

        if self._client is not None:
            try:
                result["is_running"] = self._client.is_running()
                err = self._client.get_last_error()
                if err:
                    result["runtime_error"] = err
            except (WstunnelError, OSError):
                pass

        if self._server is not None:
            try:
                result["is_running"] = self._server.is_running()
                err = self._server.get_last_error()
                if err:
                    result["runtime_error"] = err
            except (WstunnelError, OSError):
                pass

        return result

    @property
    def status(self) -> str:
        return self._status

    def db(self) -> WstunnelDB:
        return self._require_db()

    # ---- Internal: Client Start ----

    def _start_client(self, db: WstunnelDB, log_level: LogLevel) -> None:
        from .client import WstunnelClient

        cfg = db.get_client_config()
        if not cfg["remote_url"]:
            raise WstunnelError(ErrorCode.INVALID_PARAM, "remote_url is required")

        tunnels = db.list_tunnels()
        if not tunnels:
            raise WstunnelError(ErrorCode.INVALID_PARAM, "At least one tunnel is required")

        client = WstunnelClient(cfg["remote_url"], log_level=log_level)

        # Path prefix & credentials
        if cfg["http_upgrade_path_prefix"] != "v1":
            client.set_http_upgrade_path_prefix(cfg["http_upgrade_path_prefix"])
        if cfg["http_upgrade_credentials"]:
            client.set_http_upgrade_credentials(cfg["http_upgrade_credentials"])

        # TLS
        if cfg["tls_verify"]:
            client.set_tls_verify(True)
        if cfg["tls_sni_override"]:
            client.set_tls_sni_override(cfg["tls_sni_override"])
        if cfg["tls_sni_disable"]:
            client.set_tls_sni_disable(True)

        # WebSocket
        if cfg["websocket_ping_frequency"] != 30:
            client.set_websocket_ping_frequency(cfg["websocket_ping_frequency"])
        if cfg["websocket_mask_frame"]:
            client.set_websocket_mask_frame(True)

        # Connection
        if cfg["connection_min_idle"]:
            client.set_connection_min_idle(cfg["connection_min_idle"])
        if cfg["connection_retry_max_backoff"] != 300:
            client.set_connection_retry_max_backoff(cfg["connection_retry_max_backoff"])

        # Proxy
        if cfg["http_proxy"]:
            client.set_http_proxy(cfg["http_proxy"])

        # Workers
        if cfg["worker_threads"] != 2:
            client.set_worker_threads(cfg["worker_threads"])

        # HTTP headers
        for h in db.list_http_headers():
            client.add_http_header(h["name"], h["value"])

        # Tunnel rules
        for t in tunnels:
            if t["tunnel_type"] == "udp":
                client.add_tunnel_udp(
                    t["local_host"], t["local_port"],
                    t["remote_host"], t["remote_port"],
                    timeout_secs=t["timeout_secs"],
                )
            elif t["tunnel_type"] == "tcp":
                client.add_tunnel_tcp(
                    t["local_host"], t["local_port"],
                    t["remote_host"], t["remote_port"],
                )
            elif t["tunnel_type"] == "socks5":
                client.add_tunnel_socks5(
                    t["local_host"], t["local_port"],
                    timeout_secs=t["timeout_secs"],
                )

        client.start()
        self._client = client

    # ---- Internal: Server Start ----

    def _start_server(self, db: WstunnelDB, log_level: LogLevel) -> None:
        from .server import WstunnelServer

        cfg = db.get_server_config()
        if not cfg["bind_url"]:
            raise WstunnelError(ErrorCode.INVALID_PARAM, "bind_url is required")

        server = WstunnelServer(cfg["bind_url"], log_level=log_level)

        # TLS
        if cfg["tls_certificate"]:
            server.set_tls_certificate(cfg["tls_certificate"])
        if cfg["tls_private_key"]:
            server.set_tls_private_key(cfg["tls_private_key"])
        if cfg["tls_client_ca_certs"]:
            server.set_tls_client_ca_certs(cfg["tls_client_ca_certs"])

        # WebSocket
        if cfg["websocket_ping_frequency"] != 30:
            server.set_websocket_ping_frequency(cfg["websocket_ping_frequency"])
        if cfg["websocket_mask_frame"]:
            server.set_websocket_mask_frame(True)

        # Workers
        if cfg["worker_threads"] != 2:
            server.set_worker_threads(cfg["worker_threads"])

        # Restrictions
        for r in db.list_restrictions():
            if r["restriction_type"] == "target":
                server.add_restrict_to(r["value"])
            elif r["restriction_type"] == "path_prefix":
                server.add_restrict_path_prefix(r["value"])

        server.start()
        self._server = server

    # ---- Internal ----

    def _require_db(self) -> WstunnelDB:
        if self._db is None:
            raise WstunnelError(ErrorCode.NOT_INITIALIZED, "DB not open")
        return self._db

    def _close_internal(self) -> None:
        if self._status == "started":
            try:
                self.stop()
            except (WstunnelError, OSError) as e:
                _log.warning("Error during close-stop: %s", e)

        if self._client is not None:
            self._client.free()
            self._client = None

        if self._server is not None:
            self._server.free()
            self._server = None

        if self._db is not None:
            self._db.close()
            self._db = None

        self._status = "closed"
        self._last_error = ""
