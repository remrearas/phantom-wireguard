"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

WstunnelBridge — wstunnel server manager, FFI backed, DB persistent.

Usage:
    bridge = WstunnelBridge(db_path)
    bridge.configure(bind_url="wss://[::]:443",
                     restrict_to="127.0.0.1:51820",
                     restrict_path_prefix=secret,
                     tls_certificate=cert, tls_private_key=key)
    bridge.start()

Crash recovery:
    bridge2 = WstunnelBridge(db_path)
    bridge2.start()  # reads config from DB, starts via FFI
"""

from ._ffi import get_lib, _setup_log_callback
from .db import WstunnelDB
from .types import (
    BridgeError,
    ServerStartError,
    ServerNotRunningError,
    AlreadyRunningError,
    ConfigError,
    LogLevel,
    check_error,
)


class WstunnelBridge:
    """wstunnel server manager — FFI backed, DB persistent."""

    __slots__ = ("_db", "_lib", "_config", "_started")

    def __init__(self, db_path: str, log_level: LogLevel = LogLevel.ERROR):
        self._db = WstunnelDB(db_path)
        _setup_log_callback()
        self._lib = get_lib()
        self._lib.wstunnel_init_logging(int(log_level))
        self._config = None
        self._started = False

    def configure(
        self,
        bind_url: str,
        restrict_to: str = "",
        restrict_path_prefix: str = "",
        tls_certificate: str = "",
        tls_private_key: str = "",
    ) -> None:
        """Save server config to DB."""
        self._db.set_config(
            bind_url=bind_url,
            restrict_to=restrict_to,
            restrict_path_prefix=restrict_path_prefix,
            tls_certificate=tls_certificate,
            tls_private_key=tls_private_key,
        )

    def start(self) -> None:
        """Read config from DB -> create FFI server config -> start."""
        if self._started:
            raise AlreadyRunningError("Server already running")

        cfg = self._db.get_config()
        if not cfg.bind_url:
            raise ConfigError("bind_url is required")

        config = self._lib.wstunnel_server_config_new()
        if not config:
            raise ServerStartError("Failed to create server config")

        try:
            check_error(self._lib.wstunnel_server_config_set_bind_url(
                config, cfg.bind_url.encode()))

            if cfg.restrict_to:
                check_error(self._lib.wstunnel_server_config_add_restrict_to(
                    config, cfg.restrict_to.encode()))

            if cfg.restrict_path_prefix:
                check_error(self._lib.wstunnel_server_config_add_restrict_path_prefix(
                    config, cfg.restrict_path_prefix.encode()))

            if cfg.tls_certificate:
                check_error(self._lib.wstunnel_server_config_set_tls_certificate(
                    config, cfg.tls_certificate.encode()))

            if cfg.tls_private_key:
                check_error(self._lib.wstunnel_server_config_set_tls_private_key(
                    config, cfg.tls_private_key.encode()))

            check_error(self._lib.wstunnel_server_start(config))
        except (BridgeError, OSError):
            self._lib.wstunnel_server_config_free(config)
            raise

        self._config = config
        self._started = True
        self._db.set_state("started")

    def stop(self) -> None:
        """FFI stop -> update state."""
        if not self._started:
            raise ServerNotRunningError("Server not running")
        check_error(self._lib.wstunnel_server_stop())
        self._started = False
        self._db.set_state("stopped")

    def is_running(self) -> bool:
        return self._lib.wstunnel_server_is_running() == 1

    def close(self) -> None:
        """Stop (if running) + free config + close DB."""
        if self._started:
            try:
                self.stop()
            except BridgeError:
                pass
        if self._config:
            self._lib.wstunnel_server_config_free(self._config)
            self._config = None
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        if hasattr(self, "_started") and self._started:
            try:
                self.close()
            except (BridgeError, OSError):
                pass
