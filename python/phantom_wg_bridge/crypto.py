"""
WireGuardCrypto — HMAC and KDF primitives from wireguard-go.
Direct FFI access to the Noise protocol crypto functions.
"""

import ctypes

from ._ffi import get_lib

HASH_SIZE = 32  # blake2s.Size


class WireGuardCrypto:
    """Low-level cryptographic primitives used by WireGuard's Noise protocol."""

    @staticmethod
    def blake2s_size() -> int:
        return get_lib().wgBlake2sSize()

    @staticmethod
    def hmac1(key: bytes, in0: bytes) -> bytes:
        """HMAC1(key, in0) → 32-byte hash"""
        out = (ctypes.c_uint8 * HASH_SIZE)()
        get_lib().wgHmac1(
            key, len(key),
            in0, len(in0),
            out,
        )
        return bytes(out)

    @staticmethod
    def hmac2(key: bytes, in0: bytes, in1: bytes) -> bytes:
        """HMAC2(key, in0, in1) → 32-byte hash"""
        out = (ctypes.c_uint8 * HASH_SIZE)()
        get_lib().wgHmac2(
            key, len(key),
            in0, len(in0),
            in1, len(in1),
            out,
        )
        return bytes(out)

    @staticmethod
    def kdf1(key: bytes, input_data: bytes) -> bytes:
        """KDF1(key, input) → t0 (32 bytes)"""
        t0 = (ctypes.c_uint8 * HASH_SIZE)()
        get_lib().wgKdf1(
            key, len(key),
            input_data, len(input_data),
            t0,
        )
        return bytes(t0)

    @staticmethod
    def kdf2(key: bytes, input_data: bytes) -> tuple[bytes, bytes]:
        """KDF2(key, input) → (t0, t1) each 32 bytes"""
        t0 = (ctypes.c_uint8 * HASH_SIZE)()
        t1 = (ctypes.c_uint8 * HASH_SIZE)()
        get_lib().wgKdf2(
            key, len(key),
            input_data, len(input_data),
            t0, t1,
        )
        return bytes(t0), bytes(t1)

    @staticmethod
    def kdf3(key: bytes, input_data: bytes) -> tuple[bytes, bytes, bytes]:
        """KDF3(key, input) → (t0, t1, t2) each 32 bytes"""
        t0 = (ctypes.c_uint8 * HASH_SIZE)()
        t1 = (ctypes.c_uint8 * HASH_SIZE)()
        t2 = (ctypes.c_uint8 * HASH_SIZE)()
        get_lib().wgKdf3(
            key, len(key),
            input_data, len(input_data),
            t0, t1, t2,
        )
        return bytes(t0), bytes(t1), bytes(t2)