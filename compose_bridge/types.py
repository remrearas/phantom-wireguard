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

from dataclasses import dataclass


class BridgeError(Exception):
    """Base error for all compose bridge failures."""


class DockerInitError(BridgeError):
    """Docker CLI / daemon initialisation failed."""


class ProjectLoadError(BridgeError):
    """Compose file could not be parsed or loaded."""


class ProjectUpError(BridgeError):
    """Failed to start services."""


class ProjectDownError(BridgeError):
    """Failed to stop / remove services."""


class ExecError(BridgeError):
    """Command execution inside a container failed."""


class PsError(BridgeError):
    """Failed to list containers."""


class LogsError(BridgeError):
    """Failed to retrieve service logs."""


class NotFoundError(BridgeError):
    """Handle or resource not found."""


class InternalError(BridgeError):
    """Unexpected internal error."""


ERROR_MAP: dict[int, type[BridgeError]] = {
    -1: DockerInitError,
    -2: ProjectLoadError,
    -3: ProjectUpError,
    -4: ProjectDownError,
    -5: ExecError,
    -6: PsError,
    -7: LogsError,
    -8: NotFoundError,
    -99: InternalError,
}


@dataclass(frozen=True, slots=True)
class ExecResult:
    """Result of a command executed inside a container."""

    exit_code: int
    stdout: str
    stderr: str


def check_result(code: int, get_last_error=None, bridge_handle: int = 0) -> None:
    """Raise the appropriate BridgeError when *code* is negative.

    *get_last_error* is a callable that retrieves the detailed Go error
    string (``GetLastError`` FFI function).
    """
    if code >= 0:
        return

    detail = ""
    if get_last_error is not None and bridge_handle > 0:
        detail = get_last_error(bridge_handle)

    exc_cls = ERROR_MAP.get(code, InternalError)
    msg = f"compose bridge error {code}"
    if detail:
        msg = f"{msg}: {detail}"
    raise exc_cls(msg)
