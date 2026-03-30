"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

TR: Casper App Servisi - Ghost Mode .conf Configuration Export Core
    ================================================================

    Bu modül, Ghost Mode client konfigürasyonlarını WireGuard .conf formatında
    isteğe bağlı [Wstunnel] bölümüyle birlikte dışa aktarır.
    Yalnızca stdout'a çıktı verir.

    Ana Bileşenler:
        - CasperAppService: .conf formatında konfigürasyon üreten ana servis sınıfı
        - Ghost durumu kontrolü ve bilgi okuma
        - Phantom API üzerinden client verilerine erişim
        - wstunnel komutunu Ghost API'den alma ve parse etme
        - AllowedIPs hesaplama algoritması (binary tree split, IPv4 + IPv6)

    Mimari:
        CasperService (casper/core.py) ile aynı API erişim desenini ve
        AllowedIPs hesaplama algoritmasını kullanır. Fark çıktı formatındadır:
        JSON yerine WireGuard .conf formatı üretir.

EN: Casper App Service - Ghost Mode .conf Configuration Export Core
    ====================================================

    This module exports Ghost Mode client configurations in WireGuard .conf
    format with an optional [Wstunnel] section. Only outputs to stdout.

    Key Components:
        - CasperAppService: Main service class producing .conf format configurations
        - Ghost state checking and information reading
        - Client data access via Phantom API
        - Fetching and parsing wstunnel command from Ghost API
        - AllowedIPs calculation algorithm (binary tree split, IPv4 + IPv6)

    Architecture:
        Uses the same API access pattern and AllowedIPs calculation algorithm
        as CasperService (casper/core.py). The difference is in output format:
        produces WireGuard .conf format instead of JSON.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import re
import json
import ipaddress
from pathlib import Path

try:
    from phantom.api.core import PhantomAPI
    from phantom.api.exceptions import ClientNotFoundError
    PHANTOM_API_AVAILABLE = True
except ImportError:
    class PhantomAPI:
        pass

    class ClientNotFoundError(Exception):
        pass

    PHANTOM_API_AVAILABLE = False


class CasperAppService:
    def __init__(self):
        self.config_dir = Path("/opt/phantom-wg/config")
        self.ghost_state_file = self.config_dir / "ghost-state.json"
        self.phantom_config_file = self.config_dir / "phantom.json"

        self.phantom_api = None
        if PHANTOM_API_AVAILABLE:
            try:
                self.phantom_api = PhantomAPI()
            except (AttributeError, TypeError, RuntimeError):
                pass

    def export_client_config(self, username):
        """Export client configuration as .conf to stdout.

        When Ghost Mode is active, output includes [Wstunnel] section.
        """
        if not self._is_ghost_active():
            raise Exception(
                "Ghost Mode is not active. Enable it first with: "
                "phantom-api ghost enable domain=your-domain.com"
            )

        ghost_info = self._get_ghost_info()
        if not ghost_info:
            raise Exception("Unable to read Ghost Mode state")

        client_data = self._get_client_data(username)
        if not client_data:
            raise Exception(f"Client '{username}' not found")

        wstunnel_cmd = self._get_wstunnel_command()
        wstunnel_params = self._parse_wstunnel_command(wstunnel_cmd)
        ghost_config = self._generate_ghost_config(client_data, ghost_info)
        parsed_wg = self._parse_wireguard_config(ghost_config)

        conf = self._build_conf(parsed_wg, wstunnel_params)
        print(conf)

    # noinspection PyListCreation
    @staticmethod
    def _build_conf(wg, wstunnel):
        """Build .conf output with [Wstunnel] + [Interface] + [Peer]."""
        lines = []

        # [Wstunnel]
        lines.append("[Wstunnel]")
        lines.append(f"Url = {wstunnel['url']}")
        lines.append(f"Secret = {wstunnel['secret']}")
        lines.append(f"Tunnel = udp://{wstunnel['local_host']}:{wstunnel['local_port']}:{wstunnel['remote_host']}:{wstunnel['remote_port']}")
        lines.append("")

        # [Interface]
        lines.append("[Interface]")
        lines.append(f"PrivateKey = {wg['private_key']}")
        lines.append(f"Address = {wg['address']}")
        lines.append(f"DNS = {wg['dns']}")
        lines.append(f"MTU = {wg['mtu']}")
        lines.append("")

        # [Peer]
        lines.append("[Peer]")
        lines.append(f"PublicKey = {wg['public_key']}")
        if wg.get("preshared_key"):
            lines.append(f"PresharedKey = {wg['preshared_key']}")
        lines.append(f"Endpoint = {wg['endpoint']}")
        lines.append(f"AllowedIPs = {wg['allowed_ips']}")
        lines.append(f"PersistentKeepalive = {wg['persistent_keepalive']}")

        return "\n".join(lines)

    # ── Ghost state ──────────────────────────────────────────────

    def _is_ghost_active(self):
        if not self.ghost_state_file.exists():
            return False
        try:
            with open(self.ghost_state_file, 'r') as f:
                state = json.load(f)
                return state.get("enabled", False)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False

    def _get_ghost_info(self):
        try:
            with open(self.ghost_state_file, 'r') as f:
                state = json.load(f)
            info = {
                "domain": state.get("domain"),
                "server_ip": state.get("server_ip"),
                "server_ipv6": None,
                "secret": state.get("secret"),
            }
            if self.phantom_config_file.exists():
                try:
                    with open(self.phantom_config_file, 'r') as f:
                        phantom_config = json.load(f)
                    info["server_ipv6"] = phantom_config.get("server", {}).get("ipv6")
                except (json.JSONDecodeError, KeyError):
                    pass
            return info
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    # ── API access ───────────────────────────────────────────────

    def _get_wstunnel_command(self):
        if not self.phantom_api:
            raise Exception("Phantom API not available")
        try:
            response = self.phantom_api.execute("ghost", "status")
            if response.success and response.data:
                return response.data.get("connection_command", "")
            return ""
        except (AttributeError, KeyError, TypeError):
            return ""

    def _get_client_data(self, client_name):
        if not self.phantom_api:
            raise Exception("Phantom API not available")
        try:
            response = self.phantom_api.execute("core", "export_client", client_name=client_name)
            if response.success:
                return response.data
            return None
        except ClientNotFoundError:
            return None
        except Exception as e:
            raise Exception(f"Failed to get client data: {e}")

    # ── Config generation ────────────────────────────────────────

    def _generate_ghost_config(self, client_data, ghost_info):
        client_config = client_data.get("config", "")
        server_ipv6 = ghost_info.get("server_ipv6")

        modified_config = client_config.replace(
            f"Endpoint = {ghost_info.get('server_ip')}:51820",
            "Endpoint = 127.0.0.1:51820",
        )

        if server_ipv6:
            modified_config = re.sub(
                r'(Address\s*=\s*[^\n]+)',
                r'\1, fd00::2/128',
                modified_config,
            )

        allowed_ips_match = re.search(r'AllowedIPs\s*=\s*([^\n]+)', modified_config)
        if allowed_ips_match and ghost_info.get('server_ip'):
            original_allowed_ips = allowed_ips_match.group(1).strip()
            new_allowed_ips = self._calculate_allowed_ips(
                original_allowed_ips, ghost_info.get('server_ip'), server_ipv6,
            )
            modified_config = re.sub(
                r'AllowedIPs\s*=\s*[^\n]+',
                f'AllowedIPs = {", ".join(new_allowed_ips)}',
                modified_config,
            )

        return modified_config

    # ── Parsers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_wstunnel_command(wstunnel_cmd):
        secret_match = re.search(r'--http-upgrade-path-prefix\s+"([^"]+)"', wstunnel_cmd)
        secret = secret_match.group(1) if secret_match else ""

        tunnel_match = re.search(r'-L\s+udp://([^:]+):(\d+):([^:]+):(\d+)', wstunnel_cmd)
        if tunnel_match:
            local_host = tunnel_match.group(1)
            local_port = int(tunnel_match.group(2))
            remote_host = tunnel_match.group(3)
            remote_port = int(tunnel_match.group(4))
        else:
            local_host = "127.0.0.1"
            local_port = 51820
            remote_host = "127.0.0.1"
            remote_port = 51820

        url_match = re.search(r'(wss://\S+)', wstunnel_cmd)
        url = url_match.group(1) if url_match else ""

        return {
            "secret": secret,
            "local_host": local_host,
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "url": url,
        }

    @staticmethod
    def _parse_wireguard_config(config_text):
        def extract(pattern, text):
            match = re.search(pattern, text)
            return match.group(1).strip() if match else None

        return {
            "private_key": extract(r'PrivateKey\s*=\s*(.+)', config_text),
            "address": extract(r'Address\s*=\s*(.+)', config_text),
            "dns": extract(r'DNS\s*=\s*(.+)', config_text),
            "mtu": extract(r'MTU\s*=\s*(\d+)', config_text),
            "public_key": extract(r'PublicKey\s*=\s*(.+)', config_text),
            "preshared_key": extract(r'PresharedKey\s*=\s*(.+)', config_text),
            "endpoint": extract(r'Endpoint\s*=\s*(.+)', config_text),
            "allowed_ips": extract(r'AllowedIPs\s*=\s*(.+)', config_text),
            "persistent_keepalive": extract(r'PersistentKeepalive\s*=\s*(\d+)', config_text),
        }

    # ── AllowedIPs calculation ───────────────────────────────────

    @staticmethod
    def _calculate_allowed_ips(original_ips, server_ip, server_ipv6=None):
        ips_list = [ip.strip() for ip in original_ips.split(',')]
        has_default_route = any(ip == "0.0.0.0/0" for ip in ips_list)

        if not has_default_route:
            return ips_list

        server_ip_obj = ipaddress.IPv4Address(server_ip)
        server_int = int(server_ip_obj)

        def split_cidr(network, exclude_ip, max_prefix):
            if exclude_ip < int(network.network_address) or exclude_ip > int(network.broadcast_address):
                return [str(network)]
            if network.prefixlen >= max_prefix:
                return []
            networks = list(network.subnets(prefixlen_diff=1))
            result = []
            for subnet in networks:
                result.extend(split_cidr(subnet, exclude_ip, max_prefix))
            return result

        all_ipv4 = ipaddress.IPv4Network("0.0.0.0/0")
        allowed_cidrs = split_cidr(all_ipv4, server_int, 32)

        if server_ipv6:
            server_ipv6_obj = ipaddress.IPv6Address(server_ipv6)
            server_ipv6_int = int(server_ipv6_obj)
            all_ipv6 = ipaddress.IPv6Network("::/0")
            allowed_cidrs.extend(split_cidr(all_ipv6, server_ipv6_int, 128))

        for ip in ips_list:
            if ip != "0.0.0.0/0" and ip not in allowed_cidrs:
                allowed_cidrs.append(ip)

        return allowed_cidrs
