"""
Low-level ctypes bindings to libphantom_wg.so.
All other modules use this as the FFI foundation.
"""

import ctypes
import ctypes.util
import os
import platform
from pathlib import Path
from typing import Callable, Optional

# --- Library Loading ---

_lib: Optional[ctypes.CDLL] = None


def _find_library() -> str:
    """Locate libphantom_wg.so using search order."""
    # 1. Explicit env var
    env_path = os.environ.get("LIBPHANTOM_WG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2. Relative to this package (development layout)
    pkg_dir = Path(__file__).parent
    arch = platform.machine()
    arch_map = {"x86_64": "linux-amd64", "aarch64": "linux-arm64", "arm64": "linux-arm64"}
    arch_dir = arch_map.get(arch, f"linux-{arch}")

    candidates = [
        pkg_dir / "libphantom_wg.so",
        pkg_dir.parent.parent / "lib" / arch_dir / "libphantom_wg.so",
        Path("/opt/phantom-wg/lib/libphantom_wg.so"),
        Path("/usr/local/lib/libphantom_wg.so"),
        Path("/usr/lib/libphantom_wg.so"),
    ]

    for path in candidates:
        if path.is_file():
            return str(path)

    # 3. System library path
    found = ctypes.util.find_library("phantom_wg")
    if found:
        return found

    raise FileNotFoundError(
        "libphantom_wg.so not found. Set LIBPHANTOM_WG_PATH or place it in a standard location."
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
    lib.wgSetLogCallback.argtypes = [_WG_LOG_CALLBACK_TYPE, ctypes.c_void_p]
    lib.wgSetLogCallback.restype = None

    lib.wgNewLogger.argtypes = [ctypes.c_int, ctypes.c_char_p]
    lib.wgNewLogger.restype = ctypes.c_int64

    lib.wgLoggerFree.argtypes = [ctypes.c_int64]
    lib.wgLoggerFree.restype = None

    # --- Device Lifecycle ---
    lib.wgDeviceCreate.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int64]
    lib.wgDeviceCreate.restype = ctypes.c_int64

    lib.wgDeviceClose.argtypes = [ctypes.c_int64]
    lib.wgDeviceClose.restype = ctypes.c_int32

    lib.wgDeviceUp.argtypes = [ctypes.c_int64]
    lib.wgDeviceUp.restype = ctypes.c_int32

    lib.wgDeviceDown.argtypes = [ctypes.c_int64]
    lib.wgDeviceDown.restype = ctypes.c_int32

    # --- IPC ---
    lib.wgDeviceIpcSet.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceIpcSet.restype = ctypes.c_int32

    lib.wgDeviceIpcGet.argtypes = [ctypes.c_int64]
    lib.wgDeviceIpcGet.restype = ctypes.c_char_p

    lib.wgDeviceIpcSetOperation.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceIpcSetOperation.restype = ctypes.c_int64

    # --- Bind ---
    lib.wgDeviceBindClose.argtypes = [ctypes.c_int64]
    lib.wgDeviceBindClose.restype = ctypes.c_int32

    lib.wgDeviceBindUpdate.argtypes = [ctypes.c_int64]
    lib.wgDeviceBindUpdate.restype = ctypes.c_int32

    lib.wgDeviceBindSetMark.argtypes = [ctypes.c_int64, ctypes.c_uint32]
    lib.wgDeviceBindSetMark.restype = ctypes.c_int32

    # --- Device State ---
    lib.wgDeviceBatchSize.argtypes = [ctypes.c_int64]
    lib.wgDeviceBatchSize.restype = ctypes.c_int

    lib.wgDeviceIsUnderLoad.argtypes = [ctypes.c_int64]
    lib.wgDeviceIsUnderLoad.restype = ctypes.c_bool

    lib.wgDeviceWait.argtypes = [ctypes.c_int64]
    lib.wgDeviceWait.restype = ctypes.c_int32

    # --- Device Key ---
    lib.wgDeviceSetPrivateKey.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceSetPrivateKey.restype = ctypes.c_int32

    # --- Peer Management via Device ---
    lib.wgDeviceNewPeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceNewPeer.restype = ctypes.c_int64

    lib.wgDeviceLookupPeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceLookupPeer.restype = ctypes.c_int64

    lib.wgDeviceRemovePeer.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgDeviceRemovePeer.restype = ctypes.c_int32

    lib.wgDeviceRemoveAllPeers.argtypes = [ctypes.c_int64]
    lib.wgDeviceRemoveAllPeers.restype = ctypes.c_int32

    # --- Device Misc ---
    lib.wgDevicePopulatePools.argtypes = [ctypes.c_int64]
    lib.wgDevicePopulatePools.restype = ctypes.c_int32

    lib.wgDeviceDisableRoaming.argtypes = [ctypes.c_int64]
    lib.wgDeviceDisableRoaming.restype = ctypes.c_int32

    lib.wgDeviceSendKeepalivesToPeers.argtypes = [ctypes.c_int64]
    lib.wgDeviceSendKeepalivesToPeers.restype = ctypes.c_int32

    # --- Peer ---
    lib.wgPeerStart.argtypes = [ctypes.c_int64]
    lib.wgPeerStart.restype = ctypes.c_int32

    lib.wgPeerStop.argtypes = [ctypes.c_int64]
    lib.wgPeerStop.restype = ctypes.c_int32

    lib.wgPeerString.argtypes = [ctypes.c_int64]
    lib.wgPeerString.restype = ctypes.c_char_p

    lib.wgPeerFree.argtypes = [ctypes.c_int64]
    lib.wgPeerFree.restype = None

    lib.wgPeerSendHandshakeInitiation.argtypes = [ctypes.c_int64, ctypes.c_bool]
    lib.wgPeerSendHandshakeInitiation.restype = ctypes.c_int32

    lib.wgPeerSendHandshakeResponse.argtypes = [ctypes.c_int64]
    lib.wgPeerSendHandshakeResponse.restype = ctypes.c_int32

    lib.wgPeerBeginSymmetricSession.argtypes = [ctypes.c_int64]
    lib.wgPeerBeginSymmetricSession.restype = ctypes.c_int32

    lib.wgPeerSendKeepalive.argtypes = [ctypes.c_int64]
    lib.wgPeerSendKeepalive.restype = ctypes.c_int32

    lib.wgPeerSendStagedPackets.argtypes = [ctypes.c_int64]
    lib.wgPeerSendStagedPackets.restype = ctypes.c_int32

    lib.wgPeerExpireCurrentKeypairs.argtypes = [ctypes.c_int64]
    lib.wgPeerExpireCurrentKeypairs.restype = ctypes.c_int32

    lib.wgPeerHasCurrentKeypair.argtypes = [ctypes.c_int64]
    lib.wgPeerHasCurrentKeypair.restype = ctypes.c_bool

    lib.wgPeerFlushStagedPackets.argtypes = [ctypes.c_int64]
    lib.wgPeerFlushStagedPackets.restype = ctypes.c_int32

    lib.wgPeerZeroAndFlushAll.argtypes = [ctypes.c_int64]
    lib.wgPeerZeroAndFlushAll.restype = ctypes.c_int32

    lib.wgPeerHandshakeClear.argtypes = [ctypes.c_int64]
    lib.wgPeerHandshakeClear.restype = ctypes.c_int32

    # --- Keys ---
    lib.wgGeneratePrivateKey.argtypes = []
    lib.wgGeneratePrivateKey.restype = ctypes.c_char_p

    lib.wgDerivePublicKey.argtypes = [ctypes.c_char_p]
    lib.wgDerivePublicKey.restype = ctypes.c_char_p

    lib.wgGeneratePresharedKey.argtypes = []
    lib.wgGeneratePresharedKey.restype = ctypes.c_char_p

    lib.wgPrivateKeyIsZero.argtypes = [ctypes.c_char_p]
    lib.wgPrivateKeyIsZero.restype = ctypes.c_bool

    lib.wgPrivateKeyEquals.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.wgPrivateKeyEquals.restype = ctypes.c_bool

    lib.wgPublicKeyIsZero.argtypes = [ctypes.c_char_p]
    lib.wgPublicKeyIsZero.restype = ctypes.c_bool

    lib.wgPublicKeyEquals.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.wgPublicKeyEquals.restype = ctypes.c_bool

    # --- Crypto ---
    lib.wgHmac1.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.wgHmac1.restype = None

    lib.wgHmac2.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.wgHmac2.restype = None

    lib.wgKdf1.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p,
    ]
    lib.wgKdf1.restype = None

    lib.wgKdf2.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p,
    ]
    lib.wgKdf2.restype = None

    lib.wgKdf3.argtypes = [
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ]
    lib.wgKdf3.restype = None

    lib.wgBlake2sSize.argtypes = []
    lib.wgBlake2sSize.restype = ctypes.c_int

    # --- AllowedIPs ---
    lib.wgAllowedIpsInsert.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_char_p]
    lib.wgAllowedIpsInsert.restype = ctypes.c_int32

    lib.wgAllowedIpsLookup.argtypes = [ctypes.c_int64, ctypes.c_char_p]
    lib.wgAllowedIpsLookup.restype = ctypes.c_int64

    lib.wgAllowedIpsRemove.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_char_p]
    lib.wgAllowedIpsRemove.restype = ctypes.c_int32

    lib.wgAllowedIpsRemoveByPeer.argtypes = [ctypes.c_int64, ctypes.c_int64]
    lib.wgAllowedIpsRemoveByPeer.restype = ctypes.c_int32

    lib.wgAllowedIpsGetForPeer.argtypes = [ctypes.c_int64, ctypes.c_int64]
    lib.wgAllowedIpsGetForPeer.restype = ctypes.c_char_p

    # --- Version ---
    lib.wgBridgeVersion.argtypes = []
    lib.wgBridgeVersion.restype = ctypes.c_char_p

    lib.wgWireguardGoVersion.argtypes = []
    lib.wgWireguardGoVersion.restype = ctypes.c_char_p

    # --- Diagnostics ---
    lib.wgActiveDeviceCount.argtypes = []
    lib.wgActiveDeviceCount.restype = ctypes.c_int

    lib.wgActivePeerCount.argtypes = []
    lib.wgActivePeerCount.restype = ctypes.c_int

    # --- Memory ---
    lib.wgFreeString.argtypes = [ctypes.c_char_p]
    lib.wgFreeString.restype = None


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
    get_lib().wgSetLogCallback(_log_callback_ref, None)


def get_bridge_version() -> str:
    result = get_lib().wgBridgeVersion()
    return result.decode("utf-8") if result else "unknown"


def get_wireguard_go_version() -> str:
    result = get_lib().wgWireguardGoVersion()
    return result.decode("utf-8") if result else "unknown"