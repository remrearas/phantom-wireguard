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

Low-level ctypes bindings to wireguard_go_bridge.so (v2 API).
"""

import ctypes
import ctypes.util
import os
import platform
from typing import Optional

_lib: Optional[ctypes.CDLL] = None


def _resolve_platform() -> tuple[str, str]:
    system = platform.system().lower()
    arch = platform.machine()
    ext = ".dylib" if system == "darwin" else ".so"
    lib_name = f"wireguard_go_bridge{ext}"
    arch_map = {
        ("linux", "x86_64"): "linux-amd64",
        ("linux", "aarch64"): "linux-arm64",
        ("linux", "arm64"): "linux-arm64",
        ("darwin", "arm64"): "darwin-arm64",
        ("darwin", "x86_64"): "darwin-amd64",
    }
    arch_dir = arch_map.get((system, arch), f"{system}-{arch}")
    return lib_name, arch_dir


def _find_library() -> str:
    env_path = os.environ.get("WIREGUARD_GO_BRIDGE_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    lib_name, arch_dir = _resolve_platform()

    # Check dist/ directory (CI-published artifacts)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist", arch_dir, lib_name)
    if os.path.isfile(dist_path):
        return dist_path

    found = ctypes.util.find_library("wireguard_go_bridge")
    if found:
        return found

    raise FileNotFoundError(
        f"{lib_name} not found. Set WIREGUARD_GO_BRIDGE_LIB_PATH environment variable."
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


# Log callback type: void(int32_t level, const char *message, void *context)
LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int32, ctypes.c_char_p, ctypes.c_void_p)

# prevent GC of active callback
_active_log_callback = None


def _setup_signatures(lib: ctypes.CDLL) -> None:
    """Define C function signatures for v2 API."""

    c_p = ctypes.c_char_p       # input strings (Python → Go)
    c_vp = ctypes.c_void_p      # output strings (Go → Python, must FreeString)
    c_i32 = ctypes.c_int32
    c_i64 = ctypes.c_int64
    c_int = ctypes.c_int
    c_u32 = ctypes.c_uint32

    # ---- Log Callback ----

    lib.BridgeSetLogCallback.argtypes = [LOG_CALLBACK_TYPE, ctypes.c_void_p]
    lib.BridgeSetLogCallback.restype = None

    # ---- Bridge-DB High-Level API ----

    lib.BridgeInit.argtypes = [c_p, c_p, c_int, c_int]
    lib.BridgeInit.restype = c_i32

    lib.BridgeGetStatus.argtypes = []
    lib.BridgeGetStatus.restype = c_vp

    lib.BridgeSetup.argtypes = [c_p, c_p, c_p, c_p, c_int, c_int]
    lib.BridgeSetup.restype = c_i32

    lib.BridgeClose.argtypes = []
    lib.BridgeClose.restype = c_i32

    lib.BridgeStart.argtypes = []
    lib.BridgeStart.restype = c_i32

    lib.BridgeStop.argtypes = []
    lib.BridgeStop.restype = c_i32

    lib.BridgeAddClient.argtypes = [c_p]
    lib.BridgeAddClient.restype = c_vp

    lib.BridgeRemoveClient.argtypes = [c_p]
    lib.BridgeRemoveClient.restype = c_i32

    lib.BridgeEnableClient.argtypes = [c_p]
    lib.BridgeEnableClient.restype = c_i32

    lib.BridgeDisableClient.argtypes = [c_p]
    lib.BridgeDisableClient.restype = c_i32

    lib.BridgeGetClient.argtypes = [c_p]
    lib.BridgeGetClient.restype = c_vp

    lib.BridgeListClients.argtypes = [c_int, c_int]
    lib.BridgeListClients.restype = c_vp

    lib.BridgeExportClientConfig.argtypes = [c_p, c_p, c_p]
    lib.BridgeExportClientConfig.restype = c_vp

    lib.BridgeStartStatsSync.argtypes = [c_int]
    lib.BridgeStartStatsSync.restype = c_i32

    lib.BridgeStopStatsSync.argtypes = []
    lib.BridgeStopStatsSync.restype = c_i32

    lib.BridgeGetDeviceInfo.argtypes = []
    lib.BridgeGetDeviceInfo.restype = c_vp

    # ---- Server Config API ----

    lib.BridgeGetServerConfig.argtypes = []
    lib.BridgeGetServerConfig.restype = c_vp

    lib.BridgeSetServerConfig.argtypes = [c_p]
    lib.BridgeSetServerConfig.restype = c_i32

    # ---- Multihop Tunnel API ----

    lib.BridgeCreateMultihopTunnel.argtypes = [c_p, c_p, c_p, c_p, c_int]
    lib.BridgeCreateMultihopTunnel.restype = c_vp

    lib.BridgeStartMultihopTunnel.argtypes = [c_p]
    lib.BridgeStartMultihopTunnel.restype = c_i32

    lib.BridgeStopMultihopTunnel.argtypes = [c_p]
    lib.BridgeStopMultihopTunnel.restype = c_i32

    lib.BridgeDisableMultihopTunnel.argtypes = [c_p]
    lib.BridgeDisableMultihopTunnel.restype = c_i32

    lib.BridgeDeleteMultihopTunnel.argtypes = [c_p]
    lib.BridgeDeleteMultihopTunnel.restype = c_i32

    lib.BridgeListMultihopTunnels.argtypes = []
    lib.BridgeListMultihopTunnels.restype = c_vp

    lib.BridgeGetMultihopTunnel.argtypes = [c_p]
    lib.BridgeGetMultihopTunnel.restype = c_vp

    # ---- Low-Level Device API (multihop/advanced) ----

    lib.NewDevice.argtypes = [c_p, c_int, c_i64]
    lib.NewDevice.restype = c_i64

    lib.DeviceClose.argtypes = [c_i64]
    lib.DeviceClose.restype = c_i32

    lib.DeviceUp.argtypes = [c_i64]
    lib.DeviceUp.restype = c_i32

    lib.DeviceDown.argtypes = [c_i64]
    lib.DeviceDown.restype = c_i32

    lib.DeviceSetPrivateKey.argtypes = [c_i64, c_p]
    lib.DeviceSetPrivateKey.restype = c_i32

    lib.DeviceIpcSet.argtypes = [c_i64, c_p]
    lib.DeviceIpcSet.restype = c_i32

    lib.DeviceIpcGet.argtypes = [c_i64]
    lib.DeviceIpcGet.restype = c_vp

    lib.DeviceNewPeer.argtypes = [c_i64, c_p]
    lib.DeviceNewPeer.restype = c_i64

    lib.DeviceLookupPeer.argtypes = [c_i64, c_p]
    lib.DeviceLookupPeer.restype = c_i64

    lib.DeviceRemovePeer.argtypes = [c_i64, c_p]
    lib.DeviceRemovePeer.restype = c_i32

    lib.DeviceRemoveAllPeers.argtypes = [c_i64]
    lib.DeviceRemoveAllPeers.restype = c_i32

    lib.DeviceBindClose.argtypes = [c_i64]
    lib.DeviceBindClose.restype = c_i32

    lib.DeviceBindUpdate.argtypes = [c_i64]
    lib.DeviceBindUpdate.restype = c_i32

    lib.DeviceBindSetMark.argtypes = [c_i64, c_u32]
    lib.DeviceBindSetMark.restype = c_i32

    lib.AllowedIpsInsert.argtypes = [c_i64, c_p, c_p]
    lib.AllowedIpsInsert.restype = c_i32

    lib.PeerStart.argtypes = [c_i64]
    lib.PeerStart.restype = c_i32

    lib.PeerStop.argtypes = [c_i64]
    lib.PeerStop.restype = c_i32

    # ---- Key Generation ----

    lib.GeneratePrivateKey.argtypes = []
    lib.GeneratePrivateKey.restype = c_vp

    lib.DerivePublicKey.argtypes = [c_p]
    lib.DerivePublicKey.restype = c_vp

    lib.GeneratePresharedKey.argtypes = []
    lib.GeneratePresharedKey.restype = c_vp

    # ---- Version & Utility ----

    lib.BridgeVersion.argtypes = []
    lib.BridgeVersion.restype = c_vp

    lib.WireguardGoVersion.argtypes = []
    lib.WireguardGoVersion.restype = c_vp

    lib.FreeString.argtypes = [c_p]
    lib.FreeString.restype = None

    # ---- UAPI / Run (tests) ----

    lib.Run.argtypes = [c_p, c_int]
    lib.Run.restype = c_i32

    lib.DeviceUAPIListen.argtypes = [c_i64, c_p]
    lib.DeviceUAPIListen.restype = c_i32

    lib.DeviceUAPIClose.argtypes = [c_i64, c_p]
    lib.DeviceUAPIClose.restype = c_i32

    lib.DeviceUAPISocketPath.argtypes = [c_p]
    lib.DeviceUAPISocketPath.restype = c_vp


def _read_and_free(ptr) -> str:
    """Read a Go-allocated C string and free it."""
    if not ptr:
        return ""
    s = ctypes.cast(ptr, ctypes.c_char_p)
    text = s.value.decode("utf-8") if s.value else ""
    get_lib().FreeString(s)
    return text


def get_bridge_version() -> str:
    return _read_and_free(get_lib().BridgeVersion()) or "unknown"


def get_wireguard_go_version() -> str:
    return _read_and_free(get_lib().WireguardGoVersion()) or "unknown"
