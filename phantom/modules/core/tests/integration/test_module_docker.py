"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Core Module Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from pathlib import Path

from phantom.modules.core.module import CoreModule
from phantom.modules.core.tests.helpers.command_executor import CommandExecutor
from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor


class TestModuleDocker:

    @pytest.fixture
    def docker_executor(self, shared_docker_container):
        """Provide Docker command executor for running commands in test container."""
        # Create Docker executor with shared container
        executor = DockerCommandExecutor(shared_docker_container)
        executor.container = shared_docker_container
        return executor

    @pytest.fixture
    def command_executor(self, docker_executor):
        """Provide command executor wrapper for Docker operations."""
        # Wrap Docker executor with CommandExecutor interface
        return CommandExecutor(docker_executor)

    @pytest.fixture
    def core_module(self, docker_executor, command_executor, shared_docker_container):
        """Provide CoreModule instance configured for Docker testing."""
        # Get host directories from the shared container
        host_phantom_dir = Path(shared_docker_container.host_phantom_dir)
        host_config_dir = Path(shared_docker_container.host_config_dir)

        # Create data directory if it doesn't exist
        data_dir = host_phantom_dir / "data"
        data_dir.mkdir(exist_ok=True)

        # Define WireGuard configuration file path
        config_file = host_config_dir / "wg_main.conf"

        # Create CoreModule subclass that uses Docker command executor
        class DockerCoreModule(CoreModule):
            def _run_command(self, command, **kwargs):
                return command_executor.run_command(command, **kwargs)

        # Initialize and return the Docker-enabled CoreModule
        core_module = DockerCoreModule(install_dir=host_phantom_dir, wg_config_file=config_file)
        yield core_module

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_module_name(self, core_module, docker_executor):
        """Test retrieving the module name."""
        # Get module name from CoreModule
        result = core_module.get_module_name()

        # Verify module name is "core"
        assert result == "core"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_module_description(self, core_module, docker_executor):
        """Test retrieving the module description."""
        # Get module description
        result = core_module.get_module_description()

        # Verify description is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_actions(self, core_module, docker_executor):
        """Test retrieving all available module actions."""
        # Get all available actions from the module
        result = core_module.get_actions()

        # Verify result is a dictionary
        assert isinstance(result, dict)

        # Verify client management actions are present
        assert "add_client" in result
        assert "remove_client" in result
        assert "list_clients" in result
        assert "export_client" in result
        assert "latest_clients" in result

        # Verify server management actions are present
        assert "server_status" in result
        assert "service_logs" in result
        assert "restart_service" in result
        assert "get_firewall_status" in result

        # Verify tweak settings actions are present
        assert "get_tweak_settings" in result
        assert "update_tweak_setting" in result

        # Verify subnet management actions are present
        assert "get_subnet_info" in result
        assert "validate_subnet_change" in result
        assert "change_subnet" in result

    @pytest.mark.integration
    @pytest.mark.docker
    def test_add_client(self, core_module, docker_executor):
        """Test adding a new WireGuard client in Docker container."""
        # Define test client name
        client_name = "test_client_docker"

        # Add new client to WireGuard
        result = core_module.add_client(client_name)

        # Verify response structure
        assert isinstance(result, dict)
        assert "client" in result
        assert "message" in result

        # Verify client details
        client = result["client"]
        assert client["name"] == client_name
        assert "ip" in client or "ip_address" in client
        assert "public_key" in client
        assert "created" in client or "created_at" in client

        # Verify client is actually added to WireGuard interface
        wg_output = docker_executor("wg show wg_main peers")
        assert client["public_key"] in wg_output["stdout"]

    @pytest.mark.integration
    @pytest.mark.docker
    def test_list_clients(self, core_module, docker_executor):
        """Test listing all WireGuard clients."""
        # Add a test client first
        core_module.add_client("list_test_client")

        # List all clients
        result = core_module.list_clients()

        # Verify response structure
        assert isinstance(result, dict)
        assert "clients" in result
        assert isinstance(result["clients"], list)
        assert len(result["clients"]) > 0

        # Verify client information
        client = result["clients"][0]
        assert "name" in client
        assert "ip" in client or "ip_address" in client
        assert "enabled" in client

    @pytest.mark.integration
    @pytest.mark.docker
    def test_remove_client(self, core_module, docker_executor):
        """Test removing a WireGuard client."""
        # Add a client to be removed
        client_name = "remove_test_client"
        add_result = core_module.add_client(client_name)
        public_key = add_result["client"]["public_key"]

        # Remove the client
        result = core_module.remove_client(client_name)

        # Verify removal response
        assert isinstance(result, dict)
        assert "removed" in result
        assert result["removed"] == True
        assert "client_name" in result
        assert result["client_name"] == client_name

        # Verify client is removed from WireGuard interface
        wg_output = docker_executor("wg show wg_main peers")
        assert public_key not in wg_output["stdout"]

    @pytest.mark.integration
    @pytest.mark.docker
    def test_export_client(self, core_module, docker_executor):
        """Test exporting client configuration."""
        # Add a client to export
        client_name = "export_test_client"
        core_module.add_client(client_name)

        # Export client configuration
        result = core_module.export_client(client_name)

        # Verify export response structure
        assert isinstance(result, dict)
        assert "config" in result
        assert "client" in result

        # Verify configuration content
        config = result["config"]
        assert "[Interface]" in config
        assert "[Peer]" in config
        assert "PrivateKey" in config
        assert "PublicKey" in config

    @pytest.mark.integration
    @pytest.mark.docker
    def test_latest_clients(self, core_module, docker_executor):
        """Test retrieving latest added clients."""
        # Add multiple test clients
        core_module.add_client("latest_client_1")
        core_module.add_client("latest_client_2")

        # Get latest clients
        result = core_module.latest_clients(count=5)

        # Verify response structure
        assert isinstance(result, dict)
        assert "latest_clients" in result or "clients" in result

        # Verify client list
        clients = result.get("latest_clients", result.get("clients", []))
        assert isinstance(clients, list)
        assert len(clients) >= 2

    @pytest.mark.integration
    @pytest.mark.docker
    def test_server_status(self, core_module, docker_executor):
        """Test retrieving WireGuard server status."""
        # Get server status information
        result = core_module.server_status()

        # Verify response structure
        assert isinstance(result, dict)
        assert "interface" in result
        assert "service" in result
        assert "clients" in result
        assert "clients" in result and "active_connections" in result["clients"]

        # Verify interface status
        assert result["interface"]["active"] == True
        assert "interface" in result["interface"]
        assert result["interface"]["interface"] == "wg_main"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_service_logs(self, core_module, docker_executor):
        """Test retrieving WireGuard service logs."""
        # Get last 10 lines of service logs
        result = core_module.service_logs(lines=10)

        # Verify response structure and content
        assert isinstance(result, dict)
        assert "logs" in result
        assert isinstance(result["logs"], list)
        assert len(result["logs"]) <= 10

    @pytest.mark.integration
    @pytest.mark.docker
    def test_restart_service(self, core_module, docker_executor):
        """Test restarting WireGuard service."""
        # Restart the WireGuard service
        result = core_module.restart_service()

        # Verify restart response
        assert isinstance(result, dict)
        assert "restarted" in result
        assert "service_active" in result
        assert "interface_up" in result

        # Verify service is back up
        assert result["restarted"] == True
        assert result["service_active"] == True
        assert result["interface_up"] == True

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_firewall_status(self, core_module, docker_executor):
        """Test retrieving firewall status."""
        # Get firewall status
        result = core_module.get_firewall_status()

        # Verify firewall information is present
        assert isinstance(result, dict)
        assert "ufw" in result
        assert "iptables" in result

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_tweak_settings(self, core_module, docker_executor):
        """Test retrieving tweak settings."""
        # Get current tweak settings
        result = core_module.get_tweak_settings()

        # Verify tweak settings structure
        assert isinstance(result, dict)
        assert "restart_service_after_client_creation" in result

    @pytest.mark.integration
    @pytest.mark.docker
    def test_update_tweak_setting(self, core_module, docker_executor):
        """Test updating a tweak setting."""
        # Define setting to update
        setting_key = "restart_service_after_client_creation"
        setting_value = True

        # Update the tweak setting
        result = core_module.update_tweak_setting(setting_key, setting_value)

        # Verify update response
        assert isinstance(result, dict)
        assert "setting" in result
        assert result["setting"] == setting_key
        assert "new_value" in result
        assert result["new_value"] == setting_value
        assert "message" in result

    @pytest.mark.integration
    @pytest.mark.docker
    def test_get_subnet_info(self, core_module, docker_executor):
        """Test retrieving subnet information."""
        # Get current subnet information
        result = core_module.get_subnet_info()

        # Verify subnet information structure
        assert isinstance(result, dict)
        assert "current_subnet" in result
        assert "clients" in result
        assert result["current_subnet"] == "10.8.0.0/24"

    @pytest.mark.integration
    @pytest.mark.docker
    def test_validate_subnet_change(self, core_module, docker_executor):
        """Test validating a subnet change."""
        # Define new subnet to validate
        new_subnet = "10.9.0.0/24"

        # Validate the subnet change
        result = core_module.validate_subnet_change(new_subnet)

        # Verify validation response
        assert isinstance(result, dict)
        assert "valid" in result
        assert "warnings" in result
        assert isinstance(result["warnings"], list)

    @pytest.mark.integration
    @pytest.mark.docker
    def test_change_subnet(self, core_module, docker_executor):
        """Test changing the WireGuard network subnet."""
        # Define new subnet
        new_subnet = "10.9.0.0/24"

        # Verify initial subnet
        initial_info = core_module.get_subnet_info()
        assert initial_info["current_subnet"] == "10.8.0.0/24"

        # Validate the change first
        validation = core_module.validate_subnet_change(new_subnet)
        assert validation["valid"] == True

        # Change to new subnet
        result = core_module.change_subnet(new_subnet, confirm=True)

        # Verify change was successful
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] == True
        assert "new_subnet" in result
        assert result["new_subnet"] == new_subnet

        # Verify subnet was actually changed
        updated_info = core_module.get_subnet_info()
        assert updated_info["current_subnet"] == new_subnet

        # Verify network interface has new IP
        wg_output = docker_executor.run_command("ip addr show wg_main")
        assert "10.9.0.1/24" in wg_output["stdout"]

        # Restore original subnet for cleanup
        core_module.change_subnet("10.8.0.0/24", confirm=True)
        final_info = core_module.get_subnet_info()
        assert final_info["current_subnet"] == "10.8.0.0/24"
