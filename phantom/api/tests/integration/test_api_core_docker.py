"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Phantom API Core Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from pathlib import Path

from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor
from phantom.modules.core.tests.helpers.command_executor import CommandExecutor

from phantom.modules.core.module import CoreModule
from phantom.api.core import PhantomAPI
from phantom.api.response import APIResponse


class TestApiCoreDocker:

    @pytest.fixture
    def docker_executor(self, shared_docker_container):
        """Provides Docker command execution wrapper for tests."""
        executor = DockerCommandExecutor(shared_docker_container)
        executor.container = shared_docker_container
        return executor

    @pytest.fixture
    def command_executor(self, docker_executor):
        return CommandExecutor(docker_executor)

    @pytest.fixture
    def api(self, docker_executor, shared_docker_container, command_executor):
        """Creates a Docker-aware PhantomAPI instance for integration testing."""
        # Override PhantomAPI to prevent automatic module loading
        class DockerPhantomAPI(PhantomAPI):
            def _load_modules(self) -> None:
                pass

        # Override CoreModule to use Docker executor for commands
        class DockerCoreModule(CoreModule):
            def _run_command(self, command, **kwargs):
                return command_executor.run_command(command, **kwargs)

        host_phantom_dir = Path(shared_docker_container.host_phantom_dir)
        host_config_dir = Path(shared_docker_container.host_config_dir)

        # Ensure data directory exists
        host_data_dir = host_phantom_dir / "data"
        host_data_dir.mkdir(exist_ok=True)

        config_file = host_config_dir / "wg_main.conf"

        # Initialize API with Docker-aware CoreModule
        api = DockerPhantomAPI(install_dir=host_phantom_dir)
        api._modules['core'] = DockerCoreModule(install_dir=host_phantom_dir, wg_config_file=config_file)

        yield api

    @pytest.mark.docker
    def test_api_initialization(self, api):
        result = api.execute('core', 'server_status')
        assert isinstance(result, APIResponse)
        assert result.success == True

        assert hasattr(api, '_modules')
        assert 'core' in api._modules

    # Client Management API Tests

    @pytest.mark.docker
    def test_add_client(self, api, docker_executor):
        client_name = "test_client_docker"

        # Execute client addition
        result = api.execute('core', 'add_client', client_name=client_name)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "client" in result.data
        assert "message" in result.data

        client = result.data["client"]
        assert client["name"] == client_name
        assert "ip" in client or "ip_address" in client
        assert "public_key" in client
        assert "created" in client or "created_at" in client

        wg_output = docker_executor.run_command("wg show wg_main peers")
        assert client["public_key"] in wg_output["stdout"]

    @pytest.mark.docker
    def test_list_clients(self, api):
        api.execute('core', 'add_client', client_name="list_test_client")

        # List all clients
        result = api.execute('core', 'list_clients')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "clients" in result.data
        assert isinstance(result.data["clients"], list)
        assert len(result.data["clients"]) > 0

        client = result.data["clients"][0]
        assert "name" in client
        assert "ip" in client or "ip_address" in client
        assert "enabled" in client

    @pytest.mark.docker
    def test_remove_client(self, api, docker_executor):
        client_name = "remove_test_client"
        add_result = api.execute('core', 'add_client', client_name=client_name)
        public_key = add_result.data["client"]["public_key"]

        # Remove client
        result = api.execute('core', 'remove_client', client_name=client_name)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "removed" in result.data
        assert result.data["removed"] == True
        assert "client_name" in result.data
        assert result.data["client_name"] == client_name

        # Verify client is removed from WireGuard
        wg_output = docker_executor.run_command("wg show wg_main peers")
        assert public_key not in wg_output["stdout"]

    @pytest.mark.docker
    def test_export_client(self, api):
        client_name = "export_test_client"
        api.execute('core', 'add_client', client_name=client_name)

        # Export configuration
        result = api.execute('core', 'export_client', client_name=client_name)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "config" in result.data
        assert "client" in result.data

        config = result.data["config"]
        assert "[Interface]" in config
        assert "[Peer]" in config
        assert "PrivateKey" in config
        assert "PublicKey" in config

    @pytest.mark.docker
    def test_latest_clients(self, api):
        api.execute('core', 'add_client', client_name="latest_client_1")
        api.execute('core', 'add_client', client_name="latest_client_2")

        result = api.execute('core', 'latest_clients', count=5)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "latest_clients" in result.data or "clients" in result.data

        clients = result.data.get("latest_clients", result.data.get("clients", []))
        assert isinstance(clients, list)
        assert len(clients) >= 2

    # Service Management API Tests

    @pytest.mark.docker
    def test_server_status(self, api):
        result = api.execute('core', 'server_status')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "interface" in result.data
        assert "service" in result.data
        assert "clients" in result.data

        assert result.data["interface"]["active"] == True
        assert "interface" in result.data["interface"]
        assert result.data["interface"]["interface"] == "wg_main"

    @pytest.mark.docker
    def test_service_logs(self, api):
        result = api.execute('core', 'service_logs', lines=10)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "logs" in result.data
        assert isinstance(result.data["logs"], list)
        assert len(result.data["logs"]) <= 10

    @pytest.mark.docker
    def test_restart_service(self, api):
        # Restart service
        result = api.execute('core', 'restart_service')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "restarted" in result.data
        assert "service_active" in result.data
        assert "interface_up" in result.data

        assert result.data["restarted"] == True
        assert result.data["service_active"] == True
        assert result.data["interface_up"] == True

    @pytest.mark.docker
    def test_get_firewall_status(self, api):
        result = api.execute('core', 'get_firewall_status')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "ufw" in result.data
        assert "iptables" in result.data

    # Configuration API Tests

    @pytest.mark.docker
    def test_get_tweak_settings(self, api):
        result = api.execute('core', 'get_tweak_settings')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "restart_service_after_client_creation" in result.data

    @pytest.mark.docker
    def test_update_tweak_setting(self, api):
        setting_key = "restart_service_after_client_creation"
        setting_value = True

        result = api.execute('core', 'update_tweak_setting', setting_name=setting_key, value=setting_value)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "setting" in result.data
        assert result.data["setting"] == setting_key
        assert "new_value" in result.data
        assert result.data["new_value"] == setting_value
        assert "message" in result.data

    # Network Management API Tests

    @pytest.mark.docker
    def test_get_subnet_info(self, api):
        result = api.execute('core', 'get_subnet_info')

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "current_subnet" in result.data
        assert "clients" in result.data
        assert result.data["current_subnet"] == "10.8.0.0/24"

    @pytest.mark.docker
    def test_validate_subnet_change(self, api):
        new_subnet = "10.9.0.0/24"

        # Validate change
        result = api.execute('core', 'validate_subnet_change', new_subnet=new_subnet)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "valid" in result.data
        assert "warnings" in result.data
        assert isinstance(result.data["warnings"], list)

    @pytest.mark.docker
    def test_change_subnet(self, api, docker_executor):
        new_subnet = "10.9.0.0/24"

        # Verify initial subnet
        initial_info = api.execute('core', 'get_subnet_info')
        assert initial_info.data["current_subnet"] == "10.8.0.0/24"

        # Validate change before applying
        validation = api.execute('core', 'validate_subnet_change', new_subnet=new_subnet)
        assert validation.data["valid"] == True

        # Apply subnet change
        result = api.execute('core', 'change_subnet', new_subnet=new_subnet, confirm=True)

        assert isinstance(result, APIResponse)
        assert result.success == True
        assert "success" in result.data
        assert result.data["success"] == True
        assert "new_subnet" in result.data
        assert result.data["new_subnet"] == new_subnet

        # Verify subnet was changed
        updated_info = api.execute('core', 'get_subnet_info')
        assert updated_info.data["current_subnet"] == new_subnet

        # Verify at network interface level
        wg_output = docker_executor.run_command("ip addr show wg_main")
        assert "10.9.0.1/24" in wg_output["stdout"]

        # Restore original subnet for other tests
        api.execute('core', 'change_subnet', new_subnet="10.8.0.0/24", confirm=True)
        final_info = api.execute('core', 'get_subnet_info')
        assert final_info.data["current_subnet"] == "10.8.0.0/24"
