"""
Low-level ctypes bindings for libfirewall_bridge_linux.so.
"""

import ctypes
import ctypes.util
import os
import platform
from pathlib import Path
from typing import Optional

_lib: Optional[ctypes.CDLL] = None


def _resolve_platform():
    """Resolve platform-specific library name and arch directory."""
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch_dir = "linux-amd64"
    elif machine in ("aarch64", "arm64"):
        arch_dir = "linux-arm64"
    else:
        arch_dir = f"linux-{machine}"
    return "libfirewall_bridge_linux.so", arch_dir


def _find_library() -> str:
    """Find the shared library path."""
    # 1. Explicit env var
    env_path = os.environ.get("FIREWALL_BRIDGE_LIB_PATH")
    if env_path:
        return env_path

    lib_name, arch_dir = _resolve_platform()

    # 2. dist/ directory relative to package
    pkg_dir = Path(__file__).resolve().parent.parent
    dist_path = pkg_dir / "dist" / arch_dir / lib_name
    if dist_path.exists():
        return str(dist_path)

    # 3. System library path
    found = ctypes.util.find_library("firewall_bridge_linux")
    if found:
        return found

    raise FileNotFoundError(
        f"Cannot find {lib_name}. Set FIREWALL_BRIDGE_LIB_PATH or "
        f"place the library in dist/{arch_dir}/."
    )


def get_lib() -> ctypes.CDLL:
    """Load and return the shared library (cached)."""
    global _lib
    if _lib is not None:
        return _lib

    path = _find_library()
    _lib = ctypes.CDLL(path)
    _setup_signatures(_lib)
    return _lib


def _setup_signatures(lib: ctypes.CDLL) -> None:
    """Declare function signatures for type safety."""
    c_char_p = ctypes.c_char_p
    c_int32 = ctypes.c_int32
    c_uint8 = ctypes.c_uint8
    c_uint16 = ctypes.c_uint16
    c_uint32 = ctypes.c_uint32

    # --- Lifecycle ---
    lib.firewall_bridge_init.restype = c_int32
    lib.firewall_bridge_init.argtypes = []

    lib.firewall_bridge_cleanup.restype = None
    lib.firewall_bridge_cleanup.argtypes = []

    lib.firewall_bridge_get_version.restype = c_char_p
    lib.firewall_bridge_get_version.argtypes = []

    lib.firewall_bridge_get_last_error.restype = c_char_p
    lib.firewall_bridge_get_last_error.argtypes = []

    # --- Firewall: INPUT ---
    lib.fw_add_input_accept.restype = c_int32
    lib.fw_add_input_accept.argtypes = [c_uint8, c_char_p, c_uint16, c_char_p]

    lib.fw_add_input_drop.restype = c_int32
    lib.fw_add_input_drop.argtypes = [c_uint8, c_char_p, c_uint16, c_char_p]

    lib.fw_del_input.restype = c_int32
    lib.fw_del_input.argtypes = [c_uint8, c_char_p, c_uint16, c_char_p, c_char_p]

    # --- Firewall: FORWARD ---
    lib.fw_add_forward.restype = c_int32
    lib.fw_add_forward.argtypes = [c_char_p, c_char_p, c_char_p]

    lib.fw_del_forward.restype = c_int32
    lib.fw_del_forward.argtypes = [c_char_p, c_char_p, c_char_p]

    # --- Firewall: NAT ---
    lib.fw_add_nat_masquerade.restype = c_int32
    lib.fw_add_nat_masquerade.argtypes = [c_char_p, c_char_p]

    lib.fw_del_nat_masquerade.restype = c_int32
    lib.fw_del_nat_masquerade.argtypes = [c_char_p, c_char_p]

    # --- Firewall: Query ---
    lib.fw_list_rules.restype = c_char_p
    lib.fw_list_rules.argtypes = []

    lib.fw_flush_table.restype = c_int32
    lib.fw_flush_table.argtypes = []

    # --- Routing: Policy ---
    lib.rt_add_policy.restype = c_int32
    lib.rt_add_policy.argtypes = [c_char_p, c_char_p, c_char_p, c_uint32]

    lib.rt_del_policy.restype = c_int32
    lib.rt_del_policy.argtypes = [c_char_p, c_char_p, c_char_p, c_uint32]

    # --- Routing: Routes ---
    lib.rt_add_route.restype = c_int32
    lib.rt_add_route.argtypes = [c_char_p, c_char_p, c_char_p]

    lib.rt_del_route.restype = c_int32
    lib.rt_del_route.argtypes = [c_char_p, c_char_p, c_char_p]

    # --- Routing: Table management ---
    lib.rt_ensure_table.restype = c_int32
    lib.rt_ensure_table.argtypes = [c_uint32, c_char_p]

    lib.rt_flush_cache.restype = c_int32
    lib.rt_flush_cache.argtypes = []

    lib.rt_enable_ip_forward.restype = c_int32
    lib.rt_enable_ip_forward.argtypes = []