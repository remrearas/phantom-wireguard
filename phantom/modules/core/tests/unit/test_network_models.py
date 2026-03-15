"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Core Network Models Unit Test File

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.modules.core.models.network_models import (
    TransferStats,
    PeerInfo,
    NetworkInfo,
    SubnetChangeValidation,
    NetworkAnalysis,
    NetworkValidationResult,
    NetworkMigrationResult,
    MainInterfaceInfo
)


class TestTransferStats:

    def test_init(self):
        stats = TransferStats(received="1.5 GiB", sent="2.3 GiB")
        assert stats.received == "1.5 GiB"
        assert stats.sent == "2.3 GiB"

    def test_to_dict(self):
        stats = TransferStats(received="500 MiB", sent="1.2 GiB")
        assert stats.to_dict() == {
            "received": "500 MiB",
            "sent": "1.2 GiB"
        }

    def test_various_sizes(self):
        test_cases = [
            ("0 B", "0 B"),
            ("1.5 KiB", "2.5 KiB"),
            ("100 MiB", "200 MiB"),
            ("5.5 GiB", "10.2 GiB"),
            ("1.0 TiB", "2.0 TiB")
        ]
        for received, sent in test_cases:
            stats = TransferStats(received=received, sent=sent)
            assert stats.received == received
            assert stats.sent == sent


class TestPeerInfo:

    def test_init_minimal(self):
        peer = PeerInfo(
            public_key="peer_public_key_123",
            allowed_ips="10.0.0.2/32"
        )
        assert peer.public_key == "peer_public_key_123"
        assert peer.allowed_ips == "10.0.0.2/32"
        assert peer.latest_handshake is None
        assert peer.endpoint is None
        assert peer.transfer is None

    def test_init_complete(self):
        transfer = TransferStats(received="1 GiB", sent="2 GiB")
        peer = PeerInfo(
            public_key="peer_public_key_456",
            allowed_ips="10.0.0.3/32",
            latest_handshake="2 minutes ago",
            endpoint="192.168.1.100:51820",
            transfer=transfer
        )
        assert peer.public_key == "peer_public_key_456"
        assert peer.allowed_ips == "10.0.0.3/32"
        assert peer.latest_handshake == "2 minutes ago"
        assert peer.endpoint == "192.168.1.100:51820"
        assert peer.transfer == transfer

    def test_to_dict_minimal(self):
        peer = PeerInfo(
            public_key="peer_key",
            allowed_ips="10.0.0.4/32"
        )
        assert peer.to_dict() == {
            "public_key": "peer_key",
            "allowed_ips": "10.0.0.4/32"
        }

    def test_to_dict_complete(self):
        transfer = TransferStats(received="100 MiB", sent="200 MiB")
        peer = PeerInfo(
            public_key="complete_peer_key",
            allowed_ips="10.0.0.5/32",
            latest_handshake="1 minute ago",
            endpoint="10.20.30.40:51820",
            transfer=transfer
        )
        assert peer.to_dict() == {
            "public_key": "complete_peer_key",
            "allowed_ips": "10.0.0.5/32",
            "latest_handshake": "1 minute ago",
            "endpoint": "10.20.30.40:51820",
            "transfer": {
                "received": "100 MiB",
                "sent": "200 MiB"
            }
        }

    def test_from_dict_minimal(self):
        data = {
            "public_key": "from_dict_key",
            "allowed_ips": "10.0.0.6/32"
        }
        peer = PeerInfo.from_dict(data)
        assert peer.public_key == "from_dict_key"
        assert peer.allowed_ips == "10.0.0.6/32"
        assert peer.latest_handshake is None
        assert peer.endpoint is None
        assert peer.transfer is None

    def test_from_dict_complete(self):
        data = {
            "public_key": "complete_key",
            "allowed_ips": "10.0.0.7/32",
            "latest_handshake": "30 seconds ago",
            "endpoint": "1.2.3.4:51820",
            "transfer": {
                "received": "5 GiB",
                "sent": "10 GiB"
            }
        }
        peer = PeerInfo.from_dict(data)
        assert peer.public_key == "complete_key"
        assert peer.allowed_ips == "10.0.0.7/32"
        assert peer.latest_handshake == "30 seconds ago"
        assert peer.endpoint == "1.2.3.4:51820"
        assert peer.transfer is not None
        assert peer.transfer.received == "5 GiB"
        assert peer.transfer.sent == "10 GiB"

    def test_round_trip_conversion(self):
        transfer = TransferStats(received="3 GiB", sent="4 GiB")
        original = PeerInfo(
            public_key="round_trip_key",
            allowed_ips="10.0.0.8/32",
            latest_handshake="5 minutes ago",
            endpoint="192.168.1.1:51820",
            transfer=transfer
        )
        dict_form = original.to_dict()
        restored = PeerInfo.from_dict(dict_form)

        assert restored.public_key == original.public_key
        assert restored.allowed_ips == original.allowed_ips
        assert restored.latest_handshake == original.latest_handshake
        assert restored.endpoint == original.endpoint
        assert restored.transfer.received == original.transfer.received
        assert restored.transfer.sent == original.transfer.sent


class TestNetworkInfo:

    def test_init(self):
        network = NetworkInfo(
            subnet="10.0.0.0/24",
            server_ip="10.0.0.1",
            total_ips=254,
            used_ips=50,
            available_ips=204
        )
        assert network.subnet == "10.0.0.0/24"
        assert network.server_ip == "10.0.0.1"
        assert network.total_ips == 254
        assert network.used_ips == 50
        assert network.available_ips == 204

    def test_to_dict(self):
        network = NetworkInfo(
            subnet="192.168.1.0/24",
            server_ip="192.168.1.1",
            total_ips=254,
            used_ips=10,
            available_ips=244
        )
        assert network.to_dict() == {
            "subnet": "192.168.1.0/24",
            "server_ip": "192.168.1.1",
            "total_ips": 254,
            "used_ips": 10,
            "available_ips": 244
        }

    def test_different_subnets(self):
        test_cases = [
            ("10.0.0.0/24", "10.0.0.1", 254, 100, 154),
            ("172.16.0.0/16", "172.16.0.1", 65534, 1000, 64534),
            ("192.168.1.0/28", "192.168.1.1", 14, 5, 9),
            ("10.10.0.0/22", "10.10.0.1", 1022, 200, 822)
        ]
        for subnet, server_ip, total, used, available in test_cases:
            network = NetworkInfo(
                subnet=subnet,
                server_ip=server_ip,
                total_ips=total,
                used_ips=used,
                available_ips=available
            )
            assert network.total_ips == total
            assert network.used_ips == used
            assert network.available_ips == available


class TestSubnetChangeValidation:

    def test_init_minimal(self):
        validation = SubnetChangeValidation(
            valid=True,
            current_subnet="10.0.0.0/24",
            new_subnet="192.168.1.0/24"
        )
        assert validation.valid is True
        assert validation.current_subnet == "10.0.0.0/24"
        assert validation.new_subnet == "192.168.1.0/24"
        assert validation.ip_mapping == {}
        assert validation.errors == []
        assert validation.warnings == []

    def test_init_with_mapping(self):
        ip_mapping = {
            "10.0.0.2": "192.168.1.2",
            "10.0.0.3": "192.168.1.3",
            "10.0.0.4": "192.168.1.4"
        }
        validation = SubnetChangeValidation(
            valid=True,
            current_subnet="10.0.0.0/24",
            new_subnet="192.168.1.0/24",
            ip_mapping=ip_mapping
        )
        assert validation.ip_mapping == ip_mapping

    def test_init_with_errors_and_warnings(self):
        validation = SubnetChangeValidation(
            valid=False,
            current_subnet="10.0.0.0/24",
            new_subnet="10.0.0.0/24",
            errors=["Same subnet", "No change needed"],
            warnings=["Consider a different subnet"]
        )
        assert validation.valid is False
        assert len(validation.errors) == 2
        assert len(validation.warnings) == 1

    def test_to_dict_minimal(self):
        validation = SubnetChangeValidation(
            valid=True,
            current_subnet="10.0.0.0/24",
            new_subnet="172.16.0.0/24"
        )
        assert validation.to_dict() == {
            "valid": True,
            "current_subnet": "10.0.0.0/24",
            "new_subnet": "172.16.0.0/24",
            "ip_mapping": {}
        }

    def test_to_dict_complete(self):
        validation = SubnetChangeValidation(
            valid=False,
            current_subnet="10.0.0.0/24",
            new_subnet="192.168.1.0/24",
            ip_mapping={"10.0.0.2": "192.168.1.2"},
            errors=["Network conflict"],
            warnings=["Check routing table"]
        )
        assert validation.to_dict() == {
            "valid": False,
            "current_subnet": "10.0.0.0/24",
            "new_subnet": "192.168.1.0/24",
            "ip_mapping": {"10.0.0.2": "192.168.1.2"},
            "errors": ["Network conflict"],
            "warnings": ["Check routing table"]
        }


class TestNetworkAnalysis:

    def test_init_and_to_dict(self):
        analysis = NetworkAnalysis(
            current_subnet="10.0.0.0/24",
            subnet_size=254,
            clients={"total": 50, "active": 30},
            server_ip="10.0.0.1",
            can_change=True,
            blockers={"active_connections": False, "service_running": False},
            main_interface={"name": "eth0", "ip": "192.168.1.100"},
            warnings=["Backup recommended", "High client count"]
        )

        assert analysis.current_subnet == "10.0.0.0/24"
        assert analysis.subnet_size == 254
        assert analysis.clients["total"] == 50
        assert analysis.can_change is True
        assert len(analysis.warnings) == 2

        dict_result = analysis.to_dict()
        assert dict_result["current_subnet"] == "10.0.0.0/24"
        assert dict_result["subnet_size"] == 254
        assert dict_result["clients"] == {"total": 50, "active": 30}
        assert dict_result["server_ip"] == "10.0.0.1"
        assert dict_result["can_change"] is True
        assert dict_result["blockers"] == {"active_connections": False, "service_running": False}
        assert dict_result["main_interface"] == {"name": "eth0", "ip": "192.168.1.100"}
        assert dict_result["warnings"] == ["Backup recommended", "High client count"]


class TestNetworkValidationResult:

    def test_init_minimal(self):
        result = NetworkValidationResult(
            valid=True,
            new_subnet="192.168.1.0/24",
            current_subnet="10.0.0.0/24",
            checks={"format": True, "overlap": False},
            warnings=[],
            errors=[]
        )
        assert result.valid is True
        assert result.new_subnet == "192.168.1.0/24"
        assert result.current_subnet == "10.0.0.0/24"
        assert result.checks["format"] is True
        assert result.ip_mapping_preview is None

    def test_init_with_mapping_preview(self):
        mapping = {
            "10.0.0.2": "192.168.1.2",
            "10.0.0.3": "192.168.1.3"
        }
        result = NetworkValidationResult(
            valid=True,
            new_subnet="192.168.1.0/24",
            current_subnet="10.0.0.0/24",
            checks={"all": True},
            warnings=["Check DNS settings"],
            errors=[],
            ip_mapping_preview=mapping
        )
        assert result.ip_mapping_preview == mapping
        assert len(result.warnings) == 1

    def test_to_dict_minimal(self):
        result = NetworkValidationResult(
            valid=False,
            new_subnet="10.0.0.0/24",
            current_subnet="10.0.0.0/24",
            checks={"unique": False},
            warnings=[],
            errors=["Same subnet"]
        )
        assert result.to_dict() == {
            "valid": False,
            "new_subnet": "10.0.0.0/24",
            "current_subnet": "10.0.0.0/24",
            "checks": {"unique": False},
            "warnings": [],
            "errors": ["Same subnet"]
        }

    def test_to_dict_with_mapping(self):
        result = NetworkValidationResult(
            valid=True,
            new_subnet="172.16.0.0/24",
            current_subnet="10.0.0.0/24",
            checks={"all": True},
            warnings=[],
            errors=[],
            ip_mapping_preview={"10.0.0.2": "172.16.0.2"}
        )
        dict_result = result.to_dict()
        assert "ip_mapping_preview" in dict_result
        assert dict_result["ip_mapping_preview"] == {"10.0.0.2": "172.16.0.2"}


class TestNetworkMigrationResult:

    def test_init(self):
        migration = NetworkMigrationResult(
            success=True,
            old_subnet="10.0.0.0/24",
            new_subnet="192.168.1.0/24",
            clients_updated=25,
            backup_id="backup_20250101_120000",
            ip_mapping={
                "10.0.0.2": "192.168.1.2",
                "10.0.0.3": "192.168.1.3"
            }
        )
        assert migration.success is True
        assert migration.old_subnet == "10.0.0.0/24"
        assert migration.new_subnet == "192.168.1.0/24"
        assert migration.clients_updated == 25
        assert migration.backup_id == "backup_20250101_120000"
        assert len(migration.ip_mapping) == 2

    def test_to_dict(self):
        migration = NetworkMigrationResult(
            success=False,
            old_subnet="172.16.0.0/16",
            new_subnet="10.10.0.0/16",
            clients_updated=0,
            backup_id="backup_failed",
            ip_mapping={}
        )
        assert migration.to_dict() == {
            "success": False,
            "old_subnet": "172.16.0.0/16",
            "new_subnet": "10.10.0.0/16",
            "clients_updated": 0,
            "backup_id": "backup_failed",
            "ip_mapping": {}
        }

    def test_large_migration(self):
        ip_mapping = {f"10.0.0.{i}": f"192.168.1.{i}" for i in range(2, 102)}
        migration = NetworkMigrationResult(
            success=True,
            old_subnet="10.0.0.0/24",
            new_subnet="192.168.1.0/24",
            clients_updated=100,
            backup_id="backup_large_migration",
            ip_mapping=ip_mapping
        )
        assert migration.clients_updated == 100
        assert len(migration.ip_mapping) == 100


class TestMainInterfaceInfo:

    def test_init(self):
        interface = MainInterfaceInfo(
            interface="eth0",
            ip="192.168.1.100",
            network="192.168.1.0/24"
        )
        assert interface.interface == "eth0"
        assert interface.ip == "192.168.1.100"
        assert interface.network == "192.168.1.0/24"

    def test_to_dict(self):
        interface = MainInterfaceInfo(
            interface="wlan0",
            ip="10.0.0.50",
            network="10.0.0.0/24"
        )
        assert interface.to_dict() == {
            "interface": "wlan0",
            "ip": "10.0.0.50",
            "network": "10.0.0.0/24"
        }

    def test_different_interfaces(self):
        test_cases = [
            ("eth0", "192.168.1.1", "192.168.1.0/24"),
            ("wlan0", "10.0.0.1", "10.0.0.0/24"),
            ("docker0", "172.17.0.1", "172.17.0.0/16"),
            ("lo", "127.0.0.1", "127.0.0.0/8"),
            ("enp0s3", "192.168.56.101", "192.168.56.0/24")
        ]
        for iface, ip, network in test_cases:
            interface = MainInterfaceInfo(
                interface=iface,
                ip=ip,
                network=network
            )
            assert interface.interface == iface
            assert interface.ip == ip
            assert interface.network == network
