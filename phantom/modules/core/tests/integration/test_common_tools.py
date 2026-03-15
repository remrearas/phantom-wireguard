"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

CommonTools Component Integration Tests

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from textwrap import dedent
from unittest.mock import Mock, patch

from phantom.models.base import CommandResult
from phantom.modules.core.lib.common_tools import CommonTools
from phantom.api.exceptions import InvalidClientNameError, ConfigurationError


class TestCommonTools:

    @pytest.mark.integration
    def test_name_validation(self):
        """Test client name validation with various valid and invalid inputs."""
        # Setup CommonTools with minimal config
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test valid names
        valid_names = [
            "user1",
            "test-user",
            "test_user",
            "User123",
            "a",
            "a" * 50  # Maximum length (50 chars)
        ]

        for name in valid_names:
            try:
                tools.ensure_name_is_valid(name)
            except InvalidClientNameError:
                pytest.fail(f"Valid name '{name}' should not raise exception")

        # Test empty name validation
        with pytest.raises(InvalidClientNameError) as exc_info:
            tools.ensure_name_is_valid("")
        assert "cannot be empty" in str(exc_info.value)

        # Test names with invalid characters
        invalid_chars_names = [
            "user@test",     # @ symbol
            "user#1",        # # symbol
            "user$",         # $ symbol
            "user%test",     # % symbol
            "user&co",       # & symbol
            "user*star",     # * symbol
            "user(test)",    # Parentheses
            "user.com",      # Dot
            "../etc/passwd", # Path traversal attempt
            "user/test",     # Forward slash
            "user\\test",    # Backslash
        ]

        for name in invalid_chars_names:
            with pytest.raises(InvalidClientNameError) as exc_info:
                tools.ensure_name_is_valid(name)
            assert "invalid characters" in str(exc_info.value)

        # Test name length limit (>50 chars)
        with pytest.raises(InvalidClientNameError) as exc_info:
            tools.ensure_name_is_valid("a" * 51)
        assert "too long" in str(exc_info.value)

        # Test name with space
        with pytest.raises(InvalidClientNameError) as exc_info:
            tools.ensure_name_is_valid("user name")
        assert "invalid characters" in str(exc_info.value)

    @pytest.mark.integration
    def test_response_formatting(self):
        """Test API response formatting for success and error cases."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test success response without message
        data = {"client": "test", "ip": "10.8.0.2"}
        response = tools.create_success_response(data)

        assert response["success"] is True
        assert response["data"] == data
        assert response.get("message") is None

        # Test success response with message
        response = tools.create_success_response(data, "Client added successfully")

        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "Client added successfully"

        # Test error response with default code
        response = tools.create_error_response("Something went wrong")

        assert response["success"] is False
        assert response["error"] == "Something went wrong"
        assert response["code"] == "ERROR"

        # Test error response with custom code
        response = tools.create_error_response("Client not found", "NOT_FOUND")

        assert response["success"] is False
        assert response["error"] == "Client not found"
        assert response["code"] == "NOT_FOUND"

        # Verify response structure keys
        success_keys = set(tools.create_success_response({}).keys())
        assert "success" in success_keys
        assert "data" in success_keys
        error_keys = set(tools.create_error_response("").keys())
        assert error_keys == {"success", "error", "code"}

    @pytest.mark.integration
    def test_server_public_key_retrieval(self):
        """Test server public key retrieval from config or generation from private key."""
        run_command = Mock()

        # Test 1: Public key exists in config
        config = {
            "server": {
                "public_key": "validPublicKey12345678901234567890123456789="
            }
        }
        tools = CommonTools(config, run_command)

        key = tools.retrieve_server_public_key()
        assert key == "validPublicKey12345678901234567890123456789="

        # Test 2: Generate public key from private key
        config = {
            "server": {
                "public_key": "",  # Empty public key
                "private_key": "privateKey123456789012345678901234567890123="
            }
        }

        # Mock successful wg pubkey command
        mock_result = CommandResult(
            success=True,
            returncode=0,
            stdout="generatedPublicKey12345678901234567890123456=\n",
            stderr=""
        )

        run_command_mock = Mock(return_value=mock_result)
        tools = CommonTools(config, run_command_mock)

        key = tools.retrieve_server_public_key()
        assert key == "generatedPublicKey12345678901234567890123456="

        # Verify correct command was called
        run_command_mock.assert_called_once_with(
            ["wg", "pubkey"],
            input="privateKey123456789012345678901234567890123=",
            capture_output=True,
            text=True
        )

        # Test 3: Failed key generation
        config = {
            "server": {
                "public_key": "",
                "private_key": "privateKey123456789012345678901234567890123="
            }
        }

        # Mock failed wg pubkey command
        failed_result = CommandResult(
            success=False,
            returncode=1,
            stdout="",
            stderr="wg: error"
        )

        run_command_fail = Mock(return_value=failed_result)
        tools = CommonTools(config, run_command_fail)

        with pytest.raises(ConfigurationError) as exc_info:
            tools.retrieve_server_public_key()
        assert "not found" in str(exc_info.value)

        # Test 4: Missing both public and private key
        config = {"server": {}}
        tools = CommonTools(config, run_command)

        with pytest.raises(ConfigurationError) as exc_info:
            tools.retrieve_server_public_key()
        assert "not found" in str(exc_info.value)

    @pytest.mark.integration
    def test_bandwidth_parsing(self):
        """Test bandwidth string parsing to bytes conversion for various units."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test binary units (KiB, MiB, GiB, TiB)
        assert tools.parse_bandwidth_to_bytes("100 B") == 100
        assert tools.parse_bandwidth_to_bytes("1 KiB") == 1024
        assert tools.parse_bandwidth_to_bytes("1 MiB") == 1024 * 1024
        assert tools.parse_bandwidth_to_bytes("1 GiB") == 1024 * 1024 * 1024
        assert tools.parse_bandwidth_to_bytes("1 TiB") == 1024 * 1024 * 1024 * 1024

        # Test decimal values
        assert tools.parse_bandwidth_to_bytes("1.5 GiB") == int(1.5 * 1024 * 1024 * 1024)
        assert tools.parse_bandwidth_to_bytes("2.75 MiB") == int(2.75 * 1024 * 1024)
        assert tools.parse_bandwidth_to_bytes("0.5 KiB") == 512

        # Test decimal units (KB, MB, GB, TB)
        assert tools.parse_bandwidth_to_bytes("1 KB") == 1000
        assert tools.parse_bandwidth_to_bytes("1 MB") == 1000 * 1000
        assert tools.parse_bandwidth_to_bytes("1 GB") == 1000 * 1000 * 1000
        assert tools.parse_bandwidth_to_bytes("1 TB") == 1000 * 1000 * 1000 * 1000

        # Test invalid inputs
        assert tools.parse_bandwidth_to_bytes("invalid") == 0
        assert tools.parse_bandwidth_to_bytes("") == 0
        assert tools.parse_bandwidth_to_bytes("100") == 0  # No unit
        assert tools.parse_bandwidth_to_bytes("XYZ") == 0

        # Test case insensitivity and whitespace handling
        assert tools.parse_bandwidth_to_bytes("1 kib") == 1024
        assert tools.parse_bandwidth_to_bytes("1 Kib") == 1024
        assert tools.parse_bandwidth_to_bytes("  1  GiB  ") == 1024 * 1024 * 1024

    @pytest.mark.integration
    def test_transfer_data_parsing(self):
        """Test WireGuard transfer data string parsing to bytes and formatted strings."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test standard transfer data
        result = tools.parse_wg_transfer_data("38.02 MiB received, 6.41 MiB sent")

        assert result["received"] == "38.02 MiB"
        assert result["sent"] == "6.41 MiB"
        assert result["received_bytes"] == int(38.02 * 1024 * 1024)
        assert result["sent_bytes"] == int(6.41 * 1024 * 1024)

        # Test mixed units
        result = tools.parse_wg_transfer_data("100 B received, 2 KiB sent")

        assert result["received"] == "100 B"
        assert result["sent"] == "2 KiB"
        assert result["received_bytes"] == 100
        assert result["sent_bytes"] == 2048

        # Test zero transfer
        result = tools.parse_wg_transfer_data("0 B received, 0 B sent")

        assert result["received"] == "0 B"
        assert result["sent"] == "0 B"
        assert result["received_bytes"] == 0
        assert result["sent_bytes"] == 0

        # Test invalid format
        result = tools.parse_wg_transfer_data("invalid transfer data")

        assert result["received"] == "0 B"
        assert result["sent"] == "0 B"
        assert result["received_bytes"] == 0
        assert result["sent_bytes"] == 0

        # Test large values
        result = tools.parse_wg_transfer_data("1.5 TiB received, 2.3 GiB sent")

        assert result["received"] == "1.5 TiB"
        assert result["sent"] == "2.3 GiB"
        assert result["received_bytes"] == int(1.5 * 1024 * 1024 * 1024 * 1024)
        assert result["sent_bytes"] == int(2.3 * 1024 * 1024 * 1024)

    @pytest.mark.integration
    def test_wg_show_output_parsing(self):
        """Test parsing of 'wg show' command output into structured data."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test 1: Parse complete wg show output with interface and peer
        simple_output = dedent("""
            interface: wg_main
              public key: serverPublicKey123456789012345678901234567890=
              private key: (hidden)
              listening port: 51820

            peer: clientPublicKey1234567890123456789012345678901=
              preshared key: (hidden)
              endpoint: 192.168.1.100:51820
              allowed ips: 10.8.0.2/32
              latest handshake: 1 minute, 23 seconds ago
              transfer: 38.02 MiB received, 6.41 MiB sent
        """).strip()

        result = tools.parse_wg_show_output(simple_output)

        # Verify interface parsing
        assert result["interface"]["name"] == "wg_main"
        assert result["interface"]["public_key"] == "serverPublicKey123456789012345678901234567890="
        assert result["interface"]["private_key"] == "(hidden)"
        assert result["interface"]["listening_port"] == 51820

        # Verify peer parsing
        assert len(result["peers"]) == 1
        peer = result["peers"][0]
        assert peer["public_key"] == "clientPublicKey1234567890123456789012345678901="
        assert peer["preshared_key"] == "(hidden)"
        assert peer["endpoint"] == "192.168.1.100:51820"
        assert peer["allowed_ips"] == "10.8.0.2/32"
        assert peer["latest_handshake"] == "1 minute, 23 seconds ago"
        assert peer["transfer"]["received"] == "38.02 MiB"
        assert peer["transfer"]["sent"] == "6.41 MiB"

        # Test 2: Parse output with multiple peers
        multi_output = dedent("""
            interface: wg_main
              public key: serverKey
              listening port: 51820

            peer: peer1Key
              allowed ips: 10.8.0.2/32
              transfer: 1 GiB received, 500 MiB sent

            peer: peer2Key
              allowed ips: 10.8.0.3/32
              transfer: 2 GiB received, 1 GiB sent
        """).strip()

        result = tools.parse_wg_show_output(multi_output)

        assert len(result["peers"]) == 2
        assert result["peers"][0]["public_key"] == "peer1Key"
        assert result["peers"][1]["public_key"] == "peer2Key"

        # Test 3: Parse empty output
        result = tools.parse_wg_show_output("")

        assert result["interface"] == {}
        assert result["peers"] == []

        # Test 4: Parse invalid output
        result = tools.parse_wg_show_output("invalid wg output format")

        assert isinstance(result["interface"], dict)
        assert isinstance(result["peers"], list)

        # Test 5: Parse output with endpoint information
        endpoint_output = dedent("""
            interface: wg_main
              listening port: 51820

            peer: testPeer
              endpoint: 203.0.113.1:12345
              allowed ips: 10.8.0.5/32
        """).strip()

        result = tools.parse_wg_show_output(endpoint_output)

        assert result["peers"][0]["endpoint"] == "203.0.113.1:12345"

    @pytest.mark.integration
    def test_edge_cases(self):
        """Test edge cases and boundary conditions for various parsing functions."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test empty string bandwidth parsing
        assert tools.parse_bandwidth_to_bytes("") == 0

        # Test extremely large bandwidth value
        result = tools.parse_bandwidth_to_bytes("999999.99 TiB")
        assert result > 0

        # Test Unicode characters in client names
        with pytest.raises(InvalidClientNameError):
            tools.ensure_name_is_valid("用户")  # Chinese characters

        with pytest.raises(InvalidClientNameError):
            tools.ensure_name_is_valid("пользователь")  # Cyrillic characters

        with pytest.raises(InvalidClientNameError):
            tools.ensure_name_is_valid("user😀")  # Emoji

        # Test negative bandwidth value
        result = tools.parse_bandwidth_to_bytes("-1 GiB")
        assert result < 0

        # Test scientific notation
        result = tools.parse_bandwidth_to_bytes("1e3 B")
        assert result == 1000

        # Test comma in transfer data (should fail)
        result = tools.parse_wg_transfer_data("1,234.56 MiB received, 789.01 KiB sent")
        assert result["received_bytes"] == 0  # Comma not supported

    @pytest.mark.integration
    def test_exception_coverage(self):
        """Test exception handling and edge cases for coverage completeness."""
        # Setup CommonTools
        config = {"server": {"public_key": "test_key"}}
        run_command = Mock()
        tools = CommonTools(config, run_command)

        # Test configuration error when generating public key fails
        config_with_private = {
            "server": {
                "public_key": "",
                "private_key": "privateKey123="
            }
        }

        error_result = CommandResult(
            success=False,
            returncode=127,
            stdout="",
            stderr="Command not found",
            error="Command not found"
        )

        run_command_error = Mock(return_value=error_result)
        tools_with_private = CommonTools(config_with_private, run_command_error)

        with pytest.raises(ConfigurationError):
            tools_with_private.retrieve_server_public_key()

        # Test None input handling (should return 0)
        # noinspection PyTypeChecker
        assert tools.parse_bandwidth_to_bytes(None) == 0

        # Test integer input handling (should return 0)
        # noinspection PyTypeChecker
        assert tools.parse_bandwidth_to_bytes(123) == 0

        # Test internal method error handling with logging
        import logging
        with patch.object(logging, 'getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            # Test None input to internal transfer data method
            # noinspection PyTypeChecker
            result = tools._parse_wg_transfer_data_typed(None)
            assert result.received == "0 B"
            assert result.sent == "0 B"
            mock_log.warning.assert_called_once()

        # Test invalid object handling in wg_show_output parsing
        with patch.object(logging, 'getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            # Create mock object that raises AttributeError
            invalid_output = Mock()
            invalid_output.strip.side_effect = AttributeError("Invalid object")

            result = tools._parse_wg_show_output_typed(invalid_output)
            assert result.interface == {}
            assert result.peers == []
            mock_log.error.assert_called_once()

        # Test invalid port parsing (non-numeric port)
        wg_output = dedent("""
            interface: wg_main
              public key: pubkey123
              listening port: invalid_port
        """).strip()
        result = tools.parse_wg_show_output(wg_output)
        assert result["interface"]["listening_port"] == 0  # Defaults to 0 for invalid port

        # Test key-value line parsing without colon
        key, value = tools._parse_key_value_line("no colon here")
        assert key == ""
        assert value == ""
