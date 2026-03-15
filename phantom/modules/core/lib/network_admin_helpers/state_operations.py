"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: StateOperations - Sistem durumu analizi yardımcı modülü
    =====================================================================

    Ghost Mode, Multihop, aktif bağlantılar, SSH yapılandırması ve ağ
    arayüzleri dahil olmak üzere sistem durumunu analiz eder.

    Ana Sorumluluklar:
        - Ghost Mode aktivasyon durumunu kontrol et
        - Multihop aktivasyon durumunu kontrol et
        - Aktif WireGuard bağlantılarını say
        - SSH port yapılandırmasını tespit et
        - Ana ağ arayüzünü analiz et
        - Durum dosyası değişikliklerini izle

EN: StateOperations - Helper module for system state analysis
    =====================================================================

    Analyzes system state including Ghost Mode, Multihop, active
    connections, SSH configuration, and network interfaces.

    Main Responsibilities:
        - Check Ghost Mode activation status
        - Check Multihop activation status
        - Count active WireGuard connections
        - Detect SSH port configuration
        - Analyze main network interface
        - Monitor state file changes

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Callable

from phantom.modules.core.lib.default_constants import (
    GHOST_STATE_FILENAME,
    DEFAULT_SSH_PORT
)

from phantom.modules.core.lib.default_constants import (
    ACTIVE_CONNECTION_THRESHOLD
)

# Import models if available
try:
    from phantom.modules.core.models import MainInterfaceInfo
except ImportError:
    # Fallback if models not available
    class MainInterfaceInfo:
        def __init__(self, interface: str, ip: str, network: str):
            self.interface = interface
            self.ip = ip
            self.network = network

        def to_dict(self) -> Dict[str, Any]:
            return {
                "interface": self.interface,
                "ip": self.ip,
                "network": self.network
            }


class _StateOperations:
    """
    Internal helper class for system state analysis.

    Responsibilities:
        - Check Ghost Mode activation status
        - Check Multihop activation status
        - Count active WireGuard connections
        - Detect SSH port configuration from system
        - Analyze main network interface details
        - Monitor state file changes
    """

    def __init__(self, install_dir: Path, config: Dict[str, Any],
                 run_command: Callable, wg_interface: str):
        """
        Initialize state operations helper
        
        Args:
            install_dir: Installation directory path
            config: Main configuration dictionary
            run_command: Command execution function
            wg_interface: WireGuard interface name
        """
        self.install_dir = install_dir
        self.config = config
        self._run_command = run_command
        self.wg_interface = wg_interface

    def detect_ssh_port(self) -> str:
        """
        Detect the SSH port from system configuration
        
        Returns:
            SSH port as string (default "22")
        """
        try:
            # Read SSH port from sshd_config file
            sshd_config = Path("/etc/ssh/sshd_config")
            if sshd_config.exists():
                with open(sshd_config, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("Port ") and not line.startswith("#"):
                            port = line.split()[1]
                            return port

            # Alternative: check which port SSH is actively listening on
            result = self._run_command(["ss", "-tlnp"])
            if result["returncode"] == 0:
                for line in result["stdout"].split('\n'):
                    if "sshd" in line:
                        # Parse port number from socket statistics output
                        parts = line.split()
                        for part in parts:
                            if ':' in part:
                                port = part.split(':')[-1]
                                if port.isdigit():
                                    return port
        except (OSError, IOError, ValueError, KeyError, IndexError):
            # Handle common errors: file not found, permissions, parsing issues
            pass

        # Return default SSH port as fallback
        return DEFAULT_SSH_PORT

    def check_state_file_enabled(self, state_filename: str) -> bool:
        """
        Check if a state file indicates an enabled state
        
        Args:
            state_filename: Name of the state file to check
        
        Returns:
            True if state is enabled, False otherwise
        """
        state_file = self.install_dir / "config" / state_filename
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    return state.get("enabled", False)
            except (json.JSONDecodeError, OSError):
                pass
        return False

    def check_if_ghost_mode_is_active(self) -> bool:
        """
        Check if Ghost Mode is currently active
        
        Returns:
            True if Ghost Mode is active, False otherwise
        """
        return self.check_state_file_enabled(GHOST_STATE_FILENAME)

    def check_if_multihop_is_active(self) -> bool:
        """
        Check if Multihop is currently active
        
        Returns:
            True if Multihop is active, False otherwise
        """
        multihop_config = self.config.get("multihop", {})
        return multihop_config.get("enabled", False)

    def count_active_connections(self) -> int:
        """
        Count active WireGuard connections based on recent handshakes
        
        Returns:
            Number of active connections
        """
        try:
            result = self._run_command(["wg", "show", self.wg_interface, "latest-handshakes"])
            if result["returncode"] == 0:
                # Count connections with handshakes within threshold time
                current_time = int(time.time())
                active_count = 0

                for line in result["stdout"].strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) == 2:
                            try:
                                handshake_time = int(parts[1])
                                if current_time - handshake_time < ACTIVE_CONNECTION_THRESHOLD:
                                    active_count += 1
                            except ValueError:
                                continue

                return active_count
        except (ValueError, KeyError, IndexError):
            pass
        return 0

    def analyze_main_network_interface_typed(self) -> MainInterfaceInfo:
        """
        Analyze the main network interface (typed version)
        
        Returns:
            MainInterfaceInfo object with interface details
        """
        try:
            # Find the interface used for default route
            result = self._run_command(["ip", "route", "show", "default"])
            if result["returncode"] == 0 and result["stdout"]:
                # Extract interface name from default route
                parts = result["stdout"].strip().split()
                if "dev" in parts:
                    dev_index = parts.index("dev")
                    if dev_index + 1 < len(parts):
                        interface = parts[dev_index + 1]

                        # Retrieve IP address for the interface
                        ip_result = self._run_command(["ip", "addr", "show", interface])
                        if ip_result["returncode"] == 0:
                            for line in ip_result["stdout"].split('\n'):
                                if 'inet ' in line and not line.strip().startswith('inet6'):
                                    ip_part = line.strip().split()[1]
                                    return MainInterfaceInfo(
                                        interface=interface,
                                        ip=ip_part.split('/')[0],
                                        network=ip_part
                                    )
        except (ValueError, KeyError, IndexError, AttributeError):
            pass

        return MainInterfaceInfo(
            interface="unknown",
            ip="unknown",
            network="unknown"
        )

    def analyze_main_network_interface(self) -> Dict[str, Any]:
        """
        Analyze the main network interface (dict version)
        
        Returns:
            Dictionary with interface details
        """
        # Convert typed result to dictionary format
        result: MainInterfaceInfo = self.analyze_main_network_interface_typed()
        return result.to_dict()
