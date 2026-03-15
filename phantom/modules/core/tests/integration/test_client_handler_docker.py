"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Client Handler Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import json
import pytest
from unittest.mock import patch
from pathlib import Path
from phantom.modules.core.tests.helpers.command_executor import CommandExecutor
from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor
from phantom.modules.core.models import (
    ClientAddResult,
    ClientRemoveResult,
    ClientListResult,
    ClientExportResult,
    LatestClientsResult
)
from phantom.api.exceptions import (
    ClientExistsError,
    ClientNotFoundError,
    InvalidClientNameError,
    IPAllocationError
)
from phantom.modules.core.lib import (
    DataStore,
    KeyGenerator,
    CommonTools,
    ClientHandler
)
from phantom.modules.core.lib.default_constants import (
    DEFAULT_WG_INTERFACE,
    DEFAULT_WG_NETWORK
)


class TestClientHandlerDocker:
    @pytest.fixture
    def docker_executor(self, shared_docker_container):
        """Docker executor fixture"""
        executor = DockerCommandExecutor(shared_docker_container)
        executor.container = shared_docker_container
        return executor

    @pytest.fixture
    def command_executor(self, docker_executor):
        """Command executor fixture"""
        return CommandExecutor(docker_executor)

    @pytest.fixture
    def environment(self, shared_docker_container):
        """Environment fixture"""
        host_phantom_dir = Path(shared_docker_container.host_phantom_dir)
        host_config_dir = Path(shared_docker_container.host_config_dir)

        data_dir = host_phantom_dir / "data"
        data_dir.mkdir(exist_ok=True)

        phantom_config_file = host_phantom_dir / "config" / "phantom.json"
        wg_config_file = host_config_dir / "wg_main.conf"

        return {
            "host_phantom_dir": host_phantom_dir,
            "host_config_dir": host_config_dir,
            "data_dir": data_dir,
            "phantom_config_file": phantom_config_file,
            "wg_config_file": wg_config_file
        }

    @pytest.fixture
    def phantom_config_content(self, environment):
        """Phantom Config Content fixture"""
        phantom_config_file = environment["phantom_config_file"]
        phantom_config_content = json.loads(phantom_config_file.read_text()) if phantom_config_file.exists() else {}
        return phantom_config_content

    @pytest.fixture
    def data_store(self, environment):
        """Data Store fixture"""
        db_path = environment["data_dir"] / 'data.db'
        data_store = DataStore(
            db_path=db_path,
            data_dir=environment["data_dir"],
            subnet=DEFAULT_WG_NETWORK
        )
        return data_store

    @pytest.fixture
    def key_generator(self, environment, command_executor):
        """Key Generator fixture"""
        key_generator = KeyGenerator(run_command=command_executor.run_command)
        return key_generator

    @pytest.fixture
    def common_tools(self, phantom_config_content, command_executor):
        """Common Tools fixture"""
        common_tools = CommonTools(
            config=phantom_config_content,
            run_command=command_executor.run_command
        )
        return common_tools

    @pytest.fixture
    def client_handler(self, data_store, key_generator, common_tools, phantom_config_content, command_executor,
                       environment):
        """Client Handler fixture"""
        client_handler = ClientHandler(
            data_store=data_store,
            key_generator=key_generator,
            common_tools=common_tools,
            config=phantom_config_content,
            run_command=command_executor.run_command,
            wg_interface=DEFAULT_WG_INTERFACE,
            wg_config_file=environment["wg_config_file"],
            install_dir=environment["host_phantom_dir"]
        )
        yield client_handler

    @pytest.mark.integration
    @pytest.mark.docker
    def test_add_new_client_success(self, environment, client_handler):
        """Test successful addition of a new WireGuard client."""
        # Add a new client
        result = client_handler.add_new_client("test_client")

        # Verify result object and client details
        assert isinstance(result, ClientAddResult)
        assert result.client.name == "test_client"
        assert result.client.ip == "10.8.0.2"  # First available IP in subnet
        assert len(result.client.public_key) == 44  # WireGuard public key length
        assert result.message == "Client added successfully"

        # Verify client is added to WireGuard configuration file
        assert environment["wg_config_file"].exists()
        config_content = environment["wg_config_file"].read_text()
        assert result.client.public_key in config_content
        assert "10.8.0.2/32" in config_content

    @pytest.mark.integration
    @pytest.mark.docker
    def test_add_new_client_already_exists(self, environment, client_handler):
        """Test error handling when attempting to add a duplicate client."""
        # First add a client successfully
        client_handler.add_new_client("existing_client")

        # Attempt to add the same client again, should raise ClientExistsError
        with pytest.raises(ClientExistsError) as exc_info:
            client_handler.add_new_client("existing_client")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.docker
    def test_add_new_client_invalid_name(self, environment, client_handler):
        """Test validation of client name with invalid characters."""
        # Attempt to add client with invalid character (@) in name
        with pytest.raises(InvalidClientNameError) as exc_info:
            client_handler.add_new_client("test@client")
        assert "invalid characters" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.docker
    def test_add_new_client_ip_exhaustion(self, environment, data_store, client_handler):
        """Test handling when no IP addresses are available in the subnet."""
        # Mock IP allocation to simulate exhausted subnet
        with patch.object(data_store, 'allocate_next_available_ip') as mock_allocate:
            mock_allocate.side_effect = ValueError("No available IPs")

            # Attempt to add client when IPs are exhausted
            with pytest.raises(IPAllocationError) as exc_info:
                client_handler.add_new_client("new_client")
            assert "No available IP addresses" in str(exc_info.value)
            assert "10.8.0.0/24" in str(exc_info.value)  # Verify subnet info in error

    @pytest.mark.integration
    @pytest.mark.docker
    def test_remove_existing_client_success(self, environment, client_handler):
        """Test successful removal of an existing WireGuard client."""
        # First add a client to be removed
        add_result = client_handler.add_new_client("test-client")
        assert add_result.client.name == "test-client"
        client_ip = add_result.client.ip  # Store IP for verification

        # Remove the client
        result = client_handler.remove_existing_client("test-client")

        # Verify removal was successful
        assert isinstance(result, ClientRemoveResult)
        assert result.removed is True
        assert result.client_name == "test-client"
        assert result.client_ip == client_ip

    @pytest.mark.integration
    @pytest.mark.docker
    def test_remove_nonexistent_client(self, environment, client_handler):
        """Test error handling when attempting to remove a non-existent client."""
        # Attempt to remove a client that doesn't exist
        with pytest.raises(ClientNotFoundError) as exc_info:
            client_handler.remove_existing_client("nonexistent")
        assert "not found" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.docker
    def test_list_all_clients_with_pagination(self, environment, client_handler):
        """Test client listing with pagination functionality."""
        # Clean up any existing clients first
        print("Cleaning up existing clients...")
        existing_clients = client_handler.list_all_clients()
        if existing_clients.total > 0:
            for client in existing_clients.clients:
                client_handler.remove_existing_client(client.name)
                print(f"Removed existing client: {client.name}")
        print(f"Cleanup complete. Removed {existing_clients.total} clients.")

        # Create 25 test clients for pagination testing
        print("Creating 25 test clients for pagination testing...")
        for i in range(1, 26):
            client_handler.add_new_client(f"client_{i:02d}")
            if i % 5 == 0:
                print(f"Progress: {i}/25 clients created ({i * 100 // 25}%)")
        print("Successfully created 25 test clients.")

        # Test page 1 with 10 items per page
        result = client_handler.list_all_clients(page=1, per_page=10)

        # Verify pagination metadata for page 1
        assert isinstance(result, ClientListResult)
        assert result.total == 25
        assert len(result.clients) == 10
        assert result.pagination.page == 1
        assert result.pagination.total_pages == 3
        assert result.pagination.has_next is True
        assert result.pagination.has_prev is False

        # Verify first client in list
        assert result.clients[0].name == "client_01"

        # Test page 2 with 10 items per page
        result_page2 = client_handler.list_all_clients(page=2, per_page=10)
        assert len(result_page2.clients) == 10
        assert result_page2.pagination.page == 2
        assert result_page2.pagination.has_next is True
        assert result_page2.pagination.has_prev is True

        # Test page 3 with remaining 5 items
        result_page3 = client_handler.list_all_clients(page=3, per_page=10)
        assert len(result_page3.clients) == 5
        assert result_page3.pagination.has_next is False

    @pytest.mark.integration
    @pytest.mark.docker
    def test_list_all_clients_with_search(self, environment, client_handler):
        """Test client listing with search/filter functionality."""
        # Create test clients with various names
        clients = [
            "alice_vpn",
            "bob_work",
            "alice_home",
            "charlie"
        ]
        for name in clients:
            client_handler.add_new_client(name)
            print(f"Created client: {name}")

        # Search for clients with "alice" in name
        result = client_handler.list_all_clients(search="alice")

        # Verify search results
        assert result.total == 2  # Should find 2 alice clients
        assert all("alice" in client.name for client in result.clients)  # type: ignore

    @pytest.mark.integration
    @pytest.mark.docker
    def test_export_client_configuration_success(self, environment, client_handler):
        """Test successful export of client configuration for connection."""
        # Add a client first
        add_client_result = client_handler.add_new_client("test_export_client")

        # Export the client configuration
        result = client_handler.export_client_configuration("test_export_client")

        # Verify result types
        assert isinstance(add_client_result, ClientAddResult)
        assert isinstance(result, ClientExportResult)
        assert result.client.name == "test_export_client"

        # Verify configuration contains necessary sections
        assert "[Interface]" in result.config  # Client section
        assert add_client_result.client.private_key in result.config  # Private key
        assert add_client_result.client.ip in result.config  # Client IP
        assert "[Peer]" in result.config  # Server section
        assert client_handler.config.get('server')["public_key"] in result.config  # Server public key

    @pytest.mark.integration
    @pytest.mark.docker
    def test_export_nonexistent_client(self, environment, client_handler):
        """Test error handling when exporting configuration for non-existent client."""
        # Attempt to export configuration for client that doesn't exist
        with pytest.raises(ClientNotFoundError) as exc_info:
            client_handler.export_client_configuration("nonexistent")

        assert "not found" in str(exc_info.value)

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_recently_added_clients(self, environment, client_handler):
        """Test retrieval of recently added clients in reverse chronological order."""
        # Create multiple test clients
        clients = [
            "dev_laptop",
            "prod_server",
            "test_machine",
            "mobile_device",
            "ios_device"
        ]

        for name in clients:
            client_handler.add_new_client(name)
            print(f"Created client: {name}")

        # Get last 5 clients added
        result = client_handler.get_recently_added_clients(count=5)

        # Verify result
        assert isinstance(result, LatestClientsResult)
        assert result.count == 5

        # Verify order (newest first)
        assert result.latest_clients[0].name == "ios_device"  # Last added
        assert result.latest_clients[4].name == "dev_laptop"  # First added

    @pytest.mark.integration
    @pytest.mark.docker
    def test_dynamic_peer_addition_success(self, environment, client_handler, docker_executor):
        """Test dynamic peer addition without service restart."""
        # Mock to disable service restart
        with patch.object(client_handler, 'core_module') as mock_core_module:
            mock_core_module.restart_service_after_client_creation = False

            # Add client dynamically
            add_client_result = client_handler.add_new_client('test_add_dynamic_peer_for_addition')

            # Verify client is added to configuration file
            assert environment["wg_config_file"].exists()
            config_content = environment["wg_config_file"].read_text()
            assert add_client_result.client.public_key in config_content
            assert add_client_result.client.ip in config_content

    @pytest.mark.integration
    @pytest.mark.docker
    def test_dynamic_peer_removal_success(self, environment, client_handler):
        """Test dynamic peer removal without service restart."""
        # Mock to disable service restart
        with patch.object(client_handler, 'core_module') as mock_core_module:
            mock_core_module.restart_service_after_client_creation = False

            # Add client dynamically first
            add_client_result = client_handler.add_new_client('test_add_dynamic_peer_for_removal')

            # Verify client is in configuration
            assert environment["wg_config_file"].exists()
            config_content = environment["wg_config_file"].read_text()
            assert add_client_result.client.public_key in config_content
            assert add_client_result.client.ip in config_content

            # Remove client dynamically
            result = client_handler.remove_existing_client('test_add_dynamic_peer_for_removal')
            assert isinstance(result, ClientRemoveResult)
            assert result.removed is True
            assert result.client_name == "test_add_dynamic_peer_for_removal"
            assert result.client_ip == add_client_result.client.ip

            # Verify client is removed from configuration
            assert environment["wg_config_file"].exists()
            config_content = environment["wg_config_file"].read_text()
            assert add_client_result.client.ip not in config_content
            assert add_client_result.client.public_key not in config_content
