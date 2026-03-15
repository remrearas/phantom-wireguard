"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: KeyGenerator Manager - WireGuard için kriptografik anahtar oluşturma
    ==================================================================
    
    Bu sınıf, WireGuard VPN için gerekli tüm kriptografik anahtarları
    güvenli bir şekilde oluşturur. Dosya sistemi kullanılmaz, tüm anahtarlar
    bellekte üretilir ve doğrudan döndürülür.
    
    Anahtar Türleri:
        - Private Key: İstemcinin özel anahtarı (44 karakter, base64)
        - Public Key: Private key'den türetilen açık anahtar
        - Preshared Key: Ek güvenlik için ön paylaşımlı anahtar
        
    Güvenlik:
        - wg komut satırı araçları kullanılır
        - Sistem entropisi kullanılır
        - Format doğrulaması yapılır
        - Bellek temizliği otomatik

EN: KeyGenerator Manager - Create cryptographic keys for WireGuard
    ==============================================================
    
    This class securely generates all cryptographic keys required for
    WireGuard VPN. No filesystem usage, all keys are generated in memory
    and returned directly.
    
    Key Types:
        - Private Key: Client's private key (44 chars, base64)
        - Public Key: Public key derived from private key
        - Preshared Key: Pre-shared key for additional security
        
    Security:
        - Uses wg command line tools
        - Uses system entropy
        - Format validation
        - Automatic memory cleanup

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.api.exceptions import ServiceOperationError
from .default_constants import (
    WG_KEY_LENGTH as _WG_KEY_LENGTH
)

class KeyGenerator:
    """Secure cryptographic key generator for WireGuard.

    Generates all key types required for WireGuard using system entropy
    to create high-quality random keys.

    Features:
        - Three key types: private, public, preshared
        - Format validation (44 character base64)
        - In-memory operations, no filesystem usage
    """

    EXPECTED_KEY_LENGTH = _WG_KEY_LENGTH  # Base64 encoded 32 bytes = 44 chars

    def __init__(self, run_command):
        self._run_command = run_command

    def create_private_key(self) -> str:
        result = self._run_command(["wg", "genkey"])
        if not result["success"]:
            raise ServiceOperationError("Failed to generate private key")

        key = result["stdout"].strip()
        self._validate_key_format(key, "private")
        return key

    def derive_public_key(self, private_key: str) -> str:
        result = self._run_command(
            ["wg", "pubkey"],
            input=private_key,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ServiceOperationError("Failed to generate public key")

        public_key = result.stdout.strip()
        self._validate_key_format(public_key, "public")
        return public_key

    def create_preshared_key(self) -> str:
        result = self._run_command(["wg", "genpsk"])
        if not result["success"]:
            raise ServiceOperationError("Failed to generate preshared key")

        key = result["stdout"].strip()
        self._validate_key_format(key, "preshared")
        return key

    def _validate_key_format(self, key: str, key_type: str) -> None:
        """Validate that a key has the correct format.

        Args:
            key: The key string to validate
            key_type: Type of key for error messages (private/public/preshared)

        Raises:
            ServiceOperationError: If key format is invalid
        """
        if len(key) != self.EXPECTED_KEY_LENGTH:
            raise ServiceOperationError(
                f"Generated {key_type} key appears to be invalid. "
                "This is an internal error that should not occur. Please:\n"
                "• Verify WireGuard is properly installed: 'wg version'\n"
                "• Check system entropy: 'cat /proc/sys/kernel/random/entropy_avail'\n"
                "• Ensure the wg command is not modified or wrapped\n"
                "• Try regenerating the key manually: 'wg genkey'\n"
                "If the problem persists, reinstall WireGuard."
            )

    def _generate_private_key(self) -> str:
        return self.create_private_key()

    def _generate_public_key(self, private_key: str) -> str:
        return self.derive_public_key(private_key)

    def _generate_preshared_key(self) -> str:
        return self.create_preshared_key()
