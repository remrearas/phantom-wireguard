"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

WstunnelServer — High-level Python wrapper for wstunnel bridge server.

Usage:
    server = WstunnelServer("wss://0.0.0.0:8443")
    server.set_tls_certificate("/path/to/cert.pem")
    server.set_tls_private_key("/path/to/key.pem")
    server.add_restrict_to("127.0.0.1:9999")
    server.start()
    # ...
    server.stop()

Or as context manager:
    with WstunnelServer("wss://0.0.0.0:8443") as server:
        server.set_tls_certificate("/path/to/cert.pem")
        server.set_tls_private_key("/path/to/key.pem")
        server.start()
"""

from typing import Optional

from ._ffi import get_lib, _setup_log_callback
from .types import check_error, LogLevel


class WstunnelServer:
    """Wstunnel server managed via native bridge."""

    def __init__(self, bind_url: str, log_level: LogLevel = LogLevel.ERROR):
        _setup_log_callback()
        lib = get_lib()
        self._lib = lib

        # Initialize logging (must be after callback registration)
        lib.wstunnel_init_logging(int(log_level))

        # Create server config
        self._config = lib.wstunnel_server_config_new()
        if not self._config:
            raise RuntimeError("Failed to create wstunnel server config")

        # Set bind URL
        check_error(
            lib.wstunnel_server_config_set_bind_url(self._config, bind_url.encode("utf-8"))
        )

        self._freed = False

    # --- Config ---

    def set_tls_certificate(self, path: str) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_tls_certificate(
                self._config, path.encode("utf-8")
            )
        )

    def set_tls_private_key(self, path: str) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_tls_private_key(
                self._config, path.encode("utf-8")
            )
        )

    def set_tls_client_ca_certs(self, path: str) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_tls_client_ca_certs(
                self._config, path.encode("utf-8")
            )
        )

    def add_restrict_to(self, target: str) -> None:
        check_error(
            self._lib.wstunnel_server_config_add_restrict_to(
                self._config, target.encode("utf-8")
            )
        )

    def add_restrict_path_prefix(self, prefix: str) -> None:
        check_error(
            self._lib.wstunnel_server_config_add_restrict_path_prefix(
                self._config, prefix.encode("utf-8")
            )
        )

    def set_websocket_ping_frequency(self, secs: int) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_websocket_ping_frequency(self._config, secs)
        )

    def set_websocket_mask_frame(self, mask: bool) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_websocket_mask_frame(self._config, mask)
        )

    def set_worker_threads(self, threads: int) -> None:
        check_error(
            self._lib.wstunnel_server_config_set_worker_threads(self._config, threads)
        )

    # --- Server Control ---

    def start(self) -> None:
        check_error(self._lib.wstunnel_server_start(self._config))

    def stop(self) -> None:
        check_error(self._lib.wstunnel_server_stop())

    def is_running(self) -> bool:
        return self._lib.wstunnel_server_is_running() == 1

    def get_last_error(self) -> Optional[str]:
        result = self._lib.wstunnel_server_get_last_error()
        if result:
            return result.decode("utf-8")
        return None

    # --- Cleanup ---

    def free(self) -> None:
        if not self._freed and self._config:
            if self.is_running():
                self.stop()
            self._lib.wstunnel_server_config_free(self._config)
            self._config = None
            self._freed = True

    def __enter__(self) -> "WstunnelServer":
        return self

    def __exit__(self, *exc) -> None:
        self.free()

    def __del__(self) -> None:
        self.free()

    def __repr__(self) -> str:
        state = "freed" if self._freed else ("running" if self.is_running() else "idle")
        return f"WstunnelServer({state})"