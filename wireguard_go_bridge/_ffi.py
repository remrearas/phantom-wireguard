"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
Low-level ctypes bindings to wireguard_go_bridge.so.
All other modules use this as the FFI foundation.
"""

import ctypes
import ctypes.util
import os
import platform
from typing import Callable, Optional

# --- Library Loading ---

_lib: Optional[ctypes.CDLL] = None


def _resolve_platform() -> tuple[str, str]:
    """Resolve library filename and architecture directory for current platform."""
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
    """Locate wireguard_go_bridge shared library via environment variable."""
    env_path = os.environ.get("WIREGUARD_GO_BRIDGE_LIB_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    lib_name, _ = _resolve_platform()
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


# --- Function Signatures ---


def _setup_signatures(lib: ctypes.CDLL) -> None:
    """Define C function signatures for type safety."""

    # --- Logger ---
    lib.SetLogCallback.argtypes = [_WG_LOG_CALLBACK_TYPE, ctypes.c_void_p]
    lib.SetLogCallback.restype = None

    lib.NewLogger.argtypes = [ctypes.c_int, ctypes.c_char_p]
    lib.NewLogger.restype = ctypes.c_int64

    lib.LoggerFree.argtypes = [ctypes.c_int64]
    lib.LoggerFree.restype = None

    # --- Device Lifecycle ---
    lib.NewDevice.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int64]
    lib.NewDevice.restype = ctypes.c_int64

    lib.DeviceClose.argtypes = [ctypes.c_int64]
    lib.DeviceClose.restype = ctypes.c_int32

    lib.DeviceUp.argtypes = [ctypes.c_int64]
    lib.DeviceUp.restype = ctypes.c_int32

    lib.DeviceDown.argtypes = [ctypes.c_int64]
    lib.DeviceDown.restype = ctypes.c_int32

    # --- IPC ---
    lib.DeviceIpcSet.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceIpcSet.restype = ctypes.c_int32

    lib.DeviceIpcGet.argtypes = [ctypes.c_int64]
    lib.DeviceIpcGet.restype = ctypes.c_char_p

    lib.DeviceIpcSetOperation.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceIpcSetOperation.restype = ctypes.c_int64

    # --- Bind ---
    lib.DeviceBindClose.argtypes = [ctypes.c_int64]
    lib.DeviceBindClose.restype = ctypes.c_int32

    lib.DeviceBindUpdate.argtypes = [ctypes.c_int64]
    lib.DeviceBindUpdate.restype = ctypes.c_int32

    lib.DeviceBindSetMark.argtypes = [ctypes.c_int64, ctypes.c_uint32]
    lib.DeviceBindSetMark.restype = ctypes.c_int32

    # --- Device State ---
    lib.DeviceBatchSize.argtypes = [ctypes.c_int64]
    lib.DeviceBatchSize.restype = ctypes.c_int

    lib.DeviceIsUnderLoad.argtypes = [ctypes.c_int64]
    lib.DeviceIsUnderLoad.restype = ctypes.c_bool

    lib.DeviceWait.argtypes = [ctypes.c_int64]
    lib.DeviceWait.restype = ctypes.c_int32

    # --- Device Key ---
    lib.DeviceSetPrivateKey.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceSetPrivateKey.restype = ctypes.c_int32

    # --- Peer Management via Device ---
    lib.DeviceNewPeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceNewPeer.restype = ctypes.c_int64

    lib.DeviceLookupPeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceLookupPeer.restype = ctypes.c_int64

    lib.DeviceRemovePeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceRemovePeer.restype = ctypes.c_int32

    lib.DeviceRemoveAllPeers.argtypes = [ctypes.c_int64]
    lib.DeviceRemoveAllPeers.restype = ctypes.c_int32

    # --- Device Misc ---
    lib.DevicePopulatePools.argtypes = [ctypes.c_int64]
    lib.DevicePopulatePools.restype = ctypes.c_int32

    lib.DeviceDisableRoaming.argtypes = [ctypes.c_int64]
    lib.DeviceDisableRoaming.restype = ctypes.c_int32

    lib.DeviceSendKeepalivesToPeers.argtypes = [ctypes.c_int64]
    lib.DeviceSendKeepalivesToPeers.restype = ctypes.c_int32

    # --- Run (full wireguard-go foreground equivalent) ---
    lib.Run.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.Run.restype = ctypes.c_int32

    # --- UAPI Socket ---
    lib.DeviceUAPIListen.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceUAPIListen.restype = ctypes.c_int32

    lib.DeviceUAPIClose.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.DeviceUAPIClose.restype = ctypes.c_int32

    lib.DeviceUAPISocketPath.argtypes = [ctypes.c_char_p]
    lib.DeviceUAPISocketPath.restype = ctypes.c_char_p

    # --- Peer ---
    lib.PeerStart.argtypes = [ctypes.c_int64]
    lib.PeerStart.restype = ctypes.c_int32

    lib.PeerStop.argtypes = [ctypes.c_int64]
    lib.PeerStop.restype = ctypes.c_int32

    lib.PeerString.argtypes = [ctypes.c_int64]
    lib.PeerString.restype = ctypes.c_char_p

    lib.PeerFree.argtypes = [ctypes.c_int64]
    lib.PeerFree.restype = None

    lib.PeerSendHandshakeInitiation.argtypes = [ctypes.c_int64, ctypes.c_bool]
    lib.PeerSendHandshakeInitiation.restype = ctypes.c_int32

    lib.PeerSendHandshakeResponse.argtypes = [ctypes.c_int64]
    lib.PeerSendHandshakeResponse.restype = ctypes.c_int32

    lib.PeerBeginSymmetricSession.argtypes = [ctypes.c_int64]
    lib.PeerBeginSymmetricSession.restype = ctypes.c_int32

    lib.PeerSendKeepalive.argtypes = [ctypes.c_int64]
    lib.PeerSendKeepalive.restype = ctypes.c_int32

    lib.PeerSendStagedPackets.argtypes = [ctypes.c_int64]
    lib.PeerSendStagedPackets.restype = ctypes.c_int32

    lib.PeerExpireCurrentKeypairs.argtypes = [ctypes.c_int64]
    lib.PeerExpireCurrentKeypairs.restype = ctypes.c_int32

    lib.PeerFlushStagedPackets.argtypes = [ctypes.c_int64]
    lib.PeerFlushStagedPackets.restype = ctypes.c_int32

    lib.PeerZeroAndFlushAll.argtypes = [ctypes.c_int64]
    lib.PeerZeroAndFlushAll.restype = ctypes.c_int32

    # --- Keys ---
    lib.GeneratePrivateKey.argtypes = []
    lib.GeneratePrivateKey.restype = ctypes.c_char_p

    lib.DerivePublicKey.argtypes = [ctypes.c_char_p]
    lib.DerivePublicKey.restype = ctypes.c_char_p

    lib.GeneratePresharedKey.argtypes = []
    lib.GeneratePresharedKey.restype = ctypes.c_char_p

    lib.PrivateKeyIsZero.argtypes = [ctypes.c_char_p]
    lib.PrivateKeyIsZero.restype = ctypes.c_bool

    lib.PrivateKeyEquals.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.PrivateKeyEquals.restype = ctypes.c_bool

    lib.PublicKeyIsZero.argtypes = [ctypes.c_char_p]
    lib.PublicKeyIsZero.restype = ctypes.c_bool

    lib.PublicKeyEquals.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.PublicKeyEquals.restype = ctypes.c_bool

    # --- Crypto ---
    lib.HMAC1.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.HMAC1.restype = None

    lib.HMAC2.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.HMAC2.restype = None

    lib.KDF1.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.KDF1.restype = None

    lib.KDF2.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p,
    ]
    lib.KDF2.restype = None

    lib.KDF3.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ]
    lib.KDF3.restype = None

    lib.Blake2sSize.argtypes = []
    lib.Blake2sSize.restype = ctypes.c_int

    # --- AllowedIPs ---
    lib.AllowedIpsInsert.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_char_p]
    lib.AllowedIpsInsert.restype = ctypes.c_int32

    lib.AllowedIpsRemoveByPeer.argtypes = [ctypes.c_int64, ctypes.c_int64]
    lib.AllowedIpsRemoveByPeer.restype = ctypes.c_int32

    lib.AllowedIpsGetForPeer.argtypes = [ctypes.c_int64, ctypes.c_int64]
    lib.AllowedIpsGetForPeer.restype = ctypes.c_char_p

    # --- Version ---
    lib.BridgeVersion.argtypes = []
    lib.BridgeVersion.restype = ctypes.c_char_p

    lib.WireguardGoVersion.argtypes = []
    lib.WireguardGoVersion.restype = ctypes.c_char_p

    # --- Diagnostics ---
    lib.ActiveDeviceCount.argtypes = []
    lib.ActiveDeviceCount.restype = ctypes.c_int

    lib.ActivePeerCount.argtypes = []
    lib.ActivePeerCount.restype = ctypes.c_int

    # --- Memory ---
    lib.FreeString.argtypes = [ctypes.c_char_p]
    lib.FreeString.restype = None


# --- Convenience ---

# Store callback reference to prevent GC
_log_callback_ref = None

_WG_LOG_CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int32, ctypes.c_char_p, ctypes.c_void_p)


def set_log_callback(callback: Callable[[int, str], None]) -> None:
    """Set global log callback. callback(level: int, message: str)"""
    global _log_callback_ref

    def _c_callback(level, message, _context):
        callback(int(level), message.decode("utf-8") if message else "")

    _log_callback_ref = _WG_LOG_CALLBACK_TYPE(_c_callback)
    get_lib().SetLogCallback(_log_callback_ref, None)


def get_bridge_version() -> str:
    result = get_lib().BridgeVersion()
    return result.decode("utf-8") if result else "unknown"


def get_wireguard_go_version() -> str:
    result = get_lib().WireguardGoVersion()
    return result.decode("utf-8") if result else "unknown"