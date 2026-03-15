"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Ghost Models Unit Test

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.modules.ghost.models.ghost_models import (
    EnableGhostResult,
    DisableGhostResult,
    GhostServiceInfo,
    GhostStatusResult
)


class TestEnableGhostResult:

    def test_init(self):
        result = EnableGhostResult(
            status="success",
            server_ip="192.168.1.100",
            domain="ghost.example.com",
            secret="secret-key-123",
            protocol="https",
            port=443,
            activated_at="2025-01-09T10:00:00Z",
            connection_command="wstunnel client --secret secret-key-123"
        )
        assert result.status == "success"
        assert result.server_ip == "192.168.1.100"
        assert result.domain == "ghost.example.com"
        assert result.secret == "secret-key-123"
        assert result.protocol == "https"
        assert result.port == 443
        assert result.activated_at == "2025-01-09T10:00:00Z"
        assert result.connection_command == "wstunnel client --secret secret-key-123"

    def test_to_dict(self):
        result = EnableGhostResult(
            status="success",
            server_ip="10.0.0.1",
            domain="tunnel.corp.net",
            secret="abc-def-ghi",
            protocol="wss",
            port=8443,
            activated_at="2025-01-09T12:30:00Z",
            connection_command="wstunnel client -s abc-def-ghi"
        )
        expected = {
            "status": "success",
            "server_ip": "10.0.0.1",
            "domain": "tunnel.corp.net",
            "secret": "abc-def-ghi",
            "protocol": "wss",
            "port": 8443,
            "activated_at": "2025-01-09T12:30:00Z",
            "connection_command": "wstunnel client -s abc-def-ghi"
        }
        assert result.to_dict() == expected

    def test_different_protocols(self):
        protocols = ["http", "https", "ws", "wss"]
        for protocol in protocols:
            result = EnableGhostResult(
                status="active",
                server_ip="172.16.0.1",
                domain=f"{protocol}.tunnel.io",
                secret="test-secret",
                protocol=protocol,
                port=80 if protocol in ["http", "ws"] else 443,
                activated_at="2025-01-09T15:00:00Z",
                connection_command=f"connect --protocol {protocol}"
            )
            assert result.protocol == protocol
            data = result.to_dict()
            assert data["protocol"] == protocol


class TestDisableGhostResult:

    def test_init_minimal(self):
        result = DisableGhostResult(
            status="disabled",
            message="Ghost mode disabled successfully"
        )
        assert result.status == "disabled"
        assert result.message == "Ghost mode disabled successfully"
        assert result.restored is None

    def test_init_with_restored(self):
        result = DisableGhostResult(
            status="disabled",
            message="Configuration restored",
            restored=True
        )
        assert result.status == "disabled"
        assert result.message == "Configuration restored"
        assert result.restored is True

    def test_to_dict_minimal(self):
        result = DisableGhostResult(
            status="success",
            message="Disabled"
        )
        expected = {
            "status": "success",
            "message": "Disabled"
        }
        assert result.to_dict() == expected

    def test_to_dict_with_restored(self):
        result = DisableGhostResult(
            status="complete",
            message="Service stopped and configuration restored",
            restored=True
        )
        expected = {
            "status": "complete",
            "message": "Service stopped and configuration restored",
            "restored": True
        }
        assert result.to_dict() == expected

    def test_restored_false(self):
        result = DisableGhostResult(
            status="partial",
            message="Service stopped but configuration not restored",
            restored=False
        )
        data = result.to_dict()
        assert data["restored"] is False
        assert "restored" in data


class TestGhostServiceInfo:

    def test_init(self):
        info = GhostServiceInfo(wstunnel="running")
        assert info.wstunnel == "running"

    def test_to_dict(self):
        info = GhostServiceInfo(wstunnel="active")
        assert info.to_dict() == {"wstunnel": "active"}

    def test_different_statuses(self):
        statuses = ["running", "stopped", "inactive", "failed", "active", "starting"]
        for status in statuses:
            info = GhostServiceInfo(wstunnel=status)
            assert info.wstunnel == status
            assert info.to_dict() == {"wstunnel": status}


class TestGhostStatusResult:

    def test_init_minimal(self):
        result = GhostStatusResult(
            status="disabled",
            enabled=False
        )
        assert result.status == "disabled"
        assert result.enabled is False
        assert result.message is None
        assert result.server_ip is None

    def test_init_full(self):
        services = GhostServiceInfo(wstunnel="running")
        result = GhostStatusResult(
            status="active",
            enabled=True,
            message="Ghost mode is active",
            server_ip="192.168.100.1",
            domain="secure.tunnel.com",
            secret="xyz-123-abc",
            protocol="wss",
            port=443,
            services=services,
            activated_at="2025-01-09T08:00:00Z",
            connection_command="wstunnel client connect",
            client_export_info="export WSTUNNEL_HOST=secure.tunnel.com"
        )
        assert result.status == "active"
        assert result.enabled is True
        assert result.message == "Ghost mode is active"
        assert result.server_ip == "192.168.100.1"
        assert result.domain == "secure.tunnel.com"
        assert result.secret == "xyz-123-abc"
        assert result.protocol == "wss"
        assert result.port == 443
        assert result.services == services
        assert result.activated_at == "2025-01-09T08:00:00Z"
        assert result.connection_command == "wstunnel client connect"
        assert result.client_export_info == "export WSTUNNEL_HOST=secure.tunnel.com"

    def test_to_dict_minimal(self):
        result = GhostStatusResult(
            status="inactive",
            enabled=False
        )
        expected = {
            "status": "inactive",
            "enabled": False
        }
        assert result.to_dict() == expected

    def test_to_dict_with_message(self):
        result = GhostStatusResult(
            status="error",
            enabled=False,
            message="Failed to connect"
        )
        expected = {
            "status": "error",
            "enabled": False,
            "message": "Failed to connect"
        }
        assert result.to_dict() == expected

    def test_to_dict_full(self):
        services = GhostServiceInfo(wstunnel="active")
        result = GhostStatusResult(
            status="connected",
            enabled=True,
            message="Fully operational",
            server_ip="10.10.10.10",
            domain="ghost.internal",
            secret="secret-token",
            protocol="https",
            port=8080,
            services=services,
            activated_at="2025-01-09T14:20:00Z",
            connection_command="connect --token secret-token",
            client_export_info="export GHOST_ENABLED=true"
        )
        expected = {
            "status": "connected",
            "enabled": True,
            "message": "Fully operational",
            "server_ip": "10.10.10.10",
            "domain": "ghost.internal",
            "secret": "secret-token",
            "protocol": "https",
            "port": 8080,
            "services": {"wstunnel": "active"},
            "activated_at": "2025-01-09T14:20:00Z",
            "connection_command": "connect --token secret-token",
            "client_export_info": "export GHOST_ENABLED=true"
        }
        assert result.to_dict() == expected

    def test_partial_fields(self):
        result = GhostStatusResult(
            status="partial",
            enabled=True,
            server_ip="172.20.0.1",
            protocol="ws",
            port=3000
        )
        data = result.to_dict()
        assert data["status"] == "partial"
        assert data["enabled"] is True
        assert data["server_ip"] == "172.20.0.1"
        assert data["protocol"] == "ws"
        assert data["port"] == 3000
        assert "message" not in data
        assert "domain" not in data
        assert "secret" not in data
        assert "services" not in data

    def test_services_integration(self):
        services = GhostServiceInfo(wstunnel="stopped")
        result = GhostStatusResult(
            status="maintenance",
            enabled=False,
            services=services,
            message="Under maintenance"
        )
        data = result.to_dict()
        assert "services" in data
        assert data["services"] == {"wstunnel": "stopped"}

    def test_port_variations(self):
        ports = [80, 443, 8080, 8443, 3000, 9090]
        for port in ports:
            result = GhostStatusResult(
                status="test",
                enabled=True,
                port=port
            )
            data = result.to_dict()
            assert data["port"] == port
