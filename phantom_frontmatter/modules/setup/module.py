"""
Phantom-WG Frontmatter — Setup Module

The single bootstrap entry point for a fresh frontmatter install. It
takes a backend ``IP[:PORT]`` (any WireGuard server or arbitrary UDP
endpoint), generates a self-signed TLS certificate, extracts the
bundled wstunnel binary, generates a wstunnel secret, and renders +
installs the two systemd units that make up the ghost data path.
It does not start any service — that is the operator's explicit
follow-up via ``frontmatter-api ghost start``.

Idempotency model
    ``setup init`` is fail-fast. If the SQLite state already has
    an ``initialized_at`` row, the action refuses with a clear
    message that points the operator at ``setup clean``. To rebuild
    a deployment from scratch:

        frontmatter-api setup clean yes=true
        frontmatter-api setup init backend=<NEW_IP[:PORT]>

Actions:
    init   — bootstrap the host (one-shot, fails on existing state)
    clean  — destroy every artifact init produced (services, units,
             cert, binary, SQLite DB) and return the host to a
             pre-init state
    status — report whether init has been done and surface the
             primitive parameters from the setup table

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from phantom_frontmatter.api.exceptions import (
    ConfigurationError,
    SetupError,
    ValidationError,
)
from phantom_frontmatter.api.validators import validate_ip, validate_port
from phantom_frontmatter.modules.base import BaseModule

from .lib import binary_utils, cert_utils, render_utils, secret_utils


class SetupModule(BaseModule):
    """Bootstrap and factory-reset module."""

    GHOST_EGRESS_SERVICE = "phantom-frontmatter-ghost-egress.service"
    GHOST_WSTUNNEL_SERVICE = "phantom-frontmatter-ghost-wstunnel.service"
    GHOST_EGRESS_TEMPLATE = "phantom-frontmatter-ghost-egress.service.template"
    GHOST_WSTUNNEL_TEMPLATE = "phantom-frontmatter-ghost-wstunnel.service.template"

    # Wstunnel forwards to this loopback target; egress listens on
    # the same address.
    LOOPBACK_HOST = "127.0.0.1"
    LOOPBACK_PORT = 51820

    DEFAULT_WSTUNNEL_LISTEN_PORT = 443
    DEFAULT_BACKEND_PORT = 51820

    def get_module_name(self) -> str:
        return "setup"

    def get_module_description(self) -> str:
        return (
            "Bootstrap (init) and factory reset (clean) for the "
            "frontmatter host. One-shot setup, fail-fast on re-init."
        )

    def get_actions(self) -> Dict[str, Callable]:
        return {
            "init": self.init,
            "clean": self.clean,
            "status": self.status,
        }

    # ── Paths ────────────────────────────────────────────────────

    @property
    def cert_path(self) -> Path:
        return self.secrets_dir / "tls_cert"

    @property
    def key_path(self) -> Path:
        return self.secrets_dir / "tls_key"

    @property
    def wstunnel_binary(self) -> Path:
        return self.bin_dir / "wstunnel"

    @property
    def egress_unit_path(self) -> Path:
        return self.systemd_dir / self.GHOST_EGRESS_SERVICE

    @property
    def wstunnel_unit_path(self) -> Path:
        return self.systemd_dir / self.GHOST_WSTUNNEL_SERVICE

    # ── Subprocess runner (injected into lib helpers) ───────────

    def _run(self, cmd, **kwargs):
        return self.run_command(cmd, **kwargs)

    # ── Backend parsing ─────────────────────────────────────────

    def _parse_backend(self, backend: str) -> tuple[str, int]:
        """Parse a backend argument string into ``(ip, port)``.

        Accepts ``IP`` (port defaults to 51820) or ``IP:PORT``.
        Raises ValidationError on bad input.
        """
        if not isinstance(backend, str) or not backend.strip():
            raise ValidationError(
                "Missing 'backend' parameter. Usage: "
                "frontmatter-api setup init backend=<IP[:PORT]>"
            )
        backend = backend.strip()
        if ":" in backend:
            host, _, port_str = backend.rpartition(":")
            if not host or not port_str:
                raise ValidationError(
                    f"Invalid backend {backend!r}, expected IP or IP:PORT"
                )
            ip = validate_ip(host, allow_ipv6=False)
            port = validate_port(int(port_str))
        else:
            ip = validate_ip(backend, allow_ipv6=False)
            port = self.DEFAULT_BACKEND_PORT
        return ip, port

    # ── init ────────────────────────────────────────────────────

    def init(self, backend: str = "", **_: Any) -> Dict[str, Any]:
        """Bootstrap the frontmatter host.

        Refuses to run if the setup table already has an
        ``initialized_at`` marker. The operator must run
        ``frontmatter-api setup clean yes=true`` first to wipe the
        previous deployment.
        """
        # 1. Fail-fast on existing init
        existing = self.store.get("initialized_at")
        if existing is not None:
            raise ConfigurationError(
                f"Already initialized at {existing}. "
                f"Run 'frontmatter-api setup clean yes=true' first "
                f"to reset before re-running setup init."
            )

        # 2. Parse + validate backend
        backend_ip, backend_port = self._parse_backend(backend)

        # 3. Locate socat (system dependency installed by frontmatter-install.sh)
        # noinspection PyDeprecation
        socat_binary = shutil.which("socat")
        if not socat_binary:
            raise SetupError(
                "socat binary not found on PATH. Install it with "
                "'apt-get install -y socat' (the installer normally "
                "handles this)."
            )

        # 4. Read TLS defaults from packaged JSON
        defaults = cert_utils.load_cert_defaults()
        tls_common_name = defaults["common_name"]
        tls_validity = int(defaults["validity_days"])
        tls_curve = defaults["key_curve"]
        tls_org = defaults.get("organization")

        # 5. Generate self-signed cert + key
        if not cert_utils.generate_self_signed(
            cert_path=self.cert_path,
            key_path=self.key_path,
            common_name=tls_common_name,
            organization=tls_org,
            validity_days=tls_validity,
            key_curve=tls_curve,
            run_command_func=self._run,
            logger=self.logger,
        ):
            raise SetupError("Failed to generate self-signed TLS certificate")

        # 6. Extract bundled wstunnel binary
        if not binary_utils.install_wstunnel(
            bin_dir=self.bin_dir,
            run_command_func=self._run,
            logger=self.logger,
        ):
            raise SetupError(
                f"Failed to install wstunnel {binary_utils.WSTUNNEL_VERSION}"
            )
        installed_version = binary_utils.get_installed_version(
            self.wstunnel_binary, self._run
        ) or binary_utils.WSTUNNEL_VERSION

        # 7. Generate wstunnel secret
        wstunnel_secret = secret_utils.generate_secret()

        # 8. Render + install systemd units
        self._render_and_install_units(
            backend_ip=backend_ip,
            backend_port=backend_port,
            wstunnel_listen_port=self.DEFAULT_WSTUNNEL_LISTEN_PORT,
            wstunnel_secret=wstunnel_secret,
            socat_binary=socat_binary,
        )

        # 9. systemctl daemon-reload so the new units are visible
        if not self._systemctl_daemon_reload():
            raise SetupError("systemctl daemon-reload failed")

        # 10. Persist primitive parameters to the setup + ghost tables
        initialized_at = datetime.now(timezone.utc).isoformat()
        self.store.replace({
            "backend_ip":          backend_ip,
            "backend_port":        str(backend_port),
            "tls_cert_path":       str(self.cert_path),
            "tls_key_path":        str(self.key_path),
            "tls_common_name":     tls_common_name,
            "wstunnel_binary_path": str(self.wstunnel_binary),
            "wstunnel_version":    installed_version,
            "socat_binary_path":   socat_binary,
            "initialized_at":      initialized_at,
        })

        ghost_store = self.foreign_store("ghost")
        ghost_store.replace({
            "wstunnel_listen_port": str(self.DEFAULT_WSTUNNEL_LISTEN_PORT),
            "wstunnel_secret":      wstunnel_secret,
            "loopback_port":        str(self.LOOPBACK_PORT),
        })

        self.logger.info(
            f"Setup init complete: backend={backend_ip}:{backend_port}, "
            f"wstunnel={installed_version}"
        )

        return {
            "success": True,
            "backend_ip": backend_ip,
            "backend_port": backend_port,
            "tls_cert_path": str(self.cert_path),
            "tls_key_path": str(self.key_path),
            "wstunnel_version": installed_version,
            "wstunnel_listen_port": self.DEFAULT_WSTUNNEL_LISTEN_PORT,
            "wstunnel_secret_fingerprint": secret_utils.secret_fingerprint(
                wstunnel_secret
            ),
            "egress_unit": str(self.egress_unit_path),
            "wstunnel_unit": str(self.wstunnel_unit_path),
            "next_step": "frontmatter-api ghost start",
        }

    # ── render helper used by init ──────────────────────────────

    def _render_and_install_units(
        self,
        *,
        backend_ip: str,
        backend_port: int,
        wstunnel_listen_port: int,
        wstunnel_secret: str,
        socat_binary: str,
    ) -> None:
        """Render both systemd templates and write them to /etc/systemd/system."""
        loopback_target = f"{self.LOOPBACK_HOST}:{self.LOOPBACK_PORT}"
        # ``=`` syntax binds the secret to the flag so clap (the CLI
        # parser wstunnel uses) accepts secret values that start with
        # ``-`` as values rather than flags.
        restrict_arg = (
            f"--restrict-http-upgrade-path-prefix={wstunnel_secret}"
        )

        egress_text = render_utils.render_template(
            self.GHOST_EGRESS_TEMPLATE,
            {
                "SOCAT_BINARY":  socat_binary,
                "LOOPBACK_PORT": str(self.LOOPBACK_PORT),
                "BACKEND_IP":    backend_ip,
                "BACKEND_PORT":  str(backend_port),
            },
        )
        if not render_utils.write_unit_file(
            self.egress_unit_path, egress_text, self.logger
        ):
            raise SetupError(
                f"Failed to write {self.egress_unit_path}"
            )

        wstunnel_text = render_utils.render_template(
            self.GHOST_WSTUNNEL_TEMPLATE,
            {
                "INSTALL_DIR":      str(self.install_dir),
                "BINARY_PATH":      str(self.wstunnel_binary),
                "LISTEN_PORT":      str(wstunnel_listen_port),
                "TARGET":           loopback_target,
                "CERT_PATH":        str(self.cert_path),
                "KEY_PATH":         str(self.key_path),
                "RESTRICT_PATH_ARG": restrict_arg,
            },
        )
        if not render_utils.write_unit_file(
            self.wstunnel_unit_path, wstunnel_text, self.logger
        ):
            raise SetupError(
                f"Failed to write {self.wstunnel_unit_path}"
            )

    # ── clean ───────────────────────────────────────────────────

    def clean(self, yes: bool = False, **_: Any) -> Dict[str, Any]:
        """Destroy every artifact ``init`` produced and return to a
        pre-init state.

        Refuses to run unless ``yes=true`` is passed explicitly.

        What gets removed:
            - phantom-frontmatter-ghost-{egress,wstunnel}.service
              (stop + disable + unit file delete)
            - Stray socat / wstunnel processes (defensive pkill)
            - secrets/tls_cert + secrets/tls_key
            - bin/wstunnel
            - data/frontmatter.db (the SQLite state itself)

        What stays:
            - The install dir under /opt/phantom-frontmatter
            - The python virtualenv
            - The frontmatter-api / frontmatter-uninstall global commands
            - The system socat package

        Use ``frontmatter-uninstall`` for a full removal of the
        installed package.
        """
        if not yes:
            raise ConfigurationError(
                "setup clean is destructive. Pass yes=true to confirm: "
                "'frontmatter-api setup clean yes=true'"
            )

        removed: Dict[str, Any] = {
            "services_stopped": [],
            "unit_files_removed": [],
            "files_removed": [],
            "db_removed": False,
        }

        # 1. Stop + disable both ghost services (best-effort)
        for svc in (self.GHOST_WSTUNNEL_SERVICE, self.GHOST_EGRESS_SERVICE):
            self._systemctl("stop", svc)
            self._systemctl("disable", svc)
            removed["services_stopped"].append(svc)

        # 2. Remove unit files
        for unit_path in (self.wstunnel_unit_path, self.egress_unit_path):
            if unit_path.exists():
                try:
                    unit_path.unlink()
                    removed["unit_files_removed"].append(str(unit_path))
                    self.logger.info(f"Removed unit: {unit_path}")
                except OSError as e:
                    self.logger.error(f"Failed to remove {unit_path}: {e}")

        self._systemctl_daemon_reload()
        self._systemctl("reset-failed")

        # 3. Kill any wstunnel / socat processes still holding the
        #    loopback port or :443.
        self._run(["pkill", "-f", "wstunnel server"])
        self._run([
            "pkill", "-f",
            "socat.*UDP4-LISTEN:51820.*bind=127\\.0\\.0\\.1",
        ])

        # 4. Cert + binary on-disk artifacts
        for path in (self.cert_path, self.key_path, self.wstunnel_binary):
            if path.exists():
                try:
                    path.unlink()
                    removed["files_removed"].append(str(path))
                    self.logger.info(f"Removed: {path}")
                except OSError as e:
                    self.logger.error(f"Failed to remove {path}: {e}")

        # 5. Drop the SQLite DB. The next CLI invocation will recreate
        #    it via CREATE TABLE IF NOT EXISTS.
        if self.db_path.exists():
            try:
                self.db_path.unlink()
                removed["db_removed"] = True
                self.logger.info(f"Removed state DB: {self.db_path}")
            except OSError as e:
                self.logger.error(f"Failed to remove {self.db_path}: {e}")

        self.logger.info("Setup clean complete — host is back to pre-init state")
        return {
            "success": True,
            **removed,
            "next_step": "frontmatter-api setup init backend=<IP[:PORT]>",
        }

    # ── status ──────────────────────────────────────────────────

    def status(self, **_: Any) -> Dict[str, Any]:
        """Report whether setup has been initialized and surface the
        primitive parameters from the setup table.

        Read-only — never writes to the store. Service active/enabled
        flags belong to the ``ghost status`` action; this one is
        purely about the bootstrap state.
        """
        initialized_at = self.store.get("initialized_at")
        initialized = initialized_at is not None

        if not initialized:
            return {
                "initialized": False,
                "next_step": "frontmatter-api setup init backend=<IP[:PORT]>",
            }

        return {
            "initialized": True,
            "initialized_at": initialized_at,
            "backend_ip": self.store.get("backend_ip"),
            "backend_port": self.store.get_int("backend_port"),
            "tls_cert_path": self.store.get("tls_cert_path"),
            "tls_key_path": self.store.get("tls_key_path"),
            "tls_common_name": self.store.get("tls_common_name"),
            "wstunnel_binary_path": self.store.get("wstunnel_binary_path"),
            "wstunnel_version": self.store.get("wstunnel_version"),
            "socat_binary_path": self.store.get("socat_binary_path"),
            "egress_unit_present": self.egress_unit_path.exists(),
            "wstunnel_unit_present": self.wstunnel_unit_path.exists(),
            "cert_present": self.cert_path.exists(),
            "binary_present": self.wstunnel_binary.exists(),
        }
