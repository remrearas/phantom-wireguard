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

Unit tests for BridgeClient dataclass models.
ClientInfo, ClientList, DeviceInfo, ServerConfig, MultihopTunnel.
"""

from wireguard_go_bridge.client import (
    ClientInfo,
    ClientList,
    DeviceInfo,
    ServerConfig,
    MultihopTunnel,
)


class TestClientInfo:
    def test_defaults(self):
        c = ClientInfo()
        assert c.id == 0
        assert c.public_key == ""
        assert c.allowed_ip == ""
        assert c.allowed_ip_v6 == ""
        assert c.keepalive == 25
        assert c.enabled is True
        assert c.rx_bytes == 0
        assert c.tx_bytes == 0
        assert c.endpoint is None
        assert c.last_handshake is None

    def test_with_values(self):
        c = ClientInfo(
            id=1,
            public_key="abc123",
            private_key="def456",
            preshared_key="psk789",
            allowed_ip="10.8.0.2/32",
            allowed_ip_v6="fd00::2/128",
            keepalive=25,
            enabled=True,
            created_at=1700000000,
        )
        assert c.allowed_ip == "10.8.0.2/32"
        assert c.allowed_ip_v6 == "fd00::2/128"

    def test_disabled(self):
        c = ClientInfo(enabled=False)
        assert c.enabled is False


class TestClientList:
    def test_empty(self):
        cl = ClientList()
        assert cl.clients == []
        assert cl.total == 0
        assert cl.page == 1
        assert cl.limit == 50

    def test_with_clients(self):
        clients = [ClientInfo(id=1, public_key="a"), ClientInfo(id=2, public_key="b")]
        cl = ClientList(clients=clients, total=2, page=1, limit=50)
        assert len(cl.clients) == 2
        assert cl.total == 2


class TestDeviceInfo:
    def test_defaults(self):
        d = DeviceInfo()
        assert d.name == ""
        assert d.listen_port == 0
        assert d.peer_count == 0
        assert d.started_at is None

    def test_with_values(self):
        d = DeviceInfo(name="wg0", public_key="xyz", listen_port=51820, peer_count=5, started_at=1700000000)
        assert d.name == "wg0"
        assert d.started_at == 1700000000


class TestServerConfig:
    def test_defaults(self):
        s = ServerConfig()
        assert s.device_id == 1
        assert s.network == "10.8.0.0/24"
        assert s.network_v6 == ""
        assert s.dns_primary == "1.1.1.1"
        assert s.dns_secondary == "9.9.9.9"
        assert s.dns_v6 == ""
        assert s.mtu == 1420
        assert s.fwmark == 0
        assert s.endpoint == ""
        assert s.endpoint_v6 == ""

    def test_ipv6_configured(self):
        s = ServerConfig(network_v6="fd00::/64", dns_v6="2606:4700:4700::1111", endpoint_v6="[::1]:51820")
        assert s.network_v6 == "fd00::/64"
        assert s.dns_v6 == "2606:4700:4700::1111"

    def test_ipv4_only(self):
        s = ServerConfig()
        assert s.network_v6 == ""
        assert s.endpoint_v6 == ""


class TestMultihopTunnel:
    def test_defaults(self):
        m = MultihopTunnel()
        assert m.name == ""
        assert m.enabled is False
        assert m.status == "stopped"
        assert m.fwmark == 0
        assert m.routing_table == "phantom_multihop"
        assert m.routing_table_id == 100
        assert m.priority == 100
        assert m.remote_allowed_ips == "0.0.0.0/0"
        assert m.remote_keepalive == 25

    def test_with_config(self):
        m = MultihopTunnel(
            name="exit-us-1",
            interface_name="wg-hop0",
            remote_endpoint="203.0.113.5:51820",
            remote_public_key="abc",
            fwmark=51820,
            enabled=True,
        )
        assert m.name == "exit-us-1"
        assert m.enabled is True
        assert m.fwmark == 51820

    def test_error_state(self):
        m = MultihopTunnel(status="error", error_msg="tun create failed")
        assert m.status == "error"
        assert m.error_msg == "tun create failed"

    def test_running_state(self):
        m = MultihopTunnel(status="running", started_at=1700000000)
        assert m.status == "running"
        assert m.started_at == 1700000000
