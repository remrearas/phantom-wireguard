"""
Low-level ctypes bindings to libwstunnel_bridge_linux.so.
All other modules use this as the FFI foundation.
"""

import ctypes
import ctypes.util
import os
import platform
from typing import Callable, Optional

_lib: Optional[ctypes.CDLL] = None


def _resolve_platform() -> tuple[str, str]:
    """Resolve library filename and architecture directory."""
    system = platform.system().lower()
    arch = platform.machine()

    ext = ".dylib" if system == "darwin" else ".so"
    lib_name = f"libwstunnel_bridge_linux{ext}"

    arch_map = {
        ("linux", "x86_64"): "linux-amd64",
        ("linux", "aarch64"): "linux-arm64",
        ("linux", "arm64"): "linux-arm64",
    }
    arch_dir = arch_map.get((system, arch), f"{system}-{arch}")
    return lib_name, arch_dir


def _find_library() -> str:
    """Locate wstunnel bridge shared library via environment variable."""
    env_path = os.environ.get("WSTUNNEL_BRIDGE_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    found = ctypes.util.find_library("wstunnel_bridge_linux")
    if found:
        return found

    lib_name, _ = _resolve_platform()
    raise FileNotFoundError(
        f"{lib_name} not found. Set WSTUNNEL_BRIDGE_LIB_PATH environment variable."
    )


def _load_library() -> ctypes.CDLL:
    global _lib
    if _lib is None:
        path = _find_library()
        _lib = ctypes.CDLL(path)
        _setup_signatures(_lib)
    return _lib


def get_lib() -> ctypes.CDLL:
    return _load_library()


# --- Function Signatures ---

_WS_LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(
    None, ctypes.c_int32, ctypes.c_char_p, ctypes.c_void_p
)


def _setup_signatures(lib: ctypes.CDLL) -> None:
    """Define C function signatures for type safety."""

    # --- Logging ---
    lib.wstunnel_set_log_callback.argtypes = [_WS_LOG_CALLBACK_TYPE, ctypes.c_void_p]
    lib.wstunnel_set_log_callback.restype = None

    lib.wstunnel_init_logging.argtypes = [ctypes.c_int32]
    lib.wstunnel_init_logging.restype = None

    # --- Config Builder ---
    lib.wstunnel_config_new.argtypes = []
    lib.wstunnel_config_new.restype = ctypes.c_void_p

    lib.wstunnel_config_free.argtypes = [ctypes.c_void_p]
    lib.wstunnel_config_free.restype = None

    lib.wstunnel_config_set_remote_url.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_config_set_remote_url.restype = ctypes.c_int32

    lib.wstunnel_config_set_http_upgrade_path_prefix.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_config_set_http_upgrade_path_prefix.restype = ctypes.c_int32

    lib.wstunnel_config_set_http_upgrade_credentials.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_config_set_http_upgrade_credentials.restype = ctypes.c_int32

    lib.wstunnel_config_set_tls_verify.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.wstunnel_config_set_tls_verify.restype = ctypes.c_int32

    lib.wstunnel_config_set_tls_sni_override.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_config_set_tls_sni_override.restype = ctypes.c_int32

    lib.wstunnel_config_set_tls_sni_disable.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.wstunnel_config_set_tls_sni_disable.restype = ctypes.c_int32

    lib.wstunnel_config_set_websocket_ping_frequency.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.wstunnel_config_set_websocket_ping_frequency.restype = ctypes.c_int32

    lib.wstunnel_config_set_websocket_mask_frame.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.wstunnel_config_set_websocket_mask_frame.restype = ctypes.c_int32

    lib.wstunnel_config_set_connection_min_idle.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.wstunnel_config_set_connection_min_idle.restype = ctypes.c_int32

    lib.wstunnel_config_set_connection_retry_max_backoff.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
    lib.wstunnel_config_set_connection_retry_max_backoff.restype = ctypes.c_int32

    lib.wstunnel_config_set_http_proxy.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_config_set_http_proxy.restype = ctypes.c_int32

    lib.wstunnel_config_add_http_header.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.wstunnel_config_add_http_header.restype = ctypes.c_int32

    lib.wstunnel_config_set_worker_threads.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.wstunnel_config_set_worker_threads.restype = ctypes.c_int32

    # --- Tunnel Rules ---
    lib.wstunnel_config_add_tunnel_udp.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint16,
        ctypes.c_char_p, ctypes.c_uint16, ctypes.c_uint64,
    ]
    lib.wstunnel_config_add_tunnel_udp.restype = ctypes.c_int32

    lib.wstunnel_config_add_tunnel_tcp.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint16,
        ctypes.c_char_p, ctypes.c_uint16,
    ]
    lib.wstunnel_config_add_tunnel_tcp.restype = ctypes.c_int32

    lib.wstunnel_config_add_tunnel_socks5.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint16, ctypes.c_uint64,
    ]
    lib.wstunnel_config_add_tunnel_socks5.restype = ctypes.c_int32

    # --- Client Control ---
    lib.wstunnel_client_start.argtypes = [ctypes.c_void_p]
    lib.wstunnel_client_start.restype = ctypes.c_int32

    lib.wstunnel_client_stop.argtypes = []
    lib.wstunnel_client_stop.restype = ctypes.c_int32

    lib.wstunnel_client_is_running.argtypes = []
    lib.wstunnel_client_is_running.restype = ctypes.c_int32

    lib.wstunnel_client_get_last_error.argtypes = []
    lib.wstunnel_client_get_last_error.restype = ctypes.c_char_p

    lib.wstunnel_get_version.argtypes = []
    lib.wstunnel_get_version.restype = ctypes.c_char_p


# --- Convenience ---

_log_callback_ref = None


def set_log_callback(callback: Callable[[int, str], None]) -> None:
    """Set global log callback. callback(level: int, message: str)"""
    global _log_callback_ref

    def _c_callback(level, message, _context):
        callback(int(level), message.decode("utf-8") if message else "")

    _log_callback_ref = _WS_LOG_CALLBACK_TYPE(_c_callback)
    get_lib().wstunnel_set_log_callback(_log_callback_ref, None)


def get_version() -> str:
    result = get_lib().wstunnel_get_version()
    return result.decode("utf-8") if result else "unknown"