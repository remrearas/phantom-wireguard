"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Core Client Models Unit Test File

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from datetime import datetime
from phantom.modules.core.models.client_models import (
    WireGuardClient,
    ClientAddResult,
    ClientInfo,
    PaginationInfo,
    ClientListResult,
    ClientRemoveResult,
    ClientExportResult,
    LatestClientsResult
)


class TestWireGuardClient:

    def test_init_minimal(self):
        now = datetime.now()
        client = WireGuardClient(
            name="test_client",
            ip="10.0.0.2",
            private_key="private_key_123",
            public_key="public_key_123",
            preshared_key="preshared_key_123",
            created=now
        )
        assert client.name == "test_client"
        assert client.ip == "10.0.0.2"
        assert client.private_key == "private_key_123"
        assert client.public_key == "public_key_123"
        assert client.preshared_key == "preshared_key_123"
        assert client.created == now
        assert client.enabled is True  # Default value

    def test_init_with_enabled(self):
        now = datetime.now()
        client = WireGuardClient(
            name="test_client",
            ip="10.0.0.2",
            private_key="private_key_123",
            public_key="public_key_123",
            preshared_key="preshared_key_123",
            created=now,
            enabled=False
        )
        assert client.enabled is False

    def test_to_dict(self):
        now = datetime.now()
        client = WireGuardClient(
            name="test_client",
            ip="10.0.0.2",
            private_key="private_key_123",
            public_key="public_key_123",
            preshared_key="preshared_key_123",
            created=now,
            enabled=True
        )
        result = client.to_dict()
        assert result == {
            "name": "test_client",
            "ip": "10.0.0.2",
            "private_key": "private_key_123",
            "public_key": "public_key_123",
            "preshared_key": "preshared_key_123",
            "created": now.isoformat(),
            "enabled": True
        }

    def test_from_dict(self):
        now = datetime.now()
        data = {
            "name": "test_client",
            "ip": "10.0.0.3",
            "private_key": "private_key_456",
            "public_key": "public_key_456",
            "preshared_key": "preshared_key_456",
            "created": now.isoformat(),
            "enabled": False
        }
        client = WireGuardClient.from_dict(data)
        assert client.name == "test_client"
        assert client.ip == "10.0.0.3"
        assert client.private_key == "private_key_456"
        assert client.public_key == "public_key_456"
        assert client.preshared_key == "preshared_key_456"
        assert client.created.isoformat() == now.isoformat()
        assert client.enabled is False

    def test_from_dict_default_enabled(self):
        now = datetime.now()
        data = {
            "name": "test_client",
            "ip": "10.0.0.4",
            "private_key": "private_key_789",
            "public_key": "public_key_789",
            "preshared_key": "preshared_key_789",
            "created": now.isoformat()
            # enabled not provided, should default to True
        }
        client = WireGuardClient.from_dict(data)
        assert client.enabled is True

    def test_round_trip_conversion(self):
        now = datetime.now()
        original = WireGuardClient(
            name="round_trip",
            ip="10.0.0.5",
            private_key="priv_key",
            public_key="pub_key",
            preshared_key="pre_key",
            created=now,
            enabled=False
        )
        dict_form = original.to_dict()
        restored = WireGuardClient.from_dict(dict_form)

        assert restored.name == original.name
        assert restored.ip == original.ip
        assert restored.private_key == original.private_key
        assert restored.public_key == original.public_key
        assert restored.preshared_key == original.preshared_key
        assert restored.created.isoformat() == original.created.isoformat()
        assert restored.enabled == original.enabled


class TestClientAddResult:

    def test_init_and_to_dict(self):
        now = datetime.now()
        client = WireGuardClient(
            name="new_client",
            ip="10.0.0.10",
            private_key="priv",
            public_key="pub",
            preshared_key="pre",
            created=now
        )
        result = ClientAddResult(
            client=client,
            message="Client added successfully"
        )

        assert result.client == client
        assert result.message == "Client added successfully"

        dict_result = result.to_dict()
        assert dict_result == {
            "client": {
                "name": "new_client",
                "ip": "10.0.0.10",
                "public_key": "pub",
                "created": now.isoformat(),
                "enabled": True
            },
            "message": "Client added successfully"
        }

    def test_to_dict_with_disabled_client(self):
        now = datetime.now()
        client = WireGuardClient(
            name="disabled_client",
            ip="10.0.0.11",
            private_key="priv",
            public_key="pub",
            preshared_key="pre",
            created=now,
            enabled=False
        )
        result = ClientAddResult(
            client=client,
            message="Client added but disabled"
        )

        dict_result = result.to_dict()
        assert dict_result["client"]["enabled"] is False


class TestClientInfo:

    def test_init_minimal(self):
        info = ClientInfo(
            name="client1",
            ip="10.0.0.20",
            enabled=True,
            created="2025-01-01T12:00:00",
            connected=False
        )
        assert info.name == "client1"
        assert info.ip == "10.0.0.20"
        assert info.enabled is True
        assert info.created == "2025-01-01T12:00:00"
        assert info.connected is False
        assert info.connection is None

    def test_init_with_connection(self):
        connection_data = {
            "endpoint": "192.168.1.100:51820",
            "last_handshake": "2025-01-01T12:30:00",
            "bytes_sent": 1024,
            "bytes_received": 2048
        }
        info = ClientInfo(
            name="client2",
            ip="10.0.0.21",
            enabled=True,
            created="2025-01-01T12:00:00",
            connected=True,
            connection=connection_data
        )
        assert info.connected is True
        assert info.connection == connection_data

    def test_to_dict_minimal(self):
        info = ClientInfo(
            name="client3",
            ip="10.0.0.22",
            enabled=False,
            created="2025-01-01T12:00:00",
            connected=False
        )
        result = info.to_dict()
        assert result == {
            "name": "client3",
            "ip": "10.0.0.22",
            "enabled": False,
            "created": "2025-01-01T12:00:00",
            "connected": False
        }

    def test_to_dict_with_connection(self):
        connection_data = {
            "endpoint": "192.168.1.100:51820",
            "last_handshake": "2025-01-01T12:30:00"
        }
        info = ClientInfo(
            name="client4",
            ip="10.0.0.23",
            enabled=True,
            created="2025-01-01T12:00:00",
            connected=True,
            connection=connection_data
        )
        result = info.to_dict()
        assert result == {
            "name": "client4",
            "ip": "10.0.0.23",
            "enabled": True,
            "created": "2025-01-01T12:00:00",
            "connected": True,
            "connection": connection_data
        }


class TestPaginationInfo:

    def test_init(self):
        pagination = PaginationInfo(
            page=2,
            per_page=10,
            total_pages=5,
            has_next=True,
            has_prev=True,
            showing_from=11,
            showing_to=20
        )
        assert pagination.page == 2
        assert pagination.per_page == 10
        assert pagination.total_pages == 5
        assert pagination.has_next is True
        assert pagination.has_prev is True
        assert pagination.showing_from == 11
        assert pagination.showing_to == 20

    def test_to_dict(self):
        pagination = PaginationInfo(
            page=1,
            per_page=20,
            total_pages=3,
            has_next=True,
            has_prev=False,
            showing_from=1,
            showing_to=20
        )
        assert pagination.to_dict() == {
            "page": 1,
            "per_page": 20,
            "total_pages": 3,
            "has_next": True,
            "has_prev": False,
            "showing_from": 1,
            "showing_to": 20
        }

    def test_last_page(self):
        pagination = PaginationInfo(
            page=5,
            per_page=10,
            total_pages=5,
            has_next=False,
            has_prev=True,
            showing_from=41,
            showing_to=45
        )
        assert pagination.has_next is False
        assert pagination.has_prev is True


class TestClientListResult:

    def test_init_empty_list(self):
        pagination = PaginationInfo(
            page=1, per_page=10, total_pages=0,
            has_next=False, has_prev=False,
            showing_from=0, showing_to=0
        )
        result = ClientListResult(
            clients=[],
            total=0,
            pagination=pagination
        )
        assert result.clients == []
        assert result.total == 0

    def test_init_with_clients(self):
        clients = [
            ClientInfo(
                name=f"client{i}",
                ip=f"10.0.0.{i}",
                enabled=True,
                created="2025-01-01T12:00:00",
                connected=False
            )
            for i in range(3)
        ]
        pagination = PaginationInfo(
            page=1, per_page=10, total_pages=1,
            has_next=False, has_prev=False,
            showing_from=1, showing_to=3
        )
        result = ClientListResult(
            clients=clients,
            total=3,
            pagination=pagination
        )
        assert len(result.clients) == 3
        assert result.total == 3

    def test_to_dict(self):
        clients = [
            ClientInfo(
                name="client1",
                ip="10.0.0.1",
                enabled=True,
                created="2025-01-01T12:00:00",
                connected=False
            )
        ]
        pagination = PaginationInfo(
            page=1, per_page=10, total_pages=1,
            has_next=False, has_prev=False,
            showing_from=1, showing_to=1
        )
        result = ClientListResult(
            clients=clients,
            total=1,
            pagination=pagination
        )
        dict_result = result.to_dict()
        assert dict_result["total"] == 1
        assert len(dict_result["clients"]) == 1
        assert dict_result["clients"][0]["name"] == "client1"
        assert dict_result["pagination"]["page"] == 1


class TestClientRemoveResult:

    def test_init_success(self):
        result = ClientRemoveResult(
            removed=True,
            client_name="removed_client",
            client_ip="10.0.0.100"
        )
        assert result.removed is True
        assert result.client_name == "removed_client"
        assert result.client_ip == "10.0.0.100"

    def test_init_failure(self):
        result = ClientRemoveResult(
            removed=False,
            client_name="not_found",
            client_ip="10.0.0.200"
        )
        assert result.removed is False

    def test_to_dict(self):
        result = ClientRemoveResult(
            removed=True,
            client_name="test_client",
            client_ip="10.0.0.150"
        )
        assert result.to_dict() == {
            "removed": True,
            "client_name": "test_client",
            "client_ip": "10.0.0.150"
        }


class TestClientExportResult:

    def test_init_and_to_dict(self):
        now = datetime.now()
        client = WireGuardClient(
            name="export_client",
            ip="10.0.0.50",
            private_key="priv_export",
            public_key="pub_export",
            preshared_key="pre_export",
            created=now,
            enabled=True
        )
        config_content = """[Interface]
PrivateKey = priv_export
Address = 10.0.0.50/32

[Peer]
PublicKey = server_public_key
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0"""

        result = ClientExportResult(
            client=client,
            config=config_content
        )

        assert result.client == client
        assert result.config == config_content

        dict_result = result.to_dict()
        assert dict_result["config"] == config_content
        assert dict_result["client"]["name"] == "export_client"
        assert dict_result["client"]["ip"] == "10.0.0.50"
        assert dict_result["client"]["private_key"] == "priv_export"
        assert dict_result["client"]["public_key"] == "pub_export"
        assert dict_result["client"]["preshared_key"] == "pre_export"
        assert dict_result["client"]["created"] == now.isoformat()
        assert dict_result["client"]["enabled"] is True


class TestLatestClientsResult:

    def test_init_empty(self):
        result = LatestClientsResult(
            latest_clients=[],
            count=0,
            total_clients=10
        )
        assert result.latest_clients == []
        assert result.count == 0
        assert result.total_clients == 10

    def test_init_with_clients(self):
        clients = [
            ClientInfo(
                name=f"recent_client{i}",
                ip=f"10.0.1.{i}",
                enabled=True,
                created=f"2025-01-0{i + 1}T12:00:00",
                connected=False
            )
            for i in range(5)
        ]
        result = LatestClientsResult(
            latest_clients=clients,
            count=5,
            total_clients=100
        )
        assert len(result.latest_clients) == 5
        assert result.count == 5
        assert result.total_clients == 100

    def test_to_dict(self):
        clients = [
            ClientInfo(
                name="new_client1",
                ip="10.0.2.1",
                enabled=True,
                created="2025-01-10T12:00:00",
                connected=True,
                connection={"endpoint": "192.168.1.1:51820"}
            ),
            ClientInfo(
                name="new_client2",
                ip="10.0.2.2",
                enabled=False,
                created="2025-01-11T12:00:00",
                connected=False
            )
        ]
        result = LatestClientsResult(
            latest_clients=clients,
            count=2,
            total_clients=50
        )
        dict_result = result.to_dict()
        assert dict_result["count"] == 2
        assert dict_result["total_clients"] == 50
        assert len(dict_result["latest_clients"]) == 2
        assert dict_result["latest_clients"][0]["name"] == "new_client1"
        assert dict_result["latest_clients"][0]["connected"] is True
        assert dict_result["latest_clients"][0]["connection"] == {"endpoint": "192.168.1.1:51820"}
        assert dict_result["latest_clients"][1]["name"] == "new_client2"
        assert dict_result["latest_clients"][1]["enabled"] is False
