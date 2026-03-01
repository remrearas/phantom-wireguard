"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

WstunnelClient — High-level Python wrapper for wstunnel bridge.

Usage:
    client = WstunnelClient("wss://vpn.example.com:443")
    client.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 51820)
    client.set_http_upgrade_path_prefix("secret-path")
    client.start()
    # ...
    client.stop()

Or as context manager:
    with WstunnelClient("wss://vpn.example.com:443") as client:
        client.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 51820)
        client.start()
"""

from typing import Optional

from ._ffi import get_lib, _setup_log_callback
from .types import check_error, LogLevel


class WstunnelClient:
    """Wstunnel client managed via native bridge."""

    def __init__(self, remote_url: str, log_level: LogLevel = LogLevel.ERROR):
        _setup_log_callback()
        lib = get_lib()
        self._lib = lib

        # Initialize logging (must be after callback registration)
        lib.wstunnel_init_logging(int(log_level))

        # Create config
        self._config = lib.wstunnel_config_new()
        if not self._config:
            raise RuntimeError("Failed to create wstunnel config")

        # Set remote URL
        check_error(
            lib.wstunnel_config_set_remote_url(self._config, remote_url.encode("utf-8"))
        )

        self._freed = False

    # --- Config ---

    def set_http_upgrade_path_prefix(self, prefix: str) -> None:
        check_error(
            self._lib.wstunnel_config_set_http_upgrade_path_prefix(
                self._config, prefix.encode("utf-8")
            )
        )

    def set_http_upgrade_credentials(self, credentials: str) -> None:
        check_error(
            self._lib.wstunnel_config_set_http_upgrade_credentials(
                self._config, credentials.encode("utf-8")
            )
        )

    def set_tls_verify(self, verify: bool) -> None:
        check_error(
            self._lib.wstunnel_config_set_tls_verify(self._config, verify)
        )

    def set_tls_sni_override(self, domain: str) -> None:
        check_error(
            self._lib.wstunnel_config_set_tls_sni_override(
                self._config, domain.encode("utf-8")
            )
        )

    def set_tls_sni_disable(self, disable: bool) -> None:
        check_error(
            self._lib.wstunnel_config_set_tls_sni_disable(self._config, disable)
        )

    def set_websocket_ping_frequency(self, secs: int) -> None:
        check_error(
            self._lib.wstunnel_config_set_websocket_ping_frequency(self._config, secs)
        )

    def set_websocket_mask_frame(self, mask: bool) -> None:
        check_error(
            self._lib.wstunnel_config_set_websocket_mask_frame(self._config, mask)
        )

    def set_connection_min_idle(self, count: int) -> None:
        check_error(
            self._lib.wstunnel_config_set_connection_min_idle(self._config, count)
        )

    def set_connection_retry_max_backoff(self, secs: int) -> None:
        check_error(
            self._lib.wstunnel_config_set_connection_retry_max_backoff(self._config, secs)
        )

    def set_http_proxy(self, proxy: str) -> None:
        check_error(
            self._lib.wstunnel_config_set_http_proxy(
                self._config, proxy.encode("utf-8")
            )
        )

    def add_http_header(self, name: str, value: str) -> None:
        check_error(
            self._lib.wstunnel_config_add_http_header(
                self._config, name.encode("utf-8"), value.encode("utf-8")
            )
        )

    def set_worker_threads(self, threads: int) -> None:
        check_error(
            self._lib.wstunnel_config_set_worker_threads(self._config, threads)
        )

    # --- Tunnel Rules ---

    def add_tunnel_udp(
        self,
        local_host: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
        timeout_secs: int = 0,
    ) -> None:
        check_error(
            self._lib.wstunnel_config_add_tunnel_udp(
                self._config,
                local_host.encode("utf-8"),
                local_port,
                remote_host.encode("utf-8"),
                remote_port,
                timeout_secs,
            )
        )

    def add_tunnel_tcp(
        self,
        local_host: str,
        local_port: int,
        remote_host: str,
        remote_port: int,
    ) -> None:
        check_error(
            self._lib.wstunnel_config_add_tunnel_tcp(
                self._config,
                local_host.encode("utf-8"),
                local_port,
                remote_host.encode("utf-8"),
                remote_port,
            )
        )

    def add_tunnel_socks5(
        self,
        local_host: str,
        local_port: int,
        timeout_secs: int = 0,
    ) -> None:
        check_error(
            self._lib.wstunnel_config_add_tunnel_socks5(
                self._config,
                local_host.encode("utf-8"),
                local_port,
                timeout_secs,
            )
        )

    # --- Client Control ---

    def start(self) -> None:
        check_error(self._lib.wstunnel_client_start(self._config))

    def stop(self) -> None:
        check_error(self._lib.wstunnel_client_stop())

    def is_running(self) -> bool:
        return self._lib.wstunnel_client_is_running() == 1

    def get_last_error(self) -> Optional[str]:
        result = self._lib.wstunnel_client_get_last_error()
        if result:
            return result.decode("utf-8")
        return None

    # --- Cleanup ---

    def free(self) -> None:
        if not self._freed and self._config:
            if self.is_running():
                self.stop()
            self._lib.wstunnel_config_free(self._config)
            self._config = None
            self._freed = True

    def __enter__(self) -> "WstunnelClient":
        return self

    def __exit__(self, *exc) -> None:
        self.free()

    def __del__(self) -> None:
        self.free()

    def __repr__(self) -> str:
        state = "freed" if self._freed else ("running" if self.is_running() else "idle")
        return f"WstunnelClient({state})"