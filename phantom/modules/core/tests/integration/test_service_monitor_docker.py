"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

ServiceMonitor Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
import json
from pathlib import Path

from phantom.modules.core.lib.data_store import DataStore
from phantom.modules.core.lib.service_monitor import ServiceMonitor
from phantom.modules.core.lib.common_tools import CommonTools
from phantom.modules.core.lib.client_handler import ClientHandler
from phantom.modules.core.lib.key_generator import KeyGenerator

from phantom.modules.core.tests.helpers.command_executor import CommandExecutor
from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor

from phantom.modules.core.lib.default_constants import (
    DEFAULT_WG_INTERFACE,
    DEFAULT_WG_NETWORK
)


class TestServiceMonitorDocker:

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

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_wireguard_health(self, service_monitor, command_executor):
        """Test WireGuard health check retrieves service and interface status."""
        # Execute health check to get current WireGuard status
        result = service_monitor.check_wireguard_health()

        # Verify health check returns a result object
        assert result is not None
        # Verify interface status attributes are present
        if hasattr(result, 'interface'):
            assert hasattr(result.interface, 'active')
        # Verify service status attributes are present
        if hasattr(result, 'service'):
            assert hasattr(result.service, 'running')

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_wireguard_health_exception(self, service_monitor):
        """Test health check properly handles and wraps command execution failures."""
        from phantom.api.exceptions import ServiceOperationError

        # Save original command runner for restoration
        original_run_command = service_monitor._run_command

        # noinspection PyUnusedLocal
        def mock_run_command(cmd):
            raise RuntimeError("Command execution failed")

        # Replace command runner with failing mock
        service_monitor._run_command = mock_run_command

        # Verify ServiceOperationError is raised with proper message
        with pytest.raises(ServiceOperationError) as exc_info:
            service_monitor.check_wireguard_health()

        assert "Unable to retrieve server status" in str(exc_info.value)

        # Restore original command runner
        service_monitor._run_command = original_run_command

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_wireguard_health_no_interface(self, service_monitor, docker_executor):
        """Test health check correctly reports inactive status when service is stopped."""
        # Stop WireGuard service to test inactive state detection
        docker_executor("systemctl stop wg-quick@wg_main")

        # Check health status with stopped service
        result = service_monitor.check_wireguard_health()

        # Verify health check still returns results
        assert result is not None
        # Verify interface is reported as inactive
        if hasattr(result, 'interface') and result.interface:
            assert result.interface.active is False
        # Verify service is reported as not running
        if hasattr(result, 'service') and result.service:
            assert result.service.running is False

        # Restore service for subsequent tests
        docker_executor("systemctl start wg-quick@wg_main")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_get_service_running_status(self, service_monitor, docker_executor):
        """Test retrieval of detailed WireGuard service running status information."""
        # Get service status details from internal method
        result = service_monitor._get_service_running_status()

        # Verify status object was returned
        assert result is not None

        # Verify all required status attributes are present
        assert hasattr(result, 'running')
        assert hasattr(result, 'service_name')
        assert hasattr(result, 'started_at')
        assert hasattr(result, 'pid')

        # Verify correct service name is reported
        assert result.service_name == "wg-quick@wg_main"

        # Verify running status is a boolean
        assert isinstance(result.running, bool)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_retrieve_service_logs(self, service_monitor, docker_executor):
        """Test retrieval of service logs with and without journalctl availability."""
        # Test normal log retrieval with line limit
        result = service_monitor.retrieve_service_logs(lines=10)

        # Verify log structure and content limits
        assert isinstance(result, dict)
        assert 'logs' in result
        assert isinstance(result['logs'], list)
        assert len(result['logs']) <= 10  # Respect line limit

        # Test behavior when journalctl is unavailable
        docker_executor("mv /usr/bin/journalctl /usr/bin/journalctl.bak")
        result_mask_journalctl = service_monitor.retrieve_service_logs(lines=5)

        # Verify graceful handling when journalctl is missing
        assert isinstance(result_mask_journalctl, dict)
        assert 'logs' in result_mask_journalctl
        assert isinstance(result_mask_journalctl['logs'], list)
        assert result_mask_journalctl['logs'] == []  # Empty logs when unavailable
        assert 'message' in result_mask_journalctl
        assert result_mask_journalctl['message'] == "No logs available"

        # Restore journalctl for subsequent tests
        docker_executor("mv /usr/bin/journalctl.bak /usr/bin/journalctl")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_retrieve_service_logs_exception(self, service_monitor, docker_executor):
        """Test log retrieval properly handles and reports command execution failures."""
        from phantom.api.exceptions import ServiceOperationError

        # Save original command runner for restoration
        original_run_command = service_monitor._run_command

        # noinspection PyUnusedLocal
        def mock_run_command(cmd):
            raise RuntimeError("Command execution failed")

        # Replace command runner with failing mock
        service_monitor._run_command = mock_run_command

        # Verify ServiceOperationError is raised with helpful message
        with pytest.raises(ServiceOperationError) as exc_info:
            service_monitor.retrieve_service_logs(lines=10)

        assert "Unable to retrieve service logs" in str(exc_info.value)
        assert "journalctl is installed" in str(exc_info.value)  # Suggests journalctl requirement

        # Restore original command runner
        service_monitor._run_command = original_run_command

    @pytest.mark.docker
    @pytest.mark.integration
    def test_restart_wireguard_safely(self, service_monitor, docker_executor):
        """Test safe restart of WireGuard service with health verification."""
        # Execute safe restart with post-restart checks
        result = service_monitor.restart_wireguard_safely()

        # Verify restart result structure
        assert isinstance(result, dict)
        assert 'restarted' in result
        assert 'service_active' in result
        assert 'interface_up' in result
        assert 'service' in result
        assert 'message' in result

        # Verify successful restart and recovery
        assert result['restarted'] is True
        assert result['service_active'] is True  # Service running after restart
        assert result['interface_up'] is True  # Interface recovered

    @pytest.mark.docker
    @pytest.mark.integration
    def test_restart_wireguard_safely_exception(self, service_monitor, docker_executor):
        """Test restart failure handling with informative error messages."""
        from phantom.api.exceptions import ServiceOperationError

        # Save original command runner for restoration
        original_run_command = service_monitor._run_command

        # noinspection PyUnusedLocal
        def mock_run_command(cmd):
            raise RuntimeError("Command execution failed")

        # Replace command runner with failing mock
        service_monitor._run_command = mock_run_command

        # Verify ServiceOperationError with diagnostic hints
        with pytest.raises(ServiceOperationError) as exc_info:
            service_monitor.restart_wireguard_safely()

        # Verify error message includes troubleshooting hints
        assert "Failed to restart WireGuard service" in str(exc_info.value)
        assert "Configuration syntax errors" in str(exc_info.value)
        assert f"Port {51820} already in use" in str(exc_info.value)

        # Restore original command runner
        service_monitor._run_command = original_run_command

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_firewall_configuration(self, service_monitor, docker_executor):
        """Test firewall configuration check for both UFW and iptables."""
        # Check firewall configuration status
        result = service_monitor.check_firewall_configuration()

        # Verify both firewall types are checked
        assert isinstance(result, dict)
        assert 'ufw' in result  # UFW status check
        assert 'iptables' in result  # iptables status check

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_firewall_nat_rules(self, service_monitor, docker_executor):
        """Test NAT rules verification in iptables configuration."""
        # Check firewall configuration including NAT rules
        result = service_monitor.check_firewall_configuration()

        # Verify NAT rules are included in iptables check
        assert 'iptables' in result
        assert 'nat_rules' in result['iptables']  # NAT table rules for masquerading

    @pytest.mark.docker
    @pytest.mark.integration
    def test_check_firewall_configuration_exception(self, service_monitor, docker_executor):
        """Test firewall check error handling with diagnostic suggestions."""
        from phantom.api.exceptions import ServiceOperationError

        # Save original command runner for restoration
        original_run_command = service_monitor._run_command

        # noinspection PyUnusedLocal
        def mock_run_command(cmd):
            raise RuntimeError("Command execution failed")

        # Replace command runner with failing mock
        service_monitor._run_command = mock_run_command

        # Verify ServiceOperationError with diagnostic hints
        with pytest.raises(ServiceOperationError) as exc_info:
            service_monitor.check_firewall_configuration()

        # Verify error message includes diagnostic hints
        assert "Unable to check firewall status" in str(exc_info.value)
        assert "UFW is installed" in str(exc_info.value)  # Suggests UFW check
        assert "iptables is accessible" in str(exc_info.value)  # Suggests iptables check

        # Restore original command runner
        service_monitor._run_command = original_run_command

    @pytest.mark.docker
    @pytest.mark.integration
    def test_gather_interface_statistics(self, service_monitor, docker_executor):
        """Test interface statistics gathering in various interface states."""
        try:
            # Test case 1: Active WireGuard interface with statistics
            docker_executor("systemctl start wg-quick@wg_main")

            result = service_monitor.gather_interface_statistics()

            # Verify basic statistics structure
            assert isinstance(result, dict)
            assert 'active' in result
            assert 'interface' in result
            assert 'peers' in result
            assert result['interface'] == 'wg_main'

            # Verify detailed statistics when interface is active
            if result['active']:
                assert 'public_key' in result
                assert 'port' in result
                assert 'rx_bytes' in result  # Receive bytes counter
                assert 'tx_bytes' in result  # Transmit bytes counter
                assert isinstance(result['peers'], list)

            # Test case 2: Non-WireGuard dummy interface
            docker_executor("systemctl stop wg-quick@wg_main")
            docker_executor("sleep 1")
            docker_executor("ip link add wg_main type dummy 2>/dev/null || true")

            result = service_monitor.gather_interface_statistics()

            # Verify statistics for non-WireGuard interface
            assert result['active'] is False
            assert result['interface'] == 'wg_main'
            assert result['peers'] == []

            # Clean up dummy interface
            docker_executor("ip link delete wg_main 2>/dev/null || true")

            # Test case 3: No interface present
            docker_executor("systemctl stop wg-quick@wg_main")
            docker_executor("sleep 1")

            result = service_monitor.gather_interface_statistics()

            # Verify statistics when interface doesn't exist
            assert result['active'] is False
            assert result['interface'] == 'wg_main'
            assert result['peers'] == []

        finally:
            # Ensure interface is restored for subsequent tests
            docker_executor("ip link delete wg_main")
            docker_executor("systemctl start wg-quick@wg_main")
            docker_executor("sleep 1")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_gather_interface_statistics_exception(self, service_monitor, docker_executor):
        """Test interface statistics error handling without wrapping exceptions."""
        # Save original command runner for restoration
        original_run_command = service_monitor._run_command

        # noinspection PyUnusedLocal
        def mock_run_command(cmd):
            raise RuntimeError("Command execution failed")

        # Replace command runner with failing mock
        service_monitor._run_command = mock_run_command

        # Verify exception is not wrapped (passes through)
        with pytest.raises(RuntimeError) as exc_info:
            service_monitor.gather_interface_statistics()

        assert "Command execution failed" in str(exc_info.value)

        # Restore original command runner
        service_monitor._run_command = original_run_command

    @pytest.mark.docker
    @pytest.mark.integration
    def test_gather_active_connections_no_active_peers(self, service_monitor, docker_executor):
        """Test active connections returns empty dict when no peers are connected."""
        # Gather connections with no active peers
        result = service_monitor.gather_active_connections()

        # Verify empty dict is returned
        assert isinstance(result, dict)
        assert len(result) == 0  # No active connections

    @pytest.mark.docker
    @pytest.mark.integration
    def test_gather_active_connections(self, service_monitor, client_handler, docker_executor):
        """Test active connection detection using network namespace to simulate real client."""
        client_name = 'test_ns_client'
        try:
            # Create a test client with configuration
            client_handler.add_new_client(client_name)
            client_config_result = client_handler.export_client_configuration(client_name)
            client_config = client_config_result.config

            # Setup network namespace to simulate isolated client
            docker_executor("systemctl start wg-quick@wg_main")
            docker_executor("ip netns add wg-test-client")
            docker_executor("ip link add veth-main type veth peer name veth-client")
            docker_executor("ip link set veth-client netns wg-test-client")

            # Configure veth pair for connectivity between namespaces
            docker_executor("ip addr add 192.168.200.1/24 dev veth-main")
            docker_executor("ip link set veth-main up")
            docker_executor("ip netns exec wg-test-client ip addr add 192.168.200.2/24 dev veth-client")
            docker_executor("ip netns exec wg-test-client ip link set veth-client up")
            docker_executor("ip netns exec wg-test-client ip link set lo up")

            import re

            # Modify client config to use veth endpoint
            modified_config = re.sub(
                r'Endpoint = .*:(\d+)',
                r'Endpoint = 192.168.200.1:\1',
                client_config
            )

            # Remove DNS to avoid resolution issues in namespace
            modified_config = re.sub(
                r'^DNS = .*$',
                '',
                modified_config,
                flags=re.MULTILINE
            )

            # Clean up extra newlines
            modified_config = re.sub(r'\n\n+', '\n', modified_config)

            # Escape quotes for shell command
            escaped_config = modified_config.replace("'", "'\"'\"'")

            # Write config file in container
            docker_executor(f"bash -c 'cat > /tmp/wg-test-client.conf << \"EOF\"\n{escaped_config}\nEOF'")

            result = docker_executor("ls -la /tmp/wg-test-client.conf")
            print(f"File created: {result}")

            result = docker_executor("head -5 /tmp/wg-test-client.conf")
            print(f"Config first 5 lines: {result}")

            # Start WireGuard client in namespace
            docker_executor("ip netns exec wg-test-client wg-quick up /tmp/wg-test-client.conf")

            # Generate traffic to establish handshake
            docker_executor("ip netns exec wg-test-client ping -c 2 10.8.0.1")

            # Send various packet sizes to test connection
            docker_executor("ip netns exec wg-test-client ping -c 5 -s 100 10.8.0.1")
            docker_executor("ip netns exec wg-test-client ping -c 3 -s 1000 10.8.0.1")

            # Wait for handshake to be recent
            docker_executor("sleep 2")

            # Gather active connections from server perspective
            result = service_monitor.gather_active_connections()

            assert isinstance(result, dict)

            # Verify connection detection if handshake succeeded
            if len(result) > 0:
                assert client_name in result or 'Unknown' in result

                connection = result.get(client_name) or next(iter(result.values()))

                # Verify connection details are present
                assert 'latest_handshake' in connection
                assert 'public_key' in connection
                assert 'allowed_ips' in connection

                # Verify handshake is recent
                handshake = connection['latest_handshake']
                if 'second' in handshake:
                    seconds = int(handshake.split()[0])
                    assert seconds < 60, f"Handshake too old: {handshake}"

        finally:
            # Clean up namespace and test resources
            docker_executor("ip netns exec wg-test-client wg-quick down /tmp/wg-test-client.conf")
            client_handler.remove_existing_client(client_name)
            docker_executor("ip netns delete wg-test-client")
            docker_executor("ip link delete veth-main")
            docker_executor("rm -f /tmp/wg-test-client.conf")

    @pytest.mark.docker
    @pytest.mark.integration
    def test_calculate_client_statistics(self, service_monitor):
        """Test client statistics calculation with no configured clients."""
        # Calculate statistics with empty database
        result = service_monitor.calculate_client_statistics()

        # Verify statistics structure and zero counts
        assert isinstance(result, dict)
        assert result['total_configured'] == 0  # No clients configured
        assert result['active_connections'] == 0  # No active connections

    @pytest.mark.docker
    @pytest.mark.integration
    def test_gather_system_information(self, service_monitor, docker_executor):
        """Test gathering comprehensive system information about Phantom installation."""
        # Gather system information
        result = service_monitor.gather_system_information()

        # Verify all system information fields are present
        assert isinstance(result, dict)
        assert 'install_dir' in result  # Phantom installation directory
        assert 'config_dir' in result  # Configuration directory
        assert 'data_dir' in result  # Data storage directory
        assert 'firewall' in result  # Firewall status information
        assert 'wireguard_module' in result  # WireGuard kernel module status

    @pytest.mark.docker
    @pytest.mark.integration
    def test_performance_check_wireguard_health(self, service_monitor):
        """Test health check performance meets acceptable time threshold."""
        import time

        # Measure health check execution time
        start = time.time()
        service_monitor.check_wireguard_health()
        elapsed = time.time() - start

        # Verify health check completes within 2 seconds
        assert elapsed < 2.0

    @pytest.mark.docker
    @pytest.mark.integration
    def test_performance_gather_system_information(self, service_monitor):
        """Test system information gathering performance meets acceptable threshold."""
        import time

        # Measure system information gathering time
        start = time.time()
        service_monitor.gather_system_information()
        elapsed = time.time() - start

        # Verify system info gathering completes within 5 seconds
        assert elapsed < 5.0
