"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Key Generator Docker Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from unittest.mock import Mock

from phantom.models.base import CommandResult
from phantom.modules.core.tests.helpers.command_executor import CommandExecutor
from phantom.modules.core.tests.helpers.docker_test_helper import DockerCommandExecutor
from phantom.api.exceptions import ServiceOperationError

from phantom.modules.core.lib.key_generator import KeyGenerator


class TestKeyGeneratorDocker:

    @pytest.fixture
    def docker_executor(self, shared_docker_container):
        """Provide Docker command executor for test execution in container."""
        # Create Docker executor with shared container
        executor = DockerCommandExecutor(shared_docker_container)
        executor.container = shared_docker_container
        return executor

    @pytest.fixture
    def command_executor(self, docker_executor):
        """Provide command executor that runs commands in Docker container."""
        # Wrap Docker executor with CommandExecutor interface
        return CommandExecutor(docker_executor)

    @pytest.fixture
    def key_generator(self, command_executor):
        """Provide KeyGenerator instance with Docker-based command execution."""
        # Initialize KeyGenerator with Docker command executor
        return KeyGenerator(run_command=command_executor.run_command)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_create_private_key(self, key_generator):
        """Test WireGuard private key generation in Docker container."""
        # Generate a private key using WireGuard tools in container
        private_key = key_generator._generate_private_key()

        # Verify key is a valid string
        assert isinstance(private_key, str)
        # Verify key has correct base64 length (44 characters)
        assert len(private_key) == 44
        # Verify key has no extra whitespace
        assert private_key == private_key.strip()

    @pytest.mark.docker
    @pytest.mark.integration
    def test_derive_public_key(self, key_generator):
        """Test public key derivation from private key in Docker container."""
        # First generate a private key
        private_key = key_generator.create_private_key()

        # Derive public key from the private key
        public_key = key_generator._generate_public_key(private_key)

        # Verify public key is a valid string
        assert isinstance(public_key, str)
        # Verify public key has correct base64 length (44 characters)
        assert len(public_key) == 44
        # Verify public key has no extra whitespace
        assert public_key == public_key.strip()

    @pytest.mark.docker
    @pytest.mark.integration
    def test_create_preshared_key(self, key_generator):
        """Test WireGuard preshared key generation in Docker container."""
        # Generate a preshared key for additional security
        preshared_key = key_generator._generate_preshared_key()

        # Verify preshared key is a valid string
        assert isinstance(preshared_key, str)
        # Verify preshared key has correct base64 length (44 characters)
        assert len(preshared_key) == 44
        # Verify preshared key has no extra whitespace
        assert preshared_key == preshared_key.strip()

    @pytest.mark.docker
    @pytest.mark.integration
    def test_private_key_generation_failure(self):
        """Test error handling when private key generation fails."""
        # Mock a failed command execution (e.g., wg tool not found)
        mock_run_command = Mock(return_value=CommandResult(**{
            "success": False,
            "stdout": "",
            "stderr": "wg: command not found"
        }))

        # Create generator with mocked command that will fail
        generator = KeyGenerator(run_command=mock_run_command)

        # Verify appropriate error is raised when generation fails
        with pytest.raises(ServiceOperationError) as exc_info:
            generator.create_private_key()

        # Verify error message indicates key generation failure
        assert "Failed to generate private key" in str(exc_info.value)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_public_key_derivation_failure(self):
        """Test error handling when public key derivation fails."""
        # Mock a failed public key derivation (e.g., invalid private key)
        mock_run_command = Mock(return_value=CommandResult(**{
            "returncode": -1,
            "success": False,
            "stdout": "",
            "stderr": "Invalid key"
        }))

        # Create generator with mocked command that will fail
        generator = KeyGenerator(run_command=mock_run_command)

        # Verify appropriate error is raised when derivation fails
        with pytest.raises(ServiceOperationError) as exc_info:
            generator.derive_public_key("invalid_key")

        # Verify error message indicates public key generation failure
        assert "Failed to generate public key" in str(exc_info.value)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_preshared_key_generation_failure(self):
        """Test error handling when preshared key generation fails."""
        # Mock a failed preshared key generation (e.g., permission denied)
        mock_run_command = Mock(return_value=CommandResult(**{
            "success": False,
            "stdout": "",
            "stderr": "Permission denied"
        }))

        # Create generator with mocked command that will fail
        generator = KeyGenerator(mock_run_command)

        # Verify appropriate error is raised when generation fails
        with pytest.raises(ServiceOperationError) as exc_info:
            generator.create_preshared_key()

        # Verify error message indicates preshared key generation failure
        assert "Failed to generate preshared key" in str(exc_info.value)

    @pytest.mark.docker
    @pytest.mark.integration
    def test_edge_cases(self):
        """Test edge case handling for malformed key output."""
        # Mock a successful command but with invalid key format (extra characters)
        mock_run_command = Mock(return_value=CommandResult(**{
            "success": True,
            "stdout": "====" + 'mKetbh6COwAPQULUhvTqMocDNAFbOjEZS9+Ki03ZKnY=' + "====\n",
            "stderr": ""
        }))

        # Create generator with mocked command returning invalid key format
        generator = KeyGenerator(mock_run_command)

        # Verify error is raised for invalid key format despite successful command
        with pytest.raises(ServiceOperationError) as exc_info:
            generator.create_private_key()

        # Verify error message indicates key validation failure
        assert "appears to be invalid" in str(exc_info.value)
