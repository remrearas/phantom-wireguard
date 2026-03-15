"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Multihop Modülü Bağlantı Test Aracı
    ====================================

    VPN bağlantı durumunu test eder, handshake kontrolü yapar,
    IP sızıntı testleri gerçekleştirir ve bağlantı kalitesini ölçer.

EN: Multihop Module Connection Tester
    ==================================

    Tests VPN connection status, performs handshake verification,
    conducts IP leak tests and measures connection quality.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import re
import time
from pathlib import Path
from typing import Dict, Any, Optional

from .common_tools import (
    VPN_INTERFACE_NAME, DEFAULT_HANDSHAKE_TIMEOUT
)


class ConnectionTester:

    def __init__(self, config: Dict[str, Any], logger, run_command_func):
        self.config = config
        self.logger = logger
        self._run_command = run_command_func

    def wait_for_vpn_handshake(self, timeout: int = DEFAULT_HANDSHAKE_TIMEOUT) -> Dict[str, Any]:
        self.logger.info(f"Waiting for VPN handshake (timeout: {timeout}s)")

        for i in range(timeout):
            try:
                result = self._run_command(["wg", "show", VPN_INTERFACE_NAME, "latest-handshakes"])

                if result["success"] and result["stdout"].strip():
                    self.logger.info(f"VPN handshake established after {i + 1} seconds")
                    return {"success": True, "seconds": i + 1}

                time.sleep(1)

            except Exception as e:
                self.logger.warning(f"Handshake check failed: {e}")
                time.sleep(1)
                continue

        self.logger.error(f"VPN handshake timeout after {timeout} seconds")
        return {"success": False, "timeout": timeout}

    def test_vpn_connection_silently(self, exit_name: Optional[str] = None, exit_configs_dir: Optional[Path] = None) -> \
            Dict[str, Any]:
        try:
            if not exit_name:
                return {"success": False, "error": "No exit name provided"}

            if exit_configs_dir:
                exit_config_file = exit_configs_dir / f"{exit_name}.conf"
                if not exit_config_file.exists():
                    return {"success": False, "error": f"VPN config '{exit_name}' not found"}

            # Verify WireGuard handshake status
            wg_result = self._run_command(["wg", "show", VPN_INTERFACE_NAME])
            if wg_result["success"] and 'latest handshake' in wg_result["stdout"]:
                # Extract handshake timestamp
                handshake_match = re.search(r'latest handshake:\s*(.+)', wg_result["stdout"])
                if handshake_match:
                    handshake_text = handshake_match.group(1).strip()
                    return {"success": True, "handshake": handshake_text}
                else:
                    return {"success": False, "error": "Could not parse handshake timestamp"}
            else:
                return {"success": False, "error": "No recent handshake"}

        except Exception as e:
            self.logger.error(f"Silent VPN test failed: {e}")
            return {"success": False, "error": str(e)}


