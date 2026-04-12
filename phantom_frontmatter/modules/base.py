"""
Phantom-WG Frontmatter — Module Base Class

All frontmatter modules inherit from BaseModule. It owns the shared
infrastructure that every module needs and nothing else:

    - Directory layout (config, data, logs, secrets, bin)
    - A KVStore handle pointing at the module's own SQLite table
    - Per-module logger
    - run_command() helper for subprocess execution
    - systemd integration helpers (systemctl wrappers)

State principle
    A module's KV table holds **primitive runtime parameters** only.
    Backend IP, cert paths, secret, listen port — the raw inputs
    needed to run the service. Anything else is reproducible from
    those inputs and lives nowhere on disk.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from phantom_frontmatter.api.store import KVStore


class BaseModule(ABC):
    """Abstract base class for all frontmatter modules.

    Subclasses must implement:
        - ``get_module_name()``        — short identifier (e.g. "setup")
        - ``get_module_description()`` — human-readable description
        - ``get_actions()``            — mapping of action name → callable

    Shared infrastructure:
        - ``install_dir``    /opt/phantom-frontmatter
        - ``config_dir``     install_dir / "config"
        - ``data_dir``       install_dir / "data"
        - ``logs_dir``       install_dir / "logs"
        - ``secrets_dir``    install_dir / "secrets"
        - ``bin_dir``        install_dir / "bin"
        - ``db_path``        data_dir / "frontmatter.db"
        - ``store``          KVStore on the module's own table
    """

    DB_FILENAME = "frontmatter.db"

    def __init__(self, install_dir: Optional[Path] = None):
        """Initialize module paths, logger, and KV store handle.

        Args:
            install_dir: Installation root (default ``/opt/phantom-frontmatter``)
        """
        self.install_dir = install_dir or Path("/opt/phantom-frontmatter")
        self.config_dir = self.install_dir / "config"
        self.data_dir = self.install_dir / "data"
        self.logs_dir = self.install_dir / "logs"
        self.secrets_dir = self.install_dir / "secrets"
        self.bin_dir = self.install_dir / "bin"
        self.systemd_dir = Path("/etc/systemd/system")

        # Ensure the standard subdirectories exist; PermissionError
        # is swallowed so non-root callers can use a writable tmpdir.
        for d in (self.data_dir, self.config_dir, self.secrets_dir, self.bin_dir):
            try:
                d.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                pass

        self.db_path = self.data_dir / self.DB_FILENAME
        self.store = KVStore(self.db_path, self.get_module_name())

        self.logger = self._setup_logger()

    # ── Abstract surface ─────────────────────────────────────────

    @abstractmethod
    def get_module_name(self) -> str:
        """Return the module identifier (used as the SQLite table name)."""
        ...

    @abstractmethod
    def get_module_description(self) -> str:
        """Return a human-readable module description."""
        ...

    @abstractmethod
    def get_actions(self) -> Dict[str, Callable]:
        """Return a mapping of action name → bound method."""
        ...

    # ── Cross-module store helper ───────────────────────────────

    def foreign_store(self, table: str) -> KVStore:
        """Open a KVStore against another module's table.

        Used when one module needs to read parameters owned by
        another (e.g. ``ghost`` reading ``setup.backend_ip`` to
        render its systemd unit).
        """
        return KVStore(self.db_path, table)

    # ── Logging ──────────────────────────────────────────────────

    def _setup_logger(self) -> logging.Logger:
        """Set up a module-specific logger.

        Logger name: ``phantom.frontmatter.<module_name>``. Handlers
        are configured by the calling application.
        """
        logger_name = f"phantom.frontmatter.{self.get_module_name()}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        return logger

    # ── Subprocess helper ────────────────────────────────────────

    def run_command(
        self,
        cmd: List[str],
        *,
        check: bool = False,
        capture_output: bool = True,
        timeout: Optional[int] = 30,
        stdin_data: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute a shell command and return a structured result.

        Args:
            cmd:            Command and arguments as a list
            check:          Raise on non-zero exit (default: False)
            capture_output: Capture stdout/stderr (default: True)
            timeout:        Seconds before SIGKILL (default: 30)
            stdin_data:     Optional string to pipe into the subprocess stdin
            env:            Optional environment overrides

        Returns:
            ``{"success": bool, "stdout": str, "stderr": str, "returncode": int, "command": List[str]}``
        """
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                input=stdin_data,
                env=env,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "returncode": result.returncode,
                "command": cmd,
            }
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timeout: {' '.join(cmd)}")
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": f"Timeout after {timeout}s",
                "returncode": -1,
                "command": cmd,
            }
        except FileNotFoundError as e:
            self.logger.error(f"Command not found: {cmd[0]}")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command not found: {e}",
                "returncode": -1,
                "command": cmd,
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": e.stderr or "",
                "returncode": e.returncode,
                "command": cmd,
            }

    # ── systemd integration helpers ──────────────────────────────

    def _systemctl(self, *args: str, check: bool = False) -> Dict[str, Any]:
        """Run a systemctl subcommand and return the structured result."""
        return self.run_command(["systemctl", *args], check=check)

    def _systemctl_enable_start(self, service_name: str) -> bool:
        """``systemctl enable --now <service>`` — idempotent."""
        self._systemctl("enable", service_name)
        start = self._systemctl("start", service_name)
        if not start["success"]:
            self.logger.error(
                f"systemctl start {service_name} failed: {start['stderr']}"
            )
            return False
        self.logger.info(f"{service_name} enabled and started")
        return True

    def _systemctl_disable_stop(self, service_name: str) -> bool:
        """``systemctl disable --now <service>`` — idempotent."""
        self._systemctl("stop", service_name)
        self._systemctl("disable", service_name)
        self.logger.info(f"{service_name} stopped and disabled")
        return True

    def _systemctl_is_active(self, service_name: str) -> bool:
        result = self._systemctl("is-active", service_name)
        return result["stdout"].strip() == "active"

    def _systemctl_is_enabled(self, service_name: str) -> bool:
        result = self._systemctl("is-enabled", service_name)
        return result["stdout"].strip() in (
            "enabled", "alias", "static", "enabled-runtime",
        )

    def _systemctl_daemon_reload(self) -> bool:
        return self._systemctl("daemon-reload")["success"]