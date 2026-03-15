"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Core Storage Models Unit Test File

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.modules.core.models.storage_models import (
    ClientDatastoreInfo,
    ActiveConnectionsMap
)


class TestClientDatastoreInfo:

    def test_init_empty(self):
        datastore = ClientDatastoreInfo(
            clients={},
            ip_assignments={},
            metadata={}
        )
        assert datastore.clients == {}
        assert datastore.ip_assignments == {}
        assert datastore.metadata == {}

    def test_init_with_data(self):
        clients = {
            "client1": {
                "name": "client1",
                "public_key": "pub_key_1",
                "enabled": True
            },
            "client2": {
                "name": "client2",
                "public_key": "pub_key_2",
                "enabled": False
            }
        }
        ip_assignments = {
            "10.0.0.2": "client1",
            "10.0.0.3": "client2"
        }
        metadata = {
            "version": "1.0",
            "last_updated": "2025-01-01T12:00:00",
            "total_clients": 2
        }

        datastore = ClientDatastoreInfo(
            clients=clients,
            ip_assignments=ip_assignments,
            metadata=metadata
        )

        assert len(datastore.clients) == 2
        assert datastore.clients["client1"]["enabled"] is True
        assert datastore.ip_assignments["10.0.0.2"] == "client1"
        assert datastore.metadata["version"] == "1.0"

    def test_to_dict_empty(self):
        datastore = ClientDatastoreInfo(
            clients={},
            ip_assignments={},
            metadata={}
        )
        assert datastore.to_dict() == {
            "clients": {},
            "ip_assignments": {},
            "metadata": {}
        }

    def test_to_dict_with_data(self):
        clients = {
            "test_client": {
                "name": "test_client",
                "ip": "10.0.0.5",
                "created": "2025-01-01T10:00:00"
            }
        }
        ip_assignments = {
            "10.0.0.5": "test_client"
        }
        metadata = {
            "created_at": "2025-01-01T09:00:00",
            "updated_at": "2025-01-01T10:00:00"
        }

        datastore = ClientDatastoreInfo(
            clients=clients,
            ip_assignments=ip_assignments,
            metadata=metadata
        )

        result = datastore.to_dict()
        assert result == {
            "clients": clients,
            "ip_assignments": ip_assignments,
            "metadata": metadata
        }

    def test_complex_clients_structure(self):
        clients = {
            "corp_user_1": {
                "name": "corp_user_1",
                "ip": "10.0.0.10",
                "public_key": "complex_pub_key_1",
                "private_key": "complex_priv_key_1",
                "preshared_key": "complex_pre_key_1",
                "enabled": True,
                "created": "2025-01-01T08:00:00",
                "last_seen": "2025-01-01T12:00:00",
                "transfer": {
                    "rx": 1048576,
                    "tx": 2097152
                }
            },
            "corp_user_2": {
                "name": "corp_user_2",
                "ip": "10.0.0.11",
                "public_key": "complex_pub_key_2",
                "enabled": False,
                "disabled_reason": "Temporary suspension"
            }
        }

        datastore = ClientDatastoreInfo(
            clients=clients,
            ip_assignments={
                "10.0.0.10": "corp_user_1",
                "10.0.0.11": "corp_user_2"
            },
            metadata={
                "encryption": "AES-256",
                "compression": True
            }
        )

        assert datastore.clients["corp_user_1"]["transfer"]["rx"] == 1048576
        assert datastore.clients["corp_user_2"]["disabled_reason"] == "Temporary suspension"

    def test_metadata_variations(self):
        test_cases = [
            {"version": "1.0", "format": "json"},
            {"timestamp": 1704067200, "timezone": "UTC"},
            {"checksum": "sha256:abc123", "validated": True},
            {"stats": {"total": 100, "active": 50, "inactive": 50}}
        ]

        for metadata in test_cases:
            datastore = ClientDatastoreInfo(
                clients={},
                ip_assignments={},
                metadata=metadata
            )
            assert datastore.metadata == metadata


class TestActiveConnectionsMap:

    def test_init_empty(self):
        connections_map = ActiveConnectionsMap(connections={})
        assert connections_map.connections == {}

    def test_init_with_connections(self):
        connections = {
            "client1": {
                "endpoint": "192.168.1.100:51820",
                "latest_handshake": "2 minutes ago",
                "transfer_rx": "100 MiB",
                "transfer_tx": "50 MiB"
            },
            "client2": {
                "endpoint": "10.20.30.40:51820",
                "latest_handshake": "1 minute ago",
                "transfer_rx": "200 MiB",
                "transfer_tx": "150 MiB"
            }
        }

        connections_map = ActiveConnectionsMap(connections=connections)
        assert len(connections_map.connections) == 2
        assert connections_map.connections["client1"]["endpoint"] == "192.168.1.100:51820"
        assert connections_map.connections["client2"]["transfer_rx"] == "200 MiB"

    def test_to_dict(self):
        connections = {
            "test_client": {
                "endpoint": "1.2.3.4:51820",
                "connected": True,
                "duration": "1 hour"
            }
        }

        connections_map = ActiveConnectionsMap(connections=connections)
        result = connections_map.to_dict()

        # to_dict returns connections directly
        assert result == connections
        assert result["test_client"]["endpoint"] == "1.2.3.4:51820"

    def test_complex_connection_data(self):
        connections = {
            "power_user": {
                "endpoint": "203.0.113.1:51820",
                "latest_handshake": "30 seconds ago",
                "allowed_ips": ["10.0.0.2/32", "192.168.1.0/24"],
                "public_key": "user_public_key_123",
                "persistent_keepalive": 25,
                "transfer": {
                    "rx_bytes": 1073741824,  # 1 GiB
                    "tx_bytes": 536870912,  # 512 MiB
                    "rx_packets": 1000000,
                    "tx_packets": 500000
                },
                "connection_time": "2025-01-01T10:00:00",
                "last_activity": "2025-01-01T12:30:00"
            },
            "mobile_user": {
                "endpoint": "Dynamic",
                "latest_handshake": "5 minutes ago",
                "roaming": True,
                "endpoints_history": [
                    "198.51.100.1:51820",
                    "198.51.100.2:51820"
                ]
            }
        }

        connections_map = ActiveConnectionsMap(connections=connections)
        assert connections_map.connections["power_user"]["transfer"]["rx_bytes"] == 1073741824
        assert connections_map.connections["mobile_user"]["roaming"] is True

    def test_empty_vs_none_values(self):
        connections = {
            "client_empty": {},
            "client_partial": {
                "endpoint": None,
                "handshake": "",
                "active": False
            }
        }

        connections_map = ActiveConnectionsMap(connections=connections)
        assert connections_map.connections["client_empty"] == {}
        assert connections_map.connections["client_partial"]["endpoint"] is None
        assert connections_map.connections["client_partial"]["handshake"] == ""
        assert connections_map.connections["client_partial"]["active"] is False

    def test_numeric_client_ids(self):
        connections = {
            "1": {"endpoint": "10.0.0.1:51820", "id": 1},
            "2": {"endpoint": "10.0.0.2:51820", "id": 2},
            "100": {"endpoint": "10.0.0.100:51820", "id": 100}
        }

        connections_map = ActiveConnectionsMap(connections=connections)
        assert connections_map.connections["1"]["id"] == 1
        assert connections_map.connections["100"]["endpoint"] == "10.0.0.100:51820"
