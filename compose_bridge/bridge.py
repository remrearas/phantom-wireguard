"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
"""

from __future__ import annotations

import json
from typing import Any

import ctypes

from ._ffi import load_library
from .types import ExecResult, check_result


class ComposeBridge:
    """High-level Python wrapper around the compose_bridge .so FFI.

    Usage — like a firewall preset:

        with ComposeBridge("docker-compose.yml", project_name="mh-test") as bridge:
            bridge.up()
            result = bridge.exec("daemon", ["pytest", "-v"])
            bridge.down()
    """

    __slots__ = ("_lib", "_handle")

    def __init__(self, config_path: str, project_name: str = "") -> None:
        self._lib = load_library()
        handle = self._lib.NewComposeBridge(
            config_path.encode("utf-8"),
            project_name.encode("utf-8"),
        )
        check_result(handle)
        self._handle: int = handle

    # -- helpers --

    def _get_last_error(self, bridge_handle: int) -> str:
        ptr = self._lib.GetLastError(bridge_handle)
        if not ptr:
            return ""
        msg = ctypes.string_at(ptr).decode("utf-8", errors="replace")
        self._lib.FreeString(ptr)
        return msg

    def _check(self, code: int) -> None:
        check_result(
            code,
            get_last_error=self._get_last_error,
            bridge_handle=self._handle,
        )

    def _read_string(self, ptr) -> str:
        if not ptr:
            detail = self._get_last_error(self._handle)
            msg = "bridge returned null"
            if detail:
                msg = f"{msg}: {detail}"
            raise RuntimeError(msg)
        result = ctypes.string_at(ptr).decode("utf-8", errors="replace")
        self._lib.FreeString(ptr)
        return result

    # -- project info --

    @property
    def project_name(self) -> str:
        """Return the unique project name assigned by the bridge."""
        ptr = self._lib.GetProjectName(self._handle)
        return self._read_string(ptr)

    # -- project lifecycle --

    def up(self) -> None:
        """Start all services."""
        code = self._lib.ProjectUp(self._handle)
        self._check(code)

    def down(self) -> None:
        """Stop and remove services, networks, and volumes."""
        code = self._lib.ProjectDown(self._handle)
        self._check(code)

    def ps(self) -> list[dict[str, Any]]:
        """List containers."""
        ptr = self._lib.ProjectPs(self._handle)
        raw = self._read_string(ptr)
        return json.loads(raw)

    def exec(
        self,
        service: str,
        command: list[str] | str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        """Execute a command inside a service container."""
        if isinstance(command, str):
            command = [command]

        cmd_json = json.dumps(command)
        env_json = json.dumps(env) if env else ""

        ptr = self._lib.ServiceExec(
            self._handle,
            service.encode("utf-8"),
            cmd_json.encode("utf-8"),
            env_json.encode("utf-8"),
        )
        raw = self._read_string(ptr)
        data = json.loads(raw)
        return ExecResult(
            exit_code=data["exit_code"],
            stdout=data["stdout"],
            stderr=data["stderr"],
        )

    def logs(self, service: str, follow: bool = False) -> str:
        """Retrieve logs from a service."""
        ptr = self._lib.ServiceLogs(
            self._handle,
            service.encode("utf-8"),
            1 if follow else 0,
        )
        return self._read_string(ptr)

    def version(self) -> str:
        """Return the bridge version string."""
        ptr = self._lib.BridgeVersion()
        return self._read_string(ptr)

    def close(self) -> None:
        """Release bridge resources."""
        if self._handle and self._handle > 0:
            self._lib.CloseBridge(self._handle)
            self._handle = 0

    # -- context manager --

    def __enter__(self) -> ComposeBridge:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
