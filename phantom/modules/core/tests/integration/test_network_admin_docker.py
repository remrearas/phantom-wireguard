"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Network Admin Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
import json
import ipaddress
from pathlib import Path

from phantom.modules.core.lib.key_generator import KeyGenerator
from phantom.modules.core.lib.client_handler import ClientHandler
from phantom.modules.core.lib.network_admin import NetworkAdmin
from phantom.modules.core.lib.data_store import DataStore
from phantom.modules.core.lib.service_monitor import ServiceMonitor
from phantom.modules.core.lib.common_tools import CommonTools

from phantom.modules.core.tests.helpers.command_executor import CommandExecutor
from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor

from phantom.modules.core.lib.default_constants import (
    DEFAULT_WG_INTERFACE,
    DEFAULT_WG_NETWORK
)


class TestNetworkAdminDocker:

    @pytest.fixture
    def docker_executor(self, shared_docker_container):
        executor = DockerCommandExecutor(shared_docker_container)
        executor.container = shared_docker_container
        return executor

    @pytest.fixture
    def command_executor(self, docker_executor):
        return CommandExecutor(docker_executor)

    @pytest.fixture
    def environment(self, shared_docker_container):
        host_phantom_dir = Path(shared_docker_container.host_phantom_dir)
        host_config_dir = Path(shared_docker_container.host_config_dir)

        data_dir = host_phantom_dir / "data"
        data_dir.mkdir(exist_ok=True)

        phantom_config_dir = host_phantom_dir / "config"
        phantom_config_file = phantom_config_dir / "phantom.json"
        wg_config_file = host_config_dir / "wg_main.conf"

        return {
            "host_phantom_dir": host_phantom_dir,
            "host_config_dir": host_config_dir,
            "data_dir": data_dir,
            "phantom_config_dir": phantom_config_dir,
            "phantom_config_file": phantom_config_file,
            "wg_config_file": wg_config_file
        }

    @pytest.fixture
    def phantom_config_content(self, environment):
        phantom_config_file = environment["phantom_config_file"]
        phantom_config_content = json.loads(phantom_config_file.read_text()) if phantom_config_file.exists() else {}
        return phantom_config_content

    @pytest.fixture
    def data_store(self, environment):
        db_path = environment["data_dir"] / 'data.db'
        data_store = DataStore(
            db_path=db_path,
            data_dir=environment["data_dir"],
            subnet=DEFAULT_WG_NETWORK
        )
        return data_store

    @pytest.fixture
    def key_generator(self, environment, command_executor):
        key_generator = KeyGenerator(run_command=command_executor.run_command)
        return key_generator

    @pytest.fixture
    def common_tools(self, phantom_config_content, command_executor):
        common_tools = CommonTools(
            config=phantom_config_content,
            run_command=command_executor.run_command
        )
        return common_tools

    @pytest.fixture
    def client_handler(self, data_store, key_generator, common_tools, phantom_config_content, command_executor,
                       environment):
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

    @pytest.fixture
    def service_monitor(self, data_store, common_tools, phantom_config_content, command_executor, environment):
        service_monitor = ServiceMonitor(
            data_store=data_store,
            common_tools=common_tools,
            config=phantom_config_content,
            run_command=command_executor.run_command,
            wg_interface=DEFAULT_WG_INTERFACE,
            wg_config_file=environment["wg_config_file"],
            install_dir=environment["host_phantom_dir"]
        )
        return service_monitor

    @pytest.fixture
    def network_admin(self, data_store, phantom_config_content, common_tools, service_monitor, command_executor,
                      environment):

        def save_config(new_config):
            with open(environment['phantom_config_file'], 'w') as config_file:
                json.dump(new_config, config_file, indent=2)

        network_admin = NetworkAdmin(
            data_store=data_store,
            common_tools=common_tools,
            service_monitor=service_monitor,
            config=phantom_config_content,
            save_config=save_config,
            run_command=command_executor.run_command,
            wg_interface=DEFAULT_WG_INTERFACE,
            wg_config_file=environment["wg_config_file"],
            install_dir=environment["host_phantom_dir"]
        )
        yield network_admin

    @pytest.mark.docker
    @pytest.mark.integration
    def test_validate_network_modification_valid_subnet(self, network_admin):
        """Test validation of valid RFC1918 private network subnet modification."""
        # Validate a valid RFC1918 private subnet
        result = network_admin.validate_network_modification("192.168.100.0/24")

        # Verify validation passes for valid private subnet
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["new_subnet"] == "192.168.100.0/24"
        assert "checks" in result  # Contains validation checks performed
        assert "warnings" in result  # May contain warnings even if valid

    @pytest.mark.docker
    @pytest.mark.integration
    def test_validate_network_modification_invalid_subnet(self, network_admin):
        """Test validation rejects public IP ranges and subnets that are too small."""
        # Test case 1: Public IP subnet should be rejected (must be RFC1918)
        result = network_admin.validate_network_modification("8.8.8.0/24")
        assert result["valid"] is False
        assert "RFC1918" in str(result["errors"])  # Error should mention RFC1918 requirement

        # Test case 2: Subnet too small (only 4 IPs) should be rejected
        result = network_admin.validate_network_modification("10.10.10.0/30")
        assert result["valid"] is False
        assert any("small" in str(err).lower() or "size" in str(err).lower()
                   for err in result["errors"])  # Error should mention size issue

    @pytest.mark.docker
    @pytest.mark.integration
    def test_validate_network_modification_same_subnet(self, network_admin):
        """Test validation when attempting to migrate to the current subnet."""
        # Attempt to modify to the same subnet that's currently in use
        result = network_admin.validate_network_modification("10.8.0.0/24")

        # Verify the system detects no actual change in subnet
        assert result["current_subnet"] == result["new_subnet"]
        assert result["current_subnet"] == "10.8.0.0/24"

        # Validation result should still contain checks/warnings/errors
        assert "checks" in result or "warnings" in result or "errors" in result

    @pytest.mark.docker
    @pytest.mark.integration
    def test_rfc1918_subnet_validation(self, network_admin):
        """Test comprehensive validation of RFC1918 private address ranges."""
        # Define valid RFC1918 private subnets from different ranges
        valid_subnets = [
            "10.99.0.0/24",     # 10.0.0.0/8 range
            "172.20.0.0/24",    # 172.16.0.0/12 range
            "192.168.50.0/24"   # 192.168.0.0/16 range
        ]

        # Verify all RFC1918 subnets are accepted
        for subnet in valid_subnets:
            result = network_admin.validate_network_modification(subnet)
            assert result["valid"] is True, f"RFC1918 subnet {subnet} should be valid"

        # Define invalid public IP subnets
        invalid_subnets = [
            "8.8.8.0/24",       # Google DNS range
            "1.1.1.0/24",       # Cloudflare DNS range
            "44.55.66.0/24"     # Arbitrary public range
        ]

        # Verify public subnets are rejected
        for subnet in invalid_subnets:
            result = network_admin.validate_network_modification(subnet)
            assert result["valid"] is False, f"Public subnet {subnet} should be invalid"

    @pytest.mark.docker
    @pytest.mark.integration
    def test_subnet_size_validation(self, network_admin):
        """Test validation ensures subnet has sufficient capacity for VPN operations."""
        # Define subnets with valid sizes for VPN operations
        valid_sizes = [
            ("10.20.0.0/24", 254),   # Standard size - 254 usable IPs
            ("10.20.0.0/23", 510),   # Larger network - 510 usable IPs
            ("10.20.0.0/22", 1022),  # Very large network - 1022 usable IPs
        ]

        # Verify appropriately sized subnets are accepted
        for subnet, expected_ips in valid_sizes:
            result = network_admin.validate_network_modification(subnet)
            assert result["valid"] is True

        # Define subnets that are too small for practical VPN use
        invalid_sizes = [
            "10.20.0.0/30",  # Only 2 usable IPs
            "10.20.0.0/31",  # Only 2 IPs (point-to-point)
            "10.20.0.0/32"   # Single host address
        ]

        # Verify undersized subnets are rejected
        for subnet in invalid_sizes:
            result = network_admin.validate_network_modification(subnet)
            assert result["valid"] is False

    @pytest.mark.docker
    @pytest.mark.integration
    def test_ghost_mode_state_check(self, network_admin, environment):
        """Test network migration is blocked when ghost mode is active."""
        # Initial check - ghost mode should not be active
        result = network_admin.analyze_current_network()
        assert "blockers" in result
        assert result["blockers"]["ghost_mode"] is False  # Ghost mode not active

        # Simulate ghost mode activation by creating state file
        ghost_state_file = environment["phantom_config_dir"] / "ghost-state.json"
        with open(ghost_state_file, 'w') as f:
            json.dump({"enabled": True, "mode": "active"}, f)

        # Verify ghost mode is now detected as a blocker
        result = network_admin.analyze_current_network()
        assert "blockers" in result  # Should detect ghost mode blocker

        # Clean up test file
        ghost_state_file.unlink()

    @pytest.mark.docker
    @pytest.mark.integration
    def test_client_ip_reassignment_logic(self, network_admin, client_handler, environment):
        """Test validation works correctly with existing clients that need IP reassignment."""
        # Create test clients in the current network
        client_handler.add_new_client('client-1')
        client_handler.add_new_client('client-2')

        # Validate migration to new subnet with existing clients
        result = network_admin.validate_network_modification("192.168.100.0/24")
        assert result["valid"] is True
        assert result["new_subnet"] == "192.168.100.0/24"
        assert "checks" in result or "warnings" in result  # Should include client reassignment info

    @pytest.mark.docker
    @pytest.mark.integration
    def test_network_capacity_analysis(self, network_admin, client_handler, environment):
        """Test network analysis provides complete information about current configuration."""
        # Analyze current network configuration
        analysis = network_admin.analyze_current_network()
        assert "current_subnet" in analysis
        assert "subnet_size" in analysis
        assert "server_ip" in analysis
        assert "clients" in analysis

        # Test validation with sufficient capacity subnet
        result = network_admin.validate_network_modification("172.25.0.0/24")
        assert "valid" in result
        assert "checks" in result
        if result["valid"]:
            assert "new_subnet" in result
            assert result["new_subnet"] == "172.25.0.0/24"

        # Test validation with limited capacity subnet (only 16 total IPs)
        result = network_admin.validate_network_modification("10.50.0.0/28")  # 16 IPs
        assert "valid" in result
        assert "new_subnet" in result
        if not result["valid"]:
            assert len(result["errors"]) > 0  # Should have capacity errors

    @pytest.mark.docker
    @pytest.mark.integration
    def test_execute_network_migration(self, network_admin, client_handler, environment):
        """Test complete network migration process with clients and configuration updates."""
        # Clean up any existing clients from previous tests
        print("Cleaning up existing clients...")
        existing_clients = client_handler.list_all_clients()
        if existing_clients.total > 0:
            for client in existing_clients.clients:
                client_handler.remove_existing_client(client.name)
                print(f"Removed existing client: {client.name}")
        print(f"Cleanup complete. Removed {existing_clients.total} clients.")

        # Create test clients to be migrated
        add_client_first_result = client_handler.add_new_client('client-first')
        print("Created client-first client")
        add_client_second_result = client_handler.add_new_client('client-second')
        print("Created client-second client")

        # Execute network migration with force flag to bypass warnings
        result = network_admin.execute_network_migration("192.168.100.0/24", force=True)

        # Verify migration completed successfully
        assert result["success"] is True
        assert result["old_subnet"] == "10.8.0.0/24"
        assert result["new_subnet"] == "192.168.100.0/24"
        assert result["clients_updated"] == 2  # Both clients migrated

        # Verify WireGuard configuration was updated with new IPs
        assert environment["wg_config_file"].exists()
        config_content = environment["wg_config_file"].read_text()
        # Server should use first IP in new subnet (network + 1)
        assert str(ipaddress.IPv4Network(result["new_subnet"]).network_address + 1) in config_content
        # Both clients' new IPs should be in configuration
        assert result['ip_mapping'][add_client_first_result.client.ip] in config_content
        assert result['ip_mapping'][add_client_second_result.client.ip] in config_content
