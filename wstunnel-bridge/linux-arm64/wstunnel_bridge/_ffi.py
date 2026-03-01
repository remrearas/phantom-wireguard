"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Low-level ctypes bindings to libwstunnel_bridge_linux.so.
All other modules use this as the FFI foundation.
"""

import ctypes
import ctypes.util
import logging
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
    """Locate wstunnel bridge shared library."""
    env_path = os.environ.get("WSTUNNEL_BRIDGE_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    lib_name, _ = _resolve_platform()

    # Sibling path — .so alongside _ffi.py (vendor-pack layout)
    sibling_path = os.path.join(os.path.dirname(__file__), lib_name)
    if os.path.isfile(sibling_path):
        return sibling_path

    found = ctypes.util.find_library("wstunnel_bridge_linux")
    if found:
        return found

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

    # --- Server Config Builder ---
    lib.wstunnel_server_config_new.argtypes = []
    lib.wstunnel_server_config_new.restype = ctypes.c_void_p

    lib.wstunnel_server_config_free.argtypes = [ctypes.c_void_p]
    lib.wstunnel_server_config_free.restype = None

    lib.wstunnel_server_config_set_bind_url.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_set_bind_url.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_tls_certificate.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_set_tls_certificate.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_tls_private_key.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_set_tls_private_key.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_tls_client_ca_certs.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_set_tls_client_ca_certs.restype = ctypes.c_int32

    lib.wstunnel_server_config_add_restrict_to.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_add_restrict_to.restype = ctypes.c_int32

    lib.wstunnel_server_config_add_restrict_path_prefix.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.wstunnel_server_config_add_restrict_path_prefix.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_websocket_ping_frequency.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.wstunnel_server_config_set_websocket_ping_frequency.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_websocket_mask_frame.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    lib.wstunnel_server_config_set_websocket_mask_frame.restype = ctypes.c_int32

    lib.wstunnel_server_config_set_worker_threads.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    lib.wstunnel_server_config_set_worker_threads.restype = ctypes.c_int32

    # --- Server Control ---
    lib.wstunnel_server_start.argtypes = [ctypes.c_void_p]
    lib.wstunnel_server_start.restype = ctypes.c_int32

    lib.wstunnel_server_stop.argtypes = []
    lib.wstunnel_server_stop.restype = ctypes.c_int32

    lib.wstunnel_server_is_running.argtypes = []
    lib.wstunnel_server_is_running.restype = ctypes.c_int32

    lib.wstunnel_server_get_last_error.argtypes = []
    lib.wstunnel_server_get_last_error.restype = ctypes.c_char_p


# --- Logging ---

_log = logging.getLogger("wstunnel_bridge")

# Rust → Python level mapping
_LEVEL_MAP = {
    0: logging.ERROR,    # WS_LOG_ERROR
    1: logging.WARNING,  # WS_LOG_WARN
    2: logging.INFO,     # WS_LOG_INFO
    3: logging.DEBUG,    # WS_LOG_DEBUG
    4: logging.DEBUG,    # WS_LOG_TRACE → DEBUG (Python has no TRACE)
}

# Prevent GC of active callback
_active_log_callback = None
_log_callback_registered = False


def _setup_log_callback() -> None:
    """Register Rust→Python log bridge (once). Called by Client/Server init."""
    global _active_log_callback, _log_callback_registered
    if _log_callback_registered:
        return

    def _callback(level, message, _context):
        py_level = _LEVEL_MAP.get(level, logging.DEBUG)
        text = message.decode("utf-8") if message else ""
        _log.log(py_level, text)

    _active_log_callback = _WS_LOG_CALLBACK_TYPE(_callback)
    get_lib().wstunnel_set_log_callback(_active_log_callback, None)
    _log_callback_registered = True


def set_log_callback(callback: Callable[[int, str], None]) -> None:
    """Set custom log callback — overrides default Python logging bridge."""
    global _active_log_callback, _log_callback_registered

    def _c_callback(level, message, _context):
        callback(int(level), message.decode("utf-8") if message else "")

    _active_log_callback = _WS_LOG_CALLBACK_TYPE(_c_callback)
    get_lib().wstunnel_set_log_callback(_active_log_callback, None)
    _log_callback_registered = True


def get_version() -> str:
    result = get_lib().wstunnel_get_version()
    return result.decode("utf-8") if result else "unknown"