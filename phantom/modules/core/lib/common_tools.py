"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: CommonTools Manager - Tüm manager'lar için paylaşılan yardımcı araçlar
    =====================================================================
    
    Bu sınıf, diğer tüm manager'ların kullandığı ortak araçları ve yardımcı
    fonksiyonları sağlar. Kod tekrarını önler ve tutarlılık sağlar.
    
    Ana İşlevler:
        - İstemci adı doğrulaması (alfanümerik + - _)
        - Standart API yanıt formatları
        - Sunucu public key yönetimi
        - Bant genişliği hesaplamaları
        - Hata yönetimi ve standartlaştırma
        
    Doğrulama Kuralları:
        - Maksimum istemci adı: 50 karakter
        - İzin verilen karakterler: a-z, A-Z, 0-9, -, _
        - WireGuard anahtar uzunluğu: 44 karakter

EN: CommonTools Manager - Provide shared utilities for all managers
    ===============================================================
    
    This class provides common tools and utility functions used by
    all other managers. Prevents code duplication and ensures consistency.
    
    Main Functions:
        - Client name validation (alphanumeric + - _)
        - Standard API response formats
        - Server public key management
        - Bandwidth calculations
        - Error handling and standardization
        
    Validation Rules:
        - Maximum client name: 50 characters
        - Allowed characters: a-z, A-Z, 0-9, -, _
        - WireGuard key length: 44 characters

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import re
from typing import Dict, Any, List

from phantom.api.exceptions import (
    InvalidClientNameError,
    ConfigurationError
)
from ..models import (
    SuccessResponse,
    ErrorResponse,
    TransferData,
    WireGuardShowData
)
from .default_constants import (
    WG_KEY_LENGTH,
    MAX_CLIENT_NAME_LENGTH
)


class CommonTools:
    """Provides shared utility functions for all manager classes.

    This class centralizes common functionality to prevent code duplication
    and ensure consistent behavior across all managers.

    Key Functions:
        - Client name validation (alphanumeric + hyphen/underscore)
        - Standard API response formatting (success/error)
        - Server public key retrieval and derivation
        - Bandwidth string parsing and conversion
        - WireGuard output parsing and structuring
    """

    def __init__(self, config: Dict[str, Any], run_command):
        self.config = config
        self._run_command = run_command

    # noinspection PyMethodMayBeStatic
    def ensure_name_is_valid(self, name: str) -> None:
        """Validate client name against naming rules.

        Args:
            name: Client name to validate

        Raises:
            InvalidClientNameError: If name is empty, contains invalid
                                    characters, or exceeds max length
        """
        if not name:
            raise InvalidClientNameError("Client name cannot be empty")

        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise InvalidClientNameError(
                f"Client name '{name}' contains invalid characters. "
                "Only letters, numbers, underscore and hyphen are allowed"
            )

        if len(name) > MAX_CLIENT_NAME_LENGTH:
            raise InvalidClientNameError(
                f"Client name '{name}' is too long. Maximum {MAX_CLIENT_NAME_LENGTH} characters allowed"
            )

    # noinspection PyMethodMayBeStatic
    def _create_success_response_typed(self, data: Dict[str, Any], message: str = "") -> SuccessResponse:
        return SuccessResponse(
            success=True,
            data=data,
            message=message if message else None
        )

    # noinspection PyMethodMayBeStatic
    def create_success_response(self, data: Dict[str, Any], message: str = "") -> Dict[str, Any]:
        result: SuccessResponse = self._create_success_response_typed(data, message)
        return result.to_dict()

    # noinspection PyMethodMayBeStatic
    def _create_error_response_typed(self, error: str, code: str = "ERROR") -> ErrorResponse:
        return ErrorResponse(
            success=False,
            error=error,
            code=code
        )

    # noinspection PyMethodMayBeStatic
    def create_error_response(self, error: str, code: str = "ERROR") -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            error: Error message
            code: Error code (default: "ERROR")

        Returns:
            Dictionary with error response structure
        """
        result: ErrorResponse = self._create_error_response_typed(error, code)
        return result.to_dict()

    def retrieve_server_public_key(self) -> str:
        """Get server public key from config or derive from private key.

        Returns:
            44-character WireGuard public key string

        Raises:
            ConfigurationError: If public key cannot be obtained
        """
        server_config = self.config.get("server", {})
        public_key = server_config.get("public_key", "")

        # Check for pre-configured public key
        if public_key and len(public_key) == WG_KEY_LENGTH:
            return public_key

        # Derive from private key using wg pubkey
        private_key = server_config.get("private_key", "")
        if private_key:
            result = self._run_command(
                ["wg", "pubkey"],
                input=private_key,
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()

        raise ConfigurationError("Server public key not found in configuration")

    # noinspection PyMethodMayBeStatic
    def parse_bandwidth_to_bytes(self, transfer_str: str) -> int:
        """Convert bandwidth strings to bytes.

        Supports both binary (KiB, MiB, GiB) and decimal (KB, MB, GB) units.

        Args:
            transfer_str: Bandwidth string like '1.23 GiB'

        Returns:
            Number of bytes as integer, or 0 if parsing fails
        """
        try:
            parts = transfer_str.strip().split()
            if len(parts) != 2:
                return 0

            value = float(parts[0])
            unit = parts[1].upper()

            multipliers = {
                'B': 1,
                'KIB': 1024,
                'MIB': 1024 * 1024,
                'GIB': 1024 * 1024 * 1024,
                'TIB': 1024 * 1024 * 1024 * 1024,
                'KB': 1000,
                'MB': 1000 * 1000,
                'GB': 1000 * 1000 * 1000,
                'TB': 1000 * 1000 * 1000 * 1000
            }

            multiplier = multipliers.get(unit, 1)
            return int(value * multiplier)
        except (ValueError, IndexError, AttributeError):
            return 0

    def _parse_wg_transfer_data_typed(self, transfer_line: str) -> TransferData:
        import re

        received_str = "0 B"
        sent_str = "0 B"
        received_bytes = 0
        sent_bytes = 0

        try:
            # Match transfer pattern
            pattern = r'(\d+(?:\.\d+)?)\s+(\w+)\s+received,\s+(\d+(?:\.\d+)?)\s+(\w+)\s+sent'
            match = re.match(pattern, transfer_line.strip())

            if match:
                rx_value, rx_unit, tx_value, tx_unit = match.groups()

                received_str = f"{rx_value} {rx_unit}"
                sent_str = f"{tx_value} {tx_unit}"

                received_bytes = self.parse_bandwidth_to_bytes(received_str)
                sent_bytes = self.parse_bandwidth_to_bytes(sent_str)

        except (ValueError, AttributeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse transfer data '{transfer_line}': {e}")

        return TransferData(
            received=received_str,
            sent=sent_str,
            received_bytes=received_bytes,
            sent_bytes=sent_bytes
        )

    # noinspection PyMethodMayBeStatic
    def parse_wg_transfer_data(self, transfer_line: str) -> Dict[str, Any]:
        result: TransferData = self._parse_wg_transfer_data_typed(transfer_line)
        return result.to_dict()

    def _parse_wg_show_output_typed(self, output: str) -> WireGuardShowData:
        interface_data = {}
        peers_data = []

        try:
            sections = self._split_wg_sections(output)

            interface_data = self._parse_interface_section(sections.get("interface", []))

            for peer_lines in sections.get("peers", []):
                peer_data = self._parse_peer_section(peer_lines)
                if peer_data:  # Skip empty peers
                    peers_data.append(peer_data)

        except (ValueError, AttributeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to parse wg show output: {e}")

        return WireGuardShowData(
            interface=interface_data,
            peers=peers_data
        )

    # noinspection PyMethodMayBeStatic
    def parse_wg_show_output(self, output: str) -> Dict[str, Any]:
        result: WireGuardShowData = self._parse_wg_show_output_typed(output)
        return result.to_dict()

    # noinspection PyMethodMayBeStatic
    def _split_wg_sections(self, output: str) -> Dict[str, Any]:
        """Split 'wg show' output into structured sections.

        Args:
            output: Raw output from 'wg show' command

        Returns:
            Dictionary with 'interface' and 'peers' sections
        """
        import re

        lines = output.strip().split('\n')
        sections = {
            "interface": [],
            "peers": []
        }

        current_section = None
        current_peer_lines = []

        for line in lines:
            if not line.strip():
                continue

            if re.match(r'^interface:', line):
                current_section = "interface"
                sections["interface"].append(line)
            elif re.match(r'^peer:', line):
                if current_peer_lines:
                    sections["peers"].append(current_peer_lines)

                current_section = "peer"
                current_peer_lines = [line]
            elif current_section == "interface":
                sections["interface"].append(line)
            elif current_section == "peer":
                current_peer_lines.append(line)

        # Add final peer section
        if current_peer_lines:
            sections["peers"].append(current_peer_lines)

        return sections

    # noinspection PyMethodMayBeStatic
    def _parse_interface_section(self, lines: List[str]) -> Dict[str, Any]:
        """Extract interface configuration from wg show output.

        Args:
            lines: Lines containing interface data

        Returns:
            Dictionary with interface name, keys, and port
        """
        interface_data = {}

        for line in lines:
            if line.startswith('interface:'):
                interface_name = line.split(':', 1)[1].strip()
                interface_data["name"] = interface_name
            else:
                key, value = self._parse_key_value_line(line)
                if key == "public key":
                    interface_data["public_key"] = value
                elif key == "private key":
                    interface_data["private_key"] = value
                elif key == "listening port":
                    try:
                        interface_data["listening_port"] = int(value)
                    except ValueError:
                        interface_data["listening_port"] = 0

        return interface_data

    # noinspection PyMethodMayBeStatic
    def _parse_peer_section(self, lines: List[str]) -> Dict[str, Any]:
        """Extract peer configuration from wg show output.

        Args:
            lines: Lines containing peer data

        Returns:
            Dictionary with peer public key, endpoint, transfer stats, etc.
        """
        peer_data = {}

        for line in lines:
            if line.startswith('peer:'):
                peer_key = line.split(':', 1)[1].strip()
                peer_data["public_key"] = peer_key
            else:
                key, value = self._parse_key_value_line(line)
                if key == "preshared key":
                    peer_data["preshared_key"] = value
                elif key == "endpoint":
                    peer_data["endpoint"] = value
                elif key == "allowed ips":
                    peer_data["allowed_ips"] = value
                elif key == "latest handshake":
                    peer_data["latest_handshake"] = value
                elif key == "transfer":
                    peer_data["transfer"] = self.parse_wg_transfer_data(value)

        return peer_data

    # noinspection PyMethodMayBeStatic
    def _parse_key_value_line(self, line: str) -> tuple[str, str]:
        """Parse colon-separated key-value lines.

        Args:
            line: Line in 'key: value' format

        Returns:
            Tuple of (key, value) strings, or ("", "") if no colon found
        """
        if ':' not in line:
            return "", ""

        # Split on first colon only
        clean_line = line.lstrip()
        key, value = clean_line.split(':', 1)

        return key.strip(), value.strip()
