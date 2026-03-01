"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Low-level ctypes bindings to libfirewall_bridge_linux.so (v2 API).
c_void_p + free_string pattern matches wireguard-go-bridge v2.
"""

import ctypes
import ctypes.util
import os
import platform
from typing import Optional

_lib: Optional[ctypes.CDLL] = None


def _resolve_platform():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch_dir = "linux-amd64"
    elif machine in ("aarch64", "arm64"):
        arch_dir = "linux-arm64"
    else:
        arch_dir = f"linux-{machine}"
    return "libfirewall_bridge_linux.so", arch_dir


def _find_library() -> str:
    env_path = os.environ.get("FIREWALL_BRIDGE_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    lib_name, _ = _resolve_platform()

    # Sibling path — .so alongside _ffi.py (vendor-pack layout)
    sibling_path = os.path.join(os.path.dirname(__file__), lib_name)
    if os.path.isfile(sibling_path):
        return sibling_path

    found = ctypes.util.find_library("firewall_bridge_linux")
    if found:
        return found

    raise FileNotFoundError(
        f"{lib_name} not found. Set FIREWALL_BRIDGE_LIB_PATH environment variable."
    )


def get_lib() -> ctypes.CDLL:
    global _lib
    if _lib is not None:
        return _lib
    path = _find_library()
    _lib = ctypes.CDLL(path)
    _setup_signatures(_lib)
    return _lib


c_p = ctypes.c_char_p      # input strings (Python → Rust)
c_vp = ctypes.c_void_p     # output strings (Rust → Python, must free_string)
c_i32 = ctypes.c_int32
c_i64 = ctypes.c_int64
c_u8 = ctypes.c_uint8
c_u16 = ctypes.c_uint16
c_u32 = ctypes.c_uint32


# Log callback type: void(int32_t level, const char *message, void *context)
LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int32, ctypes.c_char_p, ctypes.c_void_p)

# Prevent GC of active callback
_active_log_callback = None


def _setup_signatures(lib: ctypes.CDLL) -> None:
    """Define C function signatures for v2 API."""

    # ---- Log Callback ----
    lib.firewall_bridge_set_log_callback.argtypes = [LOG_CALLBACK_TYPE, ctypes.c_void_p]
    lib.firewall_bridge_set_log_callback.restype = None

    # ---- Lifecycle ----
    lib.firewall_bridge_init.argtypes = [c_p]
    lib.firewall_bridge_init.restype = c_i32

    lib.firewall_bridge_get_status.argtypes = []
    lib.firewall_bridge_get_status.restype = c_vp

    lib.firewall_bridge_start.argtypes = []
    lib.firewall_bridge_start.restype = c_i32

    lib.firewall_bridge_stop.argtypes = []
    lib.firewall_bridge_stop.restype = c_i32

    lib.firewall_bridge_close.argtypes = []
    lib.firewall_bridge_close.restype = c_i32

    # ---- Rule Groups ----
    lib.fw_create_rule_group.argtypes = [c_p, c_p, c_i32]
    lib.fw_create_rule_group.restype = c_vp

    lib.fw_delete_rule_group.argtypes = [c_p]
    lib.fw_delete_rule_group.restype = c_i32

    lib.fw_enable_rule_group.argtypes = [c_p]
    lib.fw_enable_rule_group.restype = c_i32

    lib.fw_disable_rule_group.argtypes = [c_p]
    lib.fw_disable_rule_group.restype = c_i32

    lib.fw_list_rule_groups.argtypes = []
    lib.fw_list_rule_groups.restype = c_vp

    lib.fw_get_rule_group.argtypes = [c_p]
    lib.fw_get_rule_group.restype = c_vp

    # ---- Firewall Rules ----
    lib.fw_add_rule.argtypes = [c_p, c_p, c_p, c_u8, c_p, c_u16, c_p, c_p, c_p, c_p, c_p]
    lib.fw_add_rule.restype = c_i64

    lib.fw_remove_rule.argtypes = [c_i64]
    lib.fw_remove_rule.restype = c_i32

    lib.fw_list_rules.argtypes = [c_p]
    lib.fw_list_rules.restype = c_vp

    # ---- Routing Rules ----
    lib.rt_add_rule.argtypes = [c_p, c_p, c_p, c_p, c_p, c_u32, c_u32, c_p, c_p, c_u32]
    lib.rt_add_rule.restype = c_i64

    lib.rt_remove_rule.argtypes = [c_i64]
    lib.rt_remove_rule.restype = c_i32

    lib.rt_list_rules.argtypes = [c_p]
    lib.rt_list_rules.restype = c_vp

    # ---- Presets ----
    lib.fw_apply_preset_vpn.argtypes = [c_p, c_p, c_u16, c_p, c_p]
    lib.fw_apply_preset_vpn.restype = c_vp

    lib.fw_apply_preset_multihop.argtypes = [c_p, c_p, c_p, c_u32, c_u32, c_p]
    lib.fw_apply_preset_multihop.restype = c_vp

    lib.fw_apply_preset_kill_switch.argtypes = [c_u16, c_u16, c_p]
    lib.fw_apply_preset_kill_switch.restype = c_vp

    lib.fw_apply_preset_dns_protection.argtypes = [c_p]
    lib.fw_apply_preset_dns_protection.restype = c_vp

    lib.fw_apply_preset_ipv6_block.argtypes = []
    lib.fw_apply_preset_ipv6_block.restype = c_vp

    lib.fw_remove_preset.argtypes = [c_p]
    lib.fw_remove_preset.restype = c_i32

    # ---- Verify ----
    lib.fw_get_kernel_state.argtypes = []
    lib.fw_get_kernel_state.restype = c_vp

    lib.fw_verify_rules.argtypes = []
    lib.fw_verify_rules.restype = c_vp

    # ---- Utility ----
    lib.firewall_bridge_get_version.argtypes = []
    lib.firewall_bridge_get_version.restype = c_p  # static, no free needed

    lib.firewall_bridge_get_last_error.argtypes = []
    lib.firewall_bridge_get_last_error.restype = c_p  # static, no free needed

    lib.firewall_bridge_free_string.argtypes = [c_p]
    lib.firewall_bridge_free_string.restype = None

    lib.rt_flush_cache.argtypes = []
    lib.rt_flush_cache.restype = c_i32

    lib.rt_enable_ip_forward.argtypes = []
    lib.rt_enable_ip_forward.restype = c_i32

    lib.fw_flush_table.argtypes = []
    lib.fw_flush_table.restype = c_i32


def _read_and_free(ptr) -> str:
    """Read a Rust-allocated C string and free it."""
    if not ptr:
        return ""
    s = ctypes.cast(ptr, ctypes.c_char_p)
    text = s.value.decode("utf-8") if s.value else ""
    get_lib().firewall_bridge_free_string(s)
    return text


def get_version() -> str:
    result = get_lib().firewall_bridge_get_version()
    return result.decode("utf-8") if result else "unknown"
