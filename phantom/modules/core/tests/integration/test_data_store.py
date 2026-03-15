"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

DataStore Component Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from datetime import datetime
import ipaddress

from phantom.modules.core.lib.data_store import DataStore
from phantom.modules.core.models import WireGuardClient
from phantom.api.exceptions import ClientNotFoundError


class TestDataStore:

    @pytest.fixture
    def environment(self, tmp_path):
        """Provide test environment with temporary database and data directory."""
        # Create temporary data directory for test isolation
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Define path for test database
        db_path = data_dir / "test.db"

        return {
            'data_dir': data_dir,
            'db_path': db_path
        }

    @pytest.mark.integration
    def test_client_lifecycle(self, environment):
        """Test complete lifecycle of a WireGuard client: create, find, and remove."""
        # Initialize DataStore with test environment
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Create a new WireGuard client with all required fields
        client = WireGuardClient(
            name="test-user",
            ip="10.8.0.2",
            private_key="privateKey123456789012345678901234567890123=",
            public_key="publicKey1234567890123456789012345678901234=",
            preshared_key="presharedKey12345678901234567890123456789012=",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client)

        # Verify client can be found by name
        found = store.find_client_by_name("test-user")
        assert found is not None
        assert found.name == "test-user"
        assert found.ip == "10.8.0.2"
        assert found.enabled is True

        # Verify client exists check returns True
        assert store.check_if_client_exists("test-user") is True

        # Remove the client from the store
        store.remove_existing_client("test-user")

        # Verify client is completely removed
        assert store.find_client_by_name("test-user") is None
        assert store.check_if_client_exists("test-user") is False

    @pytest.mark.integration
    def test_ip_allocation(self, environment):
        """Test IP address allocation and reuse after client removal."""
        # Use a small subnet (/29) to test IP exhaustion
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/29"  # Only 6 usable IPs
        )

        # Allocate first available IP (should be .2)
        ip1 = store.allocate_next_available_ip()
        assert ip1 == "10.8.0.2"

        # Store first client with allocated IP
        client1 = WireGuardClient(
            name="client1",
            ip=ip1,
            private_key="key1",
            public_key="pub1",
            preshared_key="pre1",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client1)

        # Allocate second IP (should be .3)
        ip2 = store.allocate_next_available_ip()
        assert ip2 == "10.8.0.3"

        # Store second client
        client2 = WireGuardClient(
            name="client2",
            ip=ip2,
            private_key="key2",
            public_key="pub2",
            preshared_key="pre2",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client2)

        # Remove first client to free its IP
        store.remove_existing_client("client1")

        # Verify freed IP is reused
        ip3 = store.allocate_next_available_ip()
        assert ip3 == "10.8.0.2"  # Reuses freed IP

        # Store third client with reused IP
        client3 = WireGuardClient(
            name="client3",
            ip=ip3,
            private_key="key3",
            public_key="pub3",
            preshared_key="pre3",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client3)

        # Fill remaining IPs in the subnet
        for i in range(4, 7):
            client = WireGuardClient(
                name=f"client{i}",
                ip=f"10.8.0.{i}",
                private_key=f"key{i}",
                public_key=f"pub{i}",
                preshared_key=f"pre{i}",
                created=datetime.now(),
                enabled=True
            )
            store.store_new_client(client)

        # Verify error when subnet is exhausted
        with pytest.raises(ValueError) as exc_info:
            store.allocate_next_available_ip()
        assert "No available IP addresses" in str(exc_info.value)

    @pytest.mark.integration
    def test_client_existence_checks(self, environment):
        """Test client existence checking and validation methods."""
        # Initialize DataStore
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Check non-existent client returns False
        assert store.check_if_client_exists("nobody") is False

        # Ensure method should not fail for non-existent client
        try:
            store.ensure_client_does_not_exist("nobody")
        except ValueError:
            pytest.fail("Should not raise ValueError for non-existent client")
        except Exception as e:
            pytest.fail(f"Unexpected exception for non-existent client: {type(e).__name__}: {e}")

        # Create and store a test client
        client = WireGuardClient(
            name="existing-user",
            ip="10.8.0.2",
            private_key="key",
            public_key="pub",
            preshared_key="pre",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client)

        # Verify client exists
        assert store.check_if_client_exists("existing-user") is True

        # Ensure method should fail for existing client
        with pytest.raises(ValueError) as exc_info:
            store.ensure_client_does_not_exist("existing-user")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.integration
    def test_bulk_operations(self, environment):
        """Test bulk client operations including retrieval and batch IP updates."""
        # Initialize DataStore
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Verify store starts empty
        clients = store.get_all_clients()
        assert len(clients) == 0

        # Create multiple clients
        client_names = ["alice", "bob", "charlie"]
        for i, name in enumerate(client_names, start=2):
            client = WireGuardClient(
                name=name,
                ip=f"10.8.0.{i}",
                private_key=f"key_{name}",
                public_key=f"pub_{name}",
                preshared_key=f"pre_{name}",
                created=datetime.now(),
                enabled=True
            )
            store.store_new_client(client)

        # Verify all clients are stored
        all_clients = store.get_all_clients()
        assert len(all_clients) == 3
        names = [c.name for c in all_clients]
        assert set(names) == set(client_names)

        # Perform bulk IP update
        ip_mapping = {
            "alice": "10.8.0.10",
            "bob": "10.8.0.11",
            "charlie": "10.8.0.12"
        }
        store.update_all_client_ips(ip_mapping)

        # Verify all IPs were updated correctly
        for name, new_ip in ip_mapping.items():
            client = store.find_client_by_name(name)
            assert client.ip == new_ip

    @pytest.mark.integration
    def test_network_migration(self, environment):
        """Test network subnet migration with automatic IP remapping."""
        # Initialize DataStore with original subnet
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Create test clients with original IPs
        clients = [
            ("client1", "10.8.0.2"),
            ("client2", "10.8.0.3"),
            ("client3", "10.8.0.10")
        ]

        for name, ip in clients:
            client = WireGuardClient(
                name=name,
                ip=ip,
                private_key=f"key_{name}",
                public_key=f"pub_{name}",
                preshared_key=f"pre_{name}",
                created=datetime.now(),
                enabled=True
            )
            store.store_new_client(client)

        # Define old and new network subnets
        old_network = ipaddress.IPv4Network("10.8.0.0/24")
        new_network = ipaddress.IPv4Network("10.7.0.0/24")

        # Create mapping from old to new subnet
        ip_mapping = store.create_ip_mapping_for_subnet_change(old_network, new_network)

        # Verify all clients get new IPs in correct subnet
        for name in ["client1", "client2", "client3"]:
            assert ip_mapping[name].startswith("10.7.0.")

        # Update network configuration
        store.update_network_configuration("10.7.0.0/24")

        # Apply the IP mapping to all clients
        store.update_all_client_ips(ip_mapping)

        # Verify all clients have been migrated
        for name in ["client1", "client2", "client3"]:
            client = store.find_client_by_name(name)
            assert client.ip.startswith("10.7.0.")

        # Test migration to subnet too small for existing clients
        too_small_network = ipaddress.IPv4Network("10.9.0.0/30")  # Only 2 usable IPs

        with pytest.raises(ValueError) as exc_info:
            store.create_ip_mapping_for_subnet_change(new_network, too_small_network)
        assert "New subnet too small" in str(exc_info.value)
        assert "3 clients" in str(exc_info.value)

    @pytest.mark.integration
    def test_update_client_ip_method(self, environment):
        """Test updating a client's IP address and verifying IP allocation consistency."""
        # Initialize DataStore
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Create and store a test client
        client = WireGuardClient(
            name="update-test",
            ip="10.8.0.5",
            private_key="key123",
            public_key="pub123",
            preshared_key="pre123",
            created=datetime.now(),
            enabled=True
        )
        store.store_new_client(client)

        # Verify initial IP allocation
        initial_allocations = store.get_ip_allocations()
        assert any(alloc['ip'] == "10.8.0.5" for alloc in initial_allocations)

        # Update client IP address
        store.update_client_ip("update-test", "10.8.0.20")

        # Verify client has new IP
        updated_client = store.find_client_by_name("update-test")
        assert updated_client.ip == "10.8.0.20"

        # Verify IP allocation table is updated correctly
        allocations = store.get_ip_allocations()
        assert not any(alloc['ip'] == "10.8.0.5" for alloc in allocations)  # Old IP removed
        assert any(alloc['ip'] == "10.8.0.20" and alloc['client_name'] == "update-test"
                   for alloc in allocations)  # New IP added

        # Test updating non-existent client
        with pytest.raises(ClientNotFoundError) as exc_info:
            store.update_client_ip("non-existent", "10.8.0.30")
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.integration
    def test_data_integrity(self, environment):
        """Test data integrity between client records and IP allocation table."""
        # Initialize DataStore
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Create test client data
        clients_data = [
            ("integrity1", "10.8.0.10"),
            ("integrity2", "10.8.0.11"),
            ("integrity3", "10.8.0.12")
        ]

        # Store multiple clients
        for name, ip in clients_data:
            client = WireGuardClient(
                name=name,
                ip=ip,
                private_key=f"key_{name}",
                public_key=f"pub_{name}",
                preshared_key=f"pre_{name}",
                created=datetime.now(),
                enabled=True
            )
            store.store_new_client(client)

        # Get all clients and IP allocations
        all_clients = store.get_all_clients()
        ip_allocations = store.get_ip_allocations()

        # Verify consistency between client table and IP allocation table
        for client in all_clients:
            assert any(alloc['ip'] == client.ip and alloc['client_name'] == client.name
                       for alloc in ip_allocations), f"Client {client.name} IP not in IP table"

        # Remove one client to test cleanup
        store.remove_existing_client("integrity2")

        # Verify client is removed from client table
        assert store.find_client_by_name("integrity2") is None

        # Verify IP allocation is cleaned up
        ip_allocations_after = store.get_ip_allocations()
        assert not any(alloc['client_name'] == "integrity2" for alloc in ip_allocations_after)
        assert not any(alloc['ip'] == "10.8.0.11" for alloc in ip_allocations_after)

        # Check for orphan IP records
        remaining_clients = store.get_all_clients()
        client_names = {c.name for c in remaining_clients}

        for alloc in ip_allocations_after:
            assert alloc['client_name'] in client_names, \
                f"Orphan IP record found: {alloc['ip']} for non-existent client {alloc['client_name']}"

        # Verify counts match between tables
        assert len(remaining_clients) == len(ip_allocations_after), \
            "Client count doesn't match IP allocation count"

    @pytest.mark.integration
    def test_error_cases(self, environment):
        """Test various error conditions and edge cases."""
        # Test invalid subnet format
        with pytest.raises(ValueError):
            DataStore(
                db_path=environment['db_path'],
                data_dir=environment['data_dir'],
                subnet="invalid-subnet"
            )

        # Initialize valid DataStore for error testing
        store = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )

        # Test removing non-existent client
        try:
            store.remove_existing_client("non-existent")
        except (ValueError, KeyError) as e:
            # Check error message contains expected text
            assert "not found" in str(e).lower() or "does not exist" in str(e).lower(), \
                f"Expected 'not found' or 'does not exist' in error, got: {e}"
        except Exception as e:
            pytest.fail(f"Unexpected exception type {type(e).__name__}: {e}")

        # Test finding non-existent client returns None
        result = store.find_client_by_name("ghost-user")
        assert result is None

        # Test updating IP for non-existent client
        try:
            store.update_client_ip_address("nobody", "10.8.0.99")
        except ClientNotFoundError as e:
            # Expected specific error type
            assert "not found" in str(e).lower(), f"Expected 'not found' in error message, got: {e}"
        except (ValueError, KeyError) as e:
            # Alternative error types also acceptable
            assert "not found" in str(e).lower() or "does not exist" in str(e).lower(), \
                f"Expected 'not found' or 'does not exist' in error, got: {e}"
        except Exception as e:
            pytest.fail(f"Unexpected exception type {type(e).__name__}: {e}")

        # Verify get_ip_allocations returns a list
        allocations = store.get_ip_allocations()
        assert isinstance(allocations, list)

        # Test operations after closing database
        store.close()

        try:
            store.get_all_clients()
        except (ValueError, RuntimeError, AttributeError):
            pass  # Expected errors after close
        except Exception as e:
            print(f"Note: Closed DB operation raised {type(e).__name__}: {e}")

        # Test close() method handles missing database attribute gracefully
        store_without_db = DataStore(
            db_path=environment['db_path'],
            data_dir=environment['data_dir'],
            subnet="10.8.0.0/24"
        )
        delattr(store_without_db, 'db')  # Remove db attribute

        try:
            store_without_db.close()
        except AttributeError:
            pytest.fail("close() should handle missing db attribute gracefully")
