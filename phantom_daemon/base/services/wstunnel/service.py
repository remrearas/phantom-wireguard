"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel service lifecycle — bridge wrapper, config persistence.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Type

from wstunnel_bridge import WstunnelBridge
from wstunnel_bridge.models import ServerConfig

from phantom_daemon.base.errors import WstunnelError

log = logging.getLogger("phantom-daemon")


class WstunnelService:
    """wstunnel bridge lifecycle and configuration."""

    __slots__ = ("_bridge", "_db_path")

    def __init__(self, bridge: WstunnelBridge, db_path: Path) -> None:
        self._bridge = bridge
        self._db_path = db_path

    # ── Lifecycle ────────────────────────────────────────────────

    def configure(
        self,
        bind_url: str,
        restrict_to: str,
        restrict_path_prefix: str,
        tls_certificate: str,
        tls_private_key: str,
    ) -> None:
        """Save server config to bridge DB."""
        self._bridge.configure(
            bind_url=bind_url,
            restrict_to=restrict_to,
            restrict_path_prefix=restrict_path_prefix,
            tls_certificate=tls_certificate,
            tls_private_key=tls_private_key,
        )

    def start(self) -> None:
        """Start wstunnel server from persisted config."""
        self._bridge.start()
        log.info("wstunnel: started")

    def stop(self) -> None:
        """Stop wstunnel server."""
        self._bridge.stop()
        log.info("wstunnel: stopped")

    def close(self) -> None:
        """Stop (if running) and release resources."""
        self._bridge.close()

    def is_running(self) -> bool:
        return self._bridge.is_running()

    # noinspection PyUnresolvedReferences
    def was_running(self) -> bool:
        """Check if bridge DB state indicates a previous running session."""
        # noinspection PyProtectedMember
        return self._bridge._db.get_state() == "started"

    # ── Read Operations ──────────────────────────────────────────

    # noinspection PyUnresolvedReferences
    def get_config(self) -> ServerConfig:
        """Return current config from bridge DB."""
        # noinspection PyProtectedMember
        return self._bridge._db.get_config()

    # ── Context Manager ──────────────────────────────────────────

    def __enter__(self) -> WstunnelService:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        self.close()


# ── Factory ──────────────────────────────────────────────────────


def open_wstunnel(state_dir: str) -> WstunnelService:
    """Instantiate wstunnel bridge with its own DB, return service."""
    dir_path = Path(state_dir)
    if not dir_path.is_dir():
        raise WstunnelError(f"State directory does not exist: {state_dir}")

    db_path = dir_path / "wstunnel.db"

    try:
        bridge = WstunnelBridge(str(db_path))
    except Exception as exc:
        raise WstunnelError(
            f"Failed to create wstunnel bridge: {exc}"
        ) from exc

    return WstunnelService(bridge=bridge, db_path=db_path)