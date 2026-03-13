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

Curve25519 key generation via Go FFI.
"""

from ._ffi import get_lib, _read_and_free


def generate_private_key() -> str:
    """Generate a new Curve25519 private key. Returns hex string."""
    result = _read_and_free(get_lib().GeneratePrivateKey())
    if not result:
        raise RuntimeError("Failed to generate private key")
    return result


def derive_public_key(private_key_hex: str) -> str:
    """Derive public key from private key. Returns hex string."""
    result = _read_and_free(
        get_lib().DerivePublicKey(private_key_hex.encode("utf-8"))
    )
    if not result:
        raise ValueError("Failed to derive public key")
    return result


def generate_preshared_key() -> str:
    """Generate a random 32-byte preshared key. Returns hex string."""
    result = _read_and_free(get_lib().GeneratePresharedKey())
    if not result:
        raise RuntimeError("Failed to generate preshared key")
    return result


def hex_to_base64(hex_str: str) -> str:
    """Convert hex-encoded key to base64 (WireGuard config format)."""
    result = _read_and_free(
        get_lib().HexToBase64(hex_str.encode("utf-8"))
    )
    if not result:
        raise ValueError("Failed to convert hex to base64")
    return result
