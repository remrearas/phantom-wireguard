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

import ctypes
import os
import platform
import subprocess
from ctypes import c_char_p, c_int32, c_int64, c_void_p
from pathlib import Path

_SYS = platform.system().lower()
_LIB_EXT = ".dylib" if _SYS == "darwin" else ".so"
_GO_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(
    platform.machine(), platform.machine()
)
# Generic name (dev builds)
_LIB_NAME = f"compose_bridge{_LIB_EXT}"
# Platform-specific name (dist packages)
_LIB_NAME_PLATFORM = f"compose_bridge-{_SYS}-{_GO_ARCH}{_LIB_EXT}"


def _discover() -> str:
    """3-tier discovery for compose_bridge shared library.

    Tier 1: COMPOSE_BRIDGE_LIB_PATH environment variable.
    Tier 2: Sibling of this file (dist package or dev build output).
    Tier 3: System ldconfig / library path.
    """
    # Tier 1 — explicit path
    env_path = os.environ.get("COMPOSE_BRIDGE_LIB_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return str(p)
        raise FileNotFoundError(
            f"COMPOSE_BRIDGE_LIB_PATH set but file not found: {env_path}"
        )

    # Tier 2 — sibling of this module (dist or dev build)
    pkg_dir = Path(__file__).resolve().parent
    project_root = pkg_dir.parent
    for candidate in (
        # dist package: compose_bridge-linux-amd64.so alongside _ffi.py
        pkg_dir / _LIB_NAME_PLATFORM,
        # dev: compose_bridge.so alongside _ffi.py
        pkg_dir / _LIB_NAME,
        # dev build output: build/{os}-{arch}/compose_bridge.{ext}
        project_root / "build" / f"{_SYS}-{_GO_ARCH}" / _LIB_NAME,
    ):
        if candidate.is_file():
            return str(candidate)

    # Tier 3 — system ldconfig
    try:
        result = subprocess.run(
            ["ldconfig", "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if _LIB_NAME in line:
                parts = line.split("=>")
                if len(parts) == 2:
                    return parts[1].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raise FileNotFoundError(
        f"Cannot find {_LIB_NAME} or {_LIB_NAME_PLATFORM}. "
        f"Set COMPOSE_BRIDGE_LIB_PATH or place it next to this module."
    )


def _setup_signatures(lib: ctypes.CDLL) -> ctypes.CDLL:
    """Declare FFI function signatures for type safety."""

    # NewComposeBridge(configPath, projectName *char) -> int64
    lib.NewComposeBridge.argtypes = [c_char_p, c_char_p]
    lib.NewComposeBridge.restype = c_int64

    # GetProjectName(bridge int64) -> *char
    lib.GetProjectName.argtypes = [c_int64]
    lib.GetProjectName.restype = c_void_p

    # ProjectUp(bridge int64) -> int32
    lib.ProjectUp.argtypes = [c_int64]
    lib.ProjectUp.restype = c_int32

    # ProjectDown(bridge int64) -> int32
    lib.ProjectDown.argtypes = [c_int64]
    lib.ProjectDown.restype = c_int32

    # ProjectPs(bridge int64) -> *char  (c_void_p to preserve pointer for FreeString)
    lib.ProjectPs.argtypes = [c_int64]
    lib.ProjectPs.restype = c_void_p

    # ServiceExec(bridge int64, service, command, envJSON *char) -> *char
    lib.ServiceExec.argtypes = [c_int64, c_char_p, c_char_p, c_char_p]
    lib.ServiceExec.restype = c_void_p

    # ServiceLogs(bridge int64, service *char, follow int32) -> *char
    lib.ServiceLogs.argtypes = [c_int64, c_char_p, c_int32]
    lib.ServiceLogs.restype = c_void_p

    # GetLastError(bridge int64) -> *char
    lib.GetLastError.argtypes = [c_int64]
    lib.GetLastError.restype = c_void_p

    # CloseBridge(bridge int64) -> int32
    lib.CloseBridge.argtypes = [c_int64]
    lib.CloseBridge.restype = c_int32

    # FreeString(s *char)  (c_void_p to match preserved pointers)
    lib.FreeString.argtypes = [c_void_p]
    lib.FreeString.restype = None

    # BridgeVersion() -> *char
    lib.BridgeVersion.argtypes = []
    lib.BridgeVersion.restype = c_void_p

    return lib


def load_library() -> ctypes.CDLL:
    """Discover, load, and configure the compose_bridge shared library."""
    path = _discover()
    lib = ctypes.CDLL(path)
    return _setup_signatures(lib)
