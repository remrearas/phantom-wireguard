"""
WireGuardKeys — Pure in-process key generation.
Replaces: subprocess("wg genkey"), subprocess("wg pubkey"), subprocess("wg genpsk")
"""

from ._ffi import get_lib


class WireGuardKeys:
    """Static key generation and comparison utilities."""

    @staticmethod
    def generate_private() -> str:
        """Generate a new Curve25519 private key (hex-encoded)."""
        result = get_lib().wgGeneratePrivateKey()
        if not result:
            raise RuntimeError("Failed to generate private key")
        return result.decode("utf-8")

    @staticmethod
    def derive_public(private_key_hex: str) -> str:
        """Derive public key from private key (hex-encoded)."""
        result = get_lib().wgDerivePublicKey(private_key_hex.encode("utf-8"))
        if not result:
            raise RuntimeError("Failed to derive public key")
        return result.decode("utf-8")

    @staticmethod
    def generate_preshared() -> str:
        """Generate a new preshared key (hex-encoded)."""
        result = get_lib().wgGeneratePresharedKey()
        if not result:
            raise RuntimeError("Failed to generate preshared key")
        return result.decode("utf-8")

    @staticmethod
    def generate_keypair() -> tuple[str, str]:
        """Generate private + public key pair. Returns (private_hex, public_hex)."""
        private = WireGuardKeys.generate_private()
        public = WireGuardKeys.derive_public(private)
        return private, public

    @staticmethod
    def private_key_is_zero(key_hex: str) -> bool:
        return get_lib().wgPrivateKeyIsZero(key_hex.encode("utf-8"))

    @staticmethod
    def public_key_is_zero(key_hex: str) -> bool:
        return get_lib().wgPublicKeyIsZero(key_hex.encode("utf-8"))

    @staticmethod
    def private_keys_equal(key_a_hex: str, key_b_hex: str) -> bool:
        return get_lib().wgPrivateKeyEquals(
            key_a_hex.encode("utf-8"), key_b_hex.encode("utf-8")
        )

    @staticmethod
    def public_keys_equal(key_a_hex: str, key_b_hex: str) -> bool:
        return get_lib().wgPublicKeyEquals(
            key_a_hex.encode("utf-8"), key_b_hex.encode("utf-8")
        )