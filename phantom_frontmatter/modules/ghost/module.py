"""
Phantom-WG Frontmatter — Ghost Module

Runtime lifecycle for the compact wstunnel + socat-egress pair that
makes up the Ghost Mode data path. The setup module owns the
bootstrap (cert, binary, secret, systemd unit rendering); ghost
just turns the resulting services on, off, and queries them.

Service binding model
    The wstunnel systemd unit declares
    ``Requires=phantom-frontmatter-ghost-egress.service``,
    ``After=phantom-frontmatter-ghost-egress.service``,
    and ``BindsTo=phantom-frontmatter-ghost-egress.service``. That
    means:

        - ``systemctl enable --now ghost-wstunnel`` automatically
          pulls in egress (Requires + After).
        - ``systemctl stop ghost-egress`` cascades into wstunnel
          (BindsTo).

    So ghost only ever talks to the wstunnel unit by name; the
    egress unit follows along automatically. The operator
    interacts with one logical thing.

State principle
    Ghost reads parameters from the ``setup`` and ``ghost`` SQLite
    tables on demand. It never caches them, never duplicates them,
    and never writes "is the service running" back to disk —
    ``systemctl is-active`` is the source of truth for that.

Actions:
    start         — bring the data path up (pre-flights then enable+start)
    stop          — bring the data path down (BindsTo cascades egress)
    restart       — explicit ordering: egress first, wstunnel second
    status        — combine systemctl + KV reads, no writes
    client_config — emit the [Wstunnel] block clients paste into .conf

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

from pathlib import Path
from typing import Any, Callable, Dict

from phantom_frontmatter.api.exceptions import (
    ConfigurationError,
    GhostError,
)
from phantom_frontmatter.modules.base import BaseModule


class GhostModule(BaseModule):
    """Runtime lifecycle for the wstunnel + egress pair."""

    EGRESS_SERVICE = "phantom-frontmatter-ghost-egress.service"
    WSTUNNEL_SERVICE = "phantom-frontmatter-ghost-wstunnel.service"

    # Loopback constants — must match what setup writes into the
    # rendered systemd units. The client_config snippet uses these
    # so the .conf file the operator hands out is byte-identical to
    # what wstunnel actually expects.
    LOOPBACK_HOST = "127.0.0.1"
    LOOPBACK_PORT = 51820

    # Public-IP placeholder. The operator replaces this with the
    # front host's public address before handing the snippet to a
    # client.
    PUBLIC_HOST_PLACEHOLDER = "<FRONTMATTER-PUBLIC-IP>"

    def get_module_name(self) -> str:
        return "ghost"

    def get_module_description(self) -> str:
        return (
            "Runtime lifecycle for the wstunnel + socat egress data "
            "path. setup owns bootstrap; ghost owns start/stop and "
            "client config emission."
        )

    def get_actions(self) -> Dict[str, Callable]:
        return {
            "start": self.start,
            "stop": self.stop,
            "restart": self.restart,
            "status": self.status,
            "client_config": self.client_config,
            "client_command": self.client_command,
        }

    # ── Pre-flight ──────────────────────────────────────────────

    def _setup_table(self):
        return self.foreign_store("setup")

    def _ensure_initialized(self) -> Dict[str, str]:
        """Verify setup has been run; return the setup table contents.

        Raises ConfigurationError with a clear next step if any of
        the prerequisites are missing.
        """
        setup = self._setup_table().items()
        if "initialized_at" not in setup:
            raise ConfigurationError(
                "Setup has not been initialized. Run "
                "'frontmatter-api setup init backend=<IP[:PORT]>' "
                "first."
            )
        # Sanity-check the on-disk artifacts that setup is supposed
        # to have produced. If any of these are missing the state DB
        # is lying to us — tell the operator how to recover.
        cert = Path(setup.get("tls_cert_path", ""))
        key = Path(setup.get("tls_key_path", ""))
        binary = Path(setup.get("wstunnel_binary_path", ""))
        missing = [
            label for label, path in (
                ("cert", cert), ("key", key), ("binary", binary),
            ) if not path.exists()
        ]
        if missing:
            raise ConfigurationError(
                f"Setup state is corrupt: missing {missing}. "
                "Run 'frontmatter-api setup clean yes=true' followed "
                "by 'frontmatter-api setup init backend=...'."
            )
        return setup

    # ── start ───────────────────────────────────────────────────

    def start(self, **_: Any) -> Dict[str, Any]:
        """Enable + start the ghost data path.

        ``systemctl enable --now ghost-wstunnel`` pulls in
        ghost-egress automatically through the unit's Requires=/After=
        directives. Operator only ever has to think about one unit.
        """
        self._ensure_initialized()

        if not self._systemctl_enable_start(self.WSTUNNEL_SERVICE):
            raise GhostError(f"Failed to start {self.WSTUNNEL_SERVICE}")

        return {
            "success": True,
            "wstunnel": {
                "name": self.WSTUNNEL_SERVICE,
                "active": self._systemctl_is_active(self.WSTUNNEL_SERVICE),
                "enabled": self._systemctl_is_enabled(self.WSTUNNEL_SERVICE),
            },
            "egress": {
                "name": self.EGRESS_SERVICE,
                "active": self._systemctl_is_active(self.EGRESS_SERVICE),
                "enabled": self._systemctl_is_enabled(self.EGRESS_SERVICE),
            },
        }

    # ── stop ────────────────────────────────────────────────────

    def stop(self, **_: Any) -> Dict[str, Any]:
        """Disable + stop the ghost data path.

        Stopping the wstunnel unit cascades to egress through the
        wstunnel unit's ``BindsTo=ghost-egress`` directive. Both
        units are explicitly disabled so neither auto-starts on the
        next boot.
        """
        self._systemctl_disable_stop(self.WSTUNNEL_SERVICE)
        self._systemctl("disable", self.EGRESS_SERVICE)

        return {
            "success": True,
            "wstunnel": {
                "name": self.WSTUNNEL_SERVICE,
                "active": self._systemctl_is_active(self.WSTUNNEL_SERVICE),
                "enabled": self._systemctl_is_enabled(self.WSTUNNEL_SERVICE),
            },
            "egress": {
                "name": self.EGRESS_SERVICE,
                "active": self._systemctl_is_active(self.EGRESS_SERVICE),
                "enabled": self._systemctl_is_enabled(self.EGRESS_SERVICE),
            },
        }

    # ── restart ─────────────────────────────────────────────────

    def restart(self, **_: Any) -> Dict[str, Any]:
        """Restart the data path with explicit ordering: egress first,
        then wstunnel. Both processes are refreshed atomically so a
        cert / config swap on disk takes effect on both ends in the
        same operation.
        """
        self._ensure_initialized()

        egress_restart = self._systemctl("restart", self.EGRESS_SERVICE)
        if not egress_restart["success"]:
            raise GhostError(
                f"Failed to restart {self.EGRESS_SERVICE}: "
                f"{egress_restart['stderr']}"
            )

        wstunnel_restart = self._systemctl("restart", self.WSTUNNEL_SERVICE)
        if not wstunnel_restart["success"]:
            raise GhostError(
                f"Failed to restart {self.WSTUNNEL_SERVICE}: "
                f"{wstunnel_restart['stderr']}"
            )

        return {
            "success": True,
            "wstunnel": {
                "name": self.WSTUNNEL_SERVICE,
                "active": self._systemctl_is_active(self.WSTUNNEL_SERVICE),
            },
            "egress": {
                "name": self.EGRESS_SERVICE,
                "active": self._systemctl_is_active(self.EGRESS_SERVICE),
            },
        }

    # ── status ──────────────────────────────────────────────────

    def status(self, **_: Any) -> Dict[str, Any]:
        """Combine systemctl queries with the parameters in the
        setup + ghost tables. Read-only, no writes.
        """
        setup = self._setup_table().items()
        ghost = self.store.items()

        initialized = "initialized_at" in setup

        return {
            "initialized": initialized,
            "wstunnel": {
                "name": self.WSTUNNEL_SERVICE,
                "active": self._systemctl_is_active(self.WSTUNNEL_SERVICE),
                "enabled_on_boot": self._systemctl_is_enabled(self.WSTUNNEL_SERVICE),
            },
            "egress": {
                "name": self.EGRESS_SERVICE,
                "active": self._systemctl_is_active(self.EGRESS_SERVICE),
                "enabled_on_boot": self._systemctl_is_enabled(self.EGRESS_SERVICE),
            },
            "parameters": {
                "wstunnel_listen_port": _maybe_int(ghost.get("wstunnel_listen_port")),
                "loopback_port": _maybe_int(ghost.get("loopback_port")),
                "wstunnel_secret_set": "wstunnel_secret" in ghost,
                "wstunnel_version": setup.get("wstunnel_version"),
                "tls_cert_path": setup.get("tls_cert_path"),
                "tls_key_path": setup.get("tls_key_path"),
                # Backend address is read via 'setup status'.
            },
        }

    # ── client_config ───────────────────────────────────────────

    def client_config(self, **_: Any) -> Dict[str, Any]:
        """Emit the [Wstunnel] snippet operators paste into .conf files.

        The snippet is derived from primitive parameters in the ghost
        table. The remote host is the loopback constant; the public
        host is a placeholder the operator fills in.
        """
        secret = self.store.get("wstunnel_secret")
        listen_port = self.store.get_int("wstunnel_listen_port")
        loopback_port = self.store.get_int(
            "loopback_port", default=self.LOOPBACK_PORT,
        )

        if not secret or listen_port is None:
            raise ConfigurationError(
                "Ghost has no secret / listen port stored. Run "
                "'frontmatter-api setup init backend=<IP[:PORT]>' first."
            )

        url = f"wss://{self.PUBLIC_HOST_PLACEHOLDER}:{listen_port}"
        tunnel = (
            f"udp://{self.LOOPBACK_HOST}:{loopback_port}:"
            f"{self.LOOPBACK_HOST}:{loopback_port}"
        )
        block = (
            "[Wstunnel]\n"
            f"Url = {url}\n"
            f"Secret = {secret}\n"
            f"Tunnel = {tunnel}\n"
        )

        return {
            "url": url,
            "secret": secret,
            "tunnel": tunnel,
            "wstunnel_block": block,
            "note": (
                f"Replace {self.PUBLIC_HOST_PLACEHOLDER} with the "
                "front server's public host before handing this "
                "snippet to a client."
            ),
        }


    # ── client_command ───────────────────────────────────────────

    def client_command(self, **_: Any) -> Dict[str, Any]:
        """Emit a ready-to-run wstunnel client CLI command.

        For users who run the wstunnel binary directly rather than
        through an app that reads [Wstunnel] blocks.
        """
        secret = self.store.get("wstunnel_secret")
        listen_port = self.store.get_int("wstunnel_listen_port")
        loopback_port = self.store.get_int(
            "loopback_port", default=self.LOOPBACK_PORT,
        )

        if not secret or listen_port is None:
            raise ConfigurationError(
                "Ghost has no secret / listen port stored. Run "
                "'frontmatter-api setup init backend=<IP[:PORT]>' first."
            )

        tunnel = (
            f"udp://{self.LOOPBACK_HOST}:{loopback_port}:"
            f"{self.LOOPBACK_HOST}:{loopback_port}"
        )
        server_url = f"wss://{self.PUBLIC_HOST_PLACEHOLDER}:{listen_port}"

        command = (
            f"wstunnel client"
            f" --http-upgrade-path-prefix={secret}"
            f" -L {tunnel}"
            f" {server_url}"
        )

        return {
            "command": command,
            "note": (
                f"Replace {self.PUBLIC_HOST_PLACEHOLDER} with the "
                "front server's public host before running this "
                "command."
            ),
        }


def _maybe_int(raw: Any) -> Any:
    """Best-effort int parse for status output. Returns the raw value
    if it isn't an integer string."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw
