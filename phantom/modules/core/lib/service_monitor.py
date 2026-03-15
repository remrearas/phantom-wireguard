"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: ServiceMonitor Manager - WireGuard servis sağlığını izleme ve durum bilgisi sağlama
    =================================================================================
    
    Bu sınıf, WireGuard VPN servisinin kapsamlı sağlık izlemesini gerçekleştirir.
    Servis durumu, interface istatistikleri, güvenlik duvarı yapılandırması ve
    aktif bağlantıları takip eder.
    
    Ana Sorumluluklar:
        - WireGuard servis durumu kontrolü ve sağlık analizi
        - Interface istatistikleri ve peer bağlantı durumu
        - Güvenlik duvarı (UFW/iptables) konfigürasyon izleme
        - Sistem kayıtları (logs) alımı ve analizi
        - Güvenli servis yeniden başlatma işlemleri
        - Aktif istemci bağlantılarının takibi
        
    Izlenen Parametreler:
        - Servis durumu (aktif/pasif, PID, başlangıç zamanı)
        - Interface durumu (UP/DOWN, port, public key)
        - Peer istatistikleri (handshake, transfer, allowed IPs)
        - Güvenlik duvarı kuralları (UFW, iptables, NAT)
        - Sistem bilgileri (kernel modülü, açık portlar)
        - Bağlantı kalitesi (son handshake zamanları)
        
    Güvenlik:
        - Güvenli servis yeniden başlatma
        - Hata toleransı ve fallback mekanizmaları
        - Sistem kayıtlarına güvenli erişim
        - Ağ interfacesi durum doğrulaması

EN: ServiceMonitor Manager - Monitor WireGuard service health and provide status information
    ====================================================================================
    
    This class performs comprehensive health monitoring of the WireGuard VPN service.
    Tracks service status, interface statistics, firewall configuration and
    active connections.
    
    Main Responsibilities:
        - WireGuard service status checking and health analysis
        - Interface statistics and peer connection status
        - Firewall (UFW/iptables) configuration monitoring
        - System logs retrieval and analysis
        - Safe service restart operations
        - Active client connection tracking
        
    Monitored Parameters:
        - Service status (active/inactive, PID, start time)
        - Interface status (UP/DOWN, port, public key)
        - Peer statistics (handshake, transfer, allowed IPs)
        - Firewall rules (UFW, iptables, NAT)
        - System information (kernel module, open ports)
        - Connection quality (recent handshake times)
        
    Security:
        - Safe service restart procedures
        - Error tolerance and fallback mechanisms
        - Secure access to system logs
        - Network interface status validation

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from pathlib import Path
from typing import Dict, Any

from phantom.api.exceptions import ServiceOperationError
from ..models import (
    ServiceHealth, ServiceLogs, RestartResult,
    ServiceStatus, ClientStatistics, ServerConfig, SystemInfo,
    FirewallConfiguration, InterfaceStatistics
)

from .default_constants import (
    DEFAULT_LOG_LINES,
    DEFAULT_WG_PORT,
    DEFAULT_WG_NETWORK,
    DEFAULT_DNS_PRIMARY,
    DEFAULT_DNS_SECONDARY,
    ACTIVE_CONNECTION_THRESHOLD
)

import re

class ServiceMonitor:
    """WireGuard service health and status monitoring.

    Performs comprehensive monitoring of WireGuard VPN service including
    service status, interface statistics and active connections.

    Core Functions:
        - Real-time service health checking
        - Interface and peer statistics collection
        - Firewall rule analysis
        - System log access and log analysis
        - Safe service restart operations
        - Active connection quality assessment

    Features:
        - Multi-source information gathering
        - Error tolerance and fallback strategies
        - Detailed system status reporting
        - Performance metrics calculation
    """

    def __init__(self, data_store, common_tools, config: Dict[str, Any],
                 run_command, wg_interface: str, wg_config_file: Path, install_dir: Path):
        self.data_store = data_store
        self.common_tools = common_tools
        self.config = config
        self._run_command = run_command
        self.wg_interface = wg_interface
        self.wg_config_file = wg_config_file
        self.install_dir = install_dir

    def check_wireguard_health(self) -> ServiceHealth:
        try:
            service_status: ServiceStatus = self._get_service_running_status()
            interface_stats: InterfaceStatistics = self._get_interface_statistics()
            server_config: ServerConfig = self._get_server_config_info()
            client_stats: ClientStatistics = self._get_client_statistics()
            system_info: SystemInfo = self._get_system_information()

            # Create health status
            health: ServiceHealth = ServiceHealth(
                service=service_status,
                interface=interface_stats,
                configuration=server_config,
                clients=client_stats,
                system=system_info
            )

            return health

        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to check WireGuard health")
            raise ServiceOperationError(
                "Unable to retrieve server status. This may indicate:\n"
                "• WireGuard service is not installed properly\n"
                "• Insufficient permissions to access service status\n"
                "• System services are not responding\n\n"
                "Try running with sudo or check 'systemctl status wg-quick@wg_main' manually."
            )

    def _retrieve_service_logs_typed(self, lines: int = DEFAULT_LOG_LINES) -> 'ServiceLogs':
        # Import to avoid circular dependency
        from ..models import ServiceLogs

        try:
            # Get logs from systemd
            result = self._run_command([
                "journalctl", "-u", f"wg-quick@{self.wg_interface}",
                "-n", str(lines), "--no-pager"
            ])

            if result["success"]:
                log_lines = result["stdout"].strip().split('\n') if result["stdout"] else []

                # Parse log entries
                parsed_logs = []
                for line in log_lines:
                    if line.strip():
                        parsed_logs.append(line)

                return ServiceLogs(
                    logs=parsed_logs,
                    count=len(parsed_logs),
                    service=f"wg-quick@{self.wg_interface}",
                    lines_requested=lines
                )
            else:
                # No logs available
                return ServiceLogs(
                    logs=[],
                    count=0,
                    service=f"wg-quick@{self.wg_interface}",
                    lines_requested=lines,
                    message="No logs available"
                )

        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to retrieve service logs")
            raise ServiceOperationError(
                "Unable to retrieve service logs. Please check:\n"
                "• journalctl is installed and accessible\n"
                "• You have permission to read system logs\n"
                "• The service name 'wg-quick@wg_main' is correct\n\n"
                "Try manually: 'journalctl -u wg-quick@wg_main -n 50'"
            )

    def retrieve_service_logs(self, lines: int = DEFAULT_LOG_LINES) -> Dict[str, Any]:
        result: ServiceLogs = self._retrieve_service_logs_typed(lines)
        return result.to_dict()

    def _restart_wireguard_safely_typed(self) -> RestartResult:
        try:
            # Perform restart
            self.perform_service_restart()

            # Verify service is running
            post_restart_status = self.check_service_is_running()

            # Check interface status
            interface_status = self.check_interface_is_active()

            return RestartResult(
                restarted=True,
                service_active=post_restart_status["running"],
                interface_up=interface_status,
                service=f"wg-quick@{self.wg_interface}",
                message="Service restarted successfully"
            )

        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to restart WireGuard service")

            # Attempt to start service if restart failed
            try:
                self._run_command(["systemctl", "start", f"wg-quick@{self.wg_interface}"])
            except (OSError, RuntimeError):
                pass

            raise ServiceOperationError(
                "Failed to restart WireGuard service. Common causes:\n"
                "• Configuration syntax errors - check with 'wg-quick strip wg_main'\n"
                f"• Port {DEFAULT_WG_PORT} already in use - check with 'ss -ulnp | grep {DEFAULT_WG_PORT}'\n"
                "• Missing WireGuard kernel module - verify with 'lsmod | grep wireguard'\n"
                "• Insufficient permissions - try with sudo\n\n"
                "Check logs with 'journalctl -u wg-quick@wg_main -n 50' for details."
            )

    def restart_wireguard_safely(self) -> Dict[str, Any]:
        result: RestartResult = self._restart_wireguard_safely_typed()
        return result.to_dict()

    def _check_firewall_configuration_typed(self) -> FirewallConfiguration:
        try:
            ufw_info = self.check_ufw_status()
            iptables_info = self.check_iptables_rules()
            nat_info = self.check_nat_configuration()
            ports_info = self.check_open_ports()

            # Determine overall status
            status = "active" if (
                    ufw_info["enabled"] or
                    iptables_info["has_rules"]
            ) else "inactive"

            return FirewallConfiguration(
                ufw=ufw_info,
                iptables=iptables_info,
                nat=nat_info,
                ports=ports_info,
                status=status
            )

        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to check firewall status")
            raise ServiceOperationError(
                "Unable to check firewall status. Please verify:\n"
                "• UFW is installed: 'apt install ufw'\n"
                "• You have permission to query firewall rules\n"
                "• iptables is accessible for NAT rule checking\n\n"
                "Manual checks:\n"
                "• UFW status: 'ufw status verbose'\n"
                "• NAT rules: 'iptables -t nat -L POSTROUTING -n -v'"
            )

    def check_firewall_configuration(self) -> Dict[str, Any]:
        result: FirewallConfiguration = self._check_firewall_configuration_typed()
        return result.to_dict()

    def check_service_is_running(self) -> Dict[str, Any]:
        service_status: ServiceStatus = self._get_service_running_status()
        return service_status.to_dict()

    def _get_service_running_status(self) -> ServiceStatus:
        result = self._run_command(["systemctl", "is-active", f"wg-quick@{self.wg_interface}"])
        is_running = result["success"] and result["stdout"].strip() == "active"

        service_name = f"wg-quick@{self.wg_interface}"
        started_at = None
        pid = None

        # Get service details if active
        if is_running:
            result = self._run_command([
                "systemctl", "show", f"wg-quick@{self.wg_interface}",
                "--property=ActiveEnterTimestamp,MainPID"
            ])
            if result["success"]:
                for line in result["stdout"].strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key == "ActiveEnterTimestamp":
                            started_at = value
                        elif key == "MainPID":
                            pid = value

        return ServiceStatus(
            running=is_running,
            service_name=service_name,
            started_at=started_at,
            pid=pid
        )

    def gather_interface_statistics(self) -> Dict[str, Any]:
        interface_stats: InterfaceStatistics = self._get_interface_statistics()
        return interface_stats.to_dict()

    def _get_interface_statistics(self) -> InterfaceStatistics:
        # Check interface existence
        result = self._run_command(["ip", "link", "show", self.wg_interface])
        interface_exists = result["success"]

        if not interface_exists:
            return InterfaceStatistics(
                active=False,
                interface=self.wg_interface,
                peers=[]
            )

        # Get interface details
        result = self._run_command(["wg", "show", self.wg_interface])
        if not result["success"]:
            return InterfaceStatistics(
                active=False,
                interface=self.wg_interface,
                peers=[]
            )

        # Parse wg show output
        parsed_data = self.common_tools.parse_wg_show_output(result["stdout"])

        # Extract interface info
        public_key = parsed_data["interface"].get("public_key")
        port = parsed_data["interface"].get("listening_port")
        peers = parsed_data["peers"]

        # Get interface statistics
        rx_bytes = None
        tx_bytes = None
        result = self._run_command(["ip", "-s", "link", "show", self.wg_interface])
        if result["success"]:
            # Parse RX/TX bytes
            lines = result["stdout"].strip().split('\n')
            for i, line in enumerate(lines):
                if 'RX:' in line and i + 1 < len(lines):
                    rx_parts = lines[i + 1].strip().split()
                    if len(rx_parts) >= 1:
                        try:
                            rx_bytes = int(rx_parts[0])
                        except (ValueError, IndexError):
                            pass
                elif 'TX:' in line and i + 1 < len(lines):
                    tx_parts = lines[i + 1].strip().split()
                    if len(tx_parts) >= 1:
                        try:
                            tx_bytes = int(tx_parts[0])
                        except (ValueError, IndexError):
                            pass

        return InterfaceStatistics(
            active=True,
            interface=self.wg_interface,
            peers=peers,
            public_key=public_key,
            port=port,
            rx_bytes=rx_bytes,
            tx_bytes=tx_bytes
        )

    def retrieve_server_configuration(self) -> Dict[str, Any]:
        server_config: ServerConfig = self._get_server_config_info()
        return server_config.to_dict()

    def _get_server_config_info(self) -> ServerConfig:
        # Get configuration
        wg_config = self.config.get('wireguard', {})
        port = wg_config.get('port', DEFAULT_WG_PORT)
        network = wg_config.get('network', DEFAULT_WG_NETWORK)

        # Get DNS servers
        dns_config = self.config.get('dns', {})
        dns_servers = [
            dns_config.get('primary', DEFAULT_DNS_PRIMARY),
            dns_config.get('secondary', DEFAULT_DNS_SECONDARY)
        ]

        # Check config file existence
        config_exists = self.wg_config_file.exists()

        return ServerConfig(
            interface=self.wg_interface,
            config_file=str(self.wg_config_file),
            port=port,
            network=network,
            dns=dns_servers,
            config_exists=config_exists
        )

    def calculate_client_statistics(self) -> Dict[str, Any]:
        client_stats: ClientStatistics = self._get_client_statistics()
        return client_stats.to_dict()

    def _get_client_statistics(self) -> ClientStatistics:
        try:
            # Get all clients
            all_clients = self.data_store.get_all_clients()

            # Count client states
            enabled_count = sum(1 for c in all_clients if c.enabled)
            disabled_count = len(all_clients) - enabled_count

            # Get active connections
            active_connections = self.gather_active_connections()

            return ClientStatistics(
                total_configured=len(all_clients),
                enabled_clients=enabled_count,
                disabled_clients=disabled_count,
                active_connections=len(active_connections)
            )

        except (AttributeError, KeyError, TypeError, ValueError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to calculate client statistics: {e}")
            # Return defaults on error
            return ClientStatistics(
                total_configured=0,
                enabled_clients=0,
                disabled_clients=0,
                active_connections=0
            )

    def gather_system_information(self) -> Dict[str, Any]:
        system_info: SystemInfo = self._get_system_information()
        return system_info.to_dict()

    def _get_system_information(self) -> SystemInfo:
        # Directory paths
        install_dir = str(self.install_dir)
        config_dir = str(self.install_dir / "config")
        data_dir = str(self.install_dir / "data")

        # Check firewall status
        ufw_result = self._run_command(["ufw", "status"])
        firewall_info = {
            "status": "active" if ufw_result["success"] and "Status: active" in ufw_result["stdout"] else "inactive"
        }

        # Check kernel module
        wireguard_module = False
        lsmod_result = self._run_command(["lsmod"])
        if lsmod_result["success"]:
            wireguard_module = "wireguard" in lsmod_result["stdout"]

        return SystemInfo(
            install_dir=install_dir,
            config_dir=config_dir,
            data_dir=data_dir,
            firewall=firewall_info,
            wireguard_module=wireguard_module
        )

    def perform_service_restart(self) -> None:
        import time

        result = self._run_command(["systemctl", "restart", f"wg-quick@{self.wg_interface}"])

        if not result["success"]:
            # Fallback to wg-quick approach
            self._run_command(["wg-quick", "down", self.wg_interface])
            time.sleep(1)

            result = self._run_command(["wg-quick", "up", self.wg_interface])
            if not result["success"]:
                raise ServiceOperationError(
                    "Unable to restart WireGuard service. Please:\n"
                    "• Check service status: 'systemctl status wg-quick@wg_main'\n"
                    "• Review logs: 'journalctl -u wg-quick@wg_main -n 50'\n"
                    "• Verify config syntax: 'wg-quick strip wg_main'\n"
                    "If issues persist, manually restart with 'systemctl restart wg-quick@wg_main'"
                )

        # Wait for service initialization
        time.sleep(2)

    def check_interface_is_active(self) -> bool:
        result = self._run_command(["ip", "link", "show", self.wg_interface])
        return result["success"] and "UP" in result["stdout"]

    def check_ufw_status(self) -> Dict[str, Any]:
        ufw_info = {
            "enabled": False,
            "rules": []
        }

        result = self._run_command(["ufw", "status", "verbose"])
        if result["success"]:
            output = result["stdout"]
            ufw_info["enabled"] = "Status: active" in output

            # Parse UFW rules
            if ufw_info["enabled"]:
                lines = output.strip().split('\n')
                for line in lines:
                    if self.wg_interface in line or str(DEFAULT_WG_PORT) in line:
                        ufw_info["rules"].append(line.strip())

        return ufw_info

    def check_iptables_rules(self) -> Dict[str, Any]:
        iptables_info = {
            "has_rules": False,
            "nat_rules": [],
            "filter_rules": []
        }

        # Check NAT rules
        result = self._run_command(["iptables", "-t", "nat", "-L", "-n"])
        if result["success"]:
            output = result["stdout"]
            if self.wg_interface in output or DEFAULT_WG_NETWORK.split('/')[0] in output:
                iptables_info["has_rules"] = True
                # Extract relevant lines
                for line in output.split('\n'):
                    if self.wg_interface in line:
                        iptables_info["nat_rules"].append(line.strip())

        # Check filter rules
        result = self._run_command(["iptables", "-L", "-n"])
        if result["success"]:
            output = result["stdout"]
            for line in output.split('\n'):
                if self.wg_interface in line:
                    iptables_info["has_rules"] = True
                    iptables_info["filter_rules"].append(line.strip())

        return iptables_info

    def check_nat_configuration(self) -> Dict[str, Any]:
        nat_info = {
            "enabled": False,
            "rules": []
        }

        # Check POSTROUTING chain
        result = self._run_command(["iptables", "-t", "nat", "-L", "POSTROUTING", "-n"])
        if result["success"]:
            output = result["stdout"]
            for line in output.split('\n'):
                if "MASQUERADE" in line:
                    nat_info["enabled"] = True
                    nat_info["rules"].append(line.strip())

        return nat_info

    def check_open_ports(self) -> Dict[str, Any]:
        wg_port = self.config.get('wireguard', {}).get('port', DEFAULT_WG_PORT)
        ports_info = {
            "wireguard_port": wg_port,
            "listening": False
        }

        # Check if port is listening
        result = self._run_command(["ss", "-tunlp"])
        if result["success"]:
            if str(ports_info["wireguard_port"]) in result["stdout"]:
                ports_info["listening"] = True

        return ports_info

    @staticmethod
    def parse_handshake_to_seconds(handshake_str):
        """Parse WireGuard handshake string to total seconds
        Based on WireGuard's show.c implementation"""

        if not handshake_str or handshake_str == "Now" or handshake_str == "0 seconds ago":
            return 0

        total_seconds = 0

        # WireGuard uses: years, days, hours, minutes, seconds
        years = re.search(r'(\d+)\s+years?', handshake_str)
        days = re.search(r'(\d+)\s+days?', handshake_str)
        hours = re.search(r'(\d+)\s+hours?', handshake_str)
        minutes = re.search(r'(\d+)\s+minutes?', handshake_str)
        seconds = re.search(r'(\d+)\s+seconds?', handshake_str)

        if years:
            total_seconds += int(years.group(1)) * 365 * 24 * 60 * 60
        if days:
            total_seconds += int(days.group(1)) * 24 * 60 * 60
        if hours:
            total_seconds += int(hours.group(1)) * 60 * 60
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))

        return total_seconds

    def gather_active_connections(self) -> Dict[str, Any]:
        active_connections: Dict[str, Any] = {}

        # Get interface statistics
        interface_stats = self.gather_interface_statistics()

        if interface_stats.get("active") and interface_stats.get("peers"):
            # Get clients for name mapping
            all_clients = self.data_store.get_all_clients()

            # Create IP to name mapping
            ip_to_name = {}
            for client in all_clients:
                ip = client.ip
                if ip:
                    ip_to_name[f"{ip}/32"] = client.name

            # Process each peer
            for peer in interface_stats["peers"]:
                allowed_ips = peer.get("allowed_ips", "")
                client_name = ip_to_name.get(allowed_ips, "Unknown")

                # Check if handshake is recent
                latest_handshake = peer.get("latest_handshake", "")
                if latest_handshake:
                    if latest_handshake == "Now":
                        # "Now" kesinlikle aktif demektir
                        active_connections[client_name] = {
                            "public_key": peer.get("public_key"),
                            "allowed_ips": allowed_ips,
                            "latest_handshake": latest_handshake,
                            "endpoint": peer.get("endpoint", "N/A"),
                            "transfer": peer.get("transfer", {})
                        }
                    else:
                        # Parse handshake time
                        total_seconds = ServiceMonitor.parse_handshake_to_seconds(latest_handshake)
                        is_recent = total_seconds < ACTIVE_CONNECTION_THRESHOLD
                        if is_recent:
                            active_connections[client_name] = {
                                "public_key": peer.get("public_key"),
                                "allowed_ips": allowed_ips,
                                "latest_handshake": latest_handshake,
                                "endpoint": peer.get("endpoint", "N/A"),
                                "transfer": peer.get("transfer", {})
                            }

        return active_connections
