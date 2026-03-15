"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Unit tests for phantom.api.validators module

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from textwrap import dedent
from phantom.api.validators import (
    Validator,
    ClientValidator,
    NetworkValidator,
    DNSValidator,
    FileValidator,
    ConfigValidator
)
from phantom.api.exceptions import ValidationError, InvalidParameterError


class TestValidator:

    def test_validate_required_with_valid_value(self):
        assert Validator.validate_required("test", "field") == "test"
        assert Validator.validate_required(123, "field") == 123
        assert Validator.validate_required(["item"], "field") == ["item"]

    def test_validate_required_with_none(self):
        with pytest.raises(ValidationError) as exc_info:
            Validator.validate_required(None, "field")
        assert "'field' is required" in str(exc_info.value)

    def test_validate_required_with_empty_string(self):
        with pytest.raises(ValidationError) as exc_info:
            Validator.validate_required("", "field")
        assert "'field' is required" in str(exc_info.value)

    def test_validate_required_with_whitespace_string(self):
        with pytest.raises(ValidationError) as exc_info:
            Validator.validate_required("   ", "field")
        assert "'field' is required" in str(exc_info.value)

    def test_validate_type_with_correct_type(self):
        assert Validator.validate_type("test", str, "field") == "test"
        assert Validator.validate_type(123, int, "field") == 123
        assert Validator.validate_type([], list, "field") == []

    def test_validate_type_with_wrong_type(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            Validator.validate_type("test", int, "field")
        assert "field" in str(exc_info.value)


class TestClientValidator:

    def test_validate_client_name_valid(self):
        assert ClientValidator.validate_client_name("test-client") == "test-client"
        assert ClientValidator.validate_client_name("user_123") == "user_123"
        assert ClientValidator.validate_client_name("john-laptop") == "john-laptop"

    def test_validate_client_name_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            ClientValidator.validate_client_name("")
        assert "'client_name' is required" in str(exc_info.value)

    def test_validate_client_name_too_short(self):
        # No minimum length enforced currently
        assert ClientValidator.validate_client_name("ab") == "ab"
        assert ClientValidator.validate_client_name("a") == "a"

    def test_validate_client_name_too_long(self):
        max_length = getattr(ClientValidator, 'MAX_CLIENT_NAME_LENGTH', 50)
        long_name = "a" * (max_length + 1)
        with pytest.raises(InvalidParameterError) as exc_info:
            ClientValidator.validate_client_name(long_name)
        assert "characters or less" in str(exc_info.value)

    def test_validate_client_name_invalid_chars(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            ClientValidator.validate_client_name("test@client")
        assert "can only contain letters, numbers, dashes, and underscores" in str(exc_info.value)

    def test_validate_client_name_reserved(self):
        reserved_names = ["server", "admin", "root", "system", "ghost", "multihop"]
        for name in reserved_names:
            with pytest.raises(InvalidParameterError) as exc_info:
                ClientValidator.validate_client_name(name)
            assert "reserved name" in str(exc_info.value)


class TestNetworkValidator:

    def test_validate_ip_address_ipv4(self):
        assert NetworkValidator.validate_ip_address("192.168.1.1") == "192.168.1.1"
        assert NetworkValidator.validate_ip_address("10.0.0.1", version=4) == "10.0.0.1"

    def test_validate_ip_address_ipv6(self):
        assert NetworkValidator.validate_ip_address("::1", version=6) == "::1"
        result = NetworkValidator.validate_ip_address("2001:db8::1", version=6)
        assert result == "2001:db8::1"

    def test_validate_ip_address_invalid(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_ip_address("999.999.999.999")
        assert "Invalid IP address" in str(exc_info.value)

    def test_validate_ip_address_wrong_version(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_ip_address("192.168.1.1", version=6)
        assert "IPv6 address required" in str(exc_info.value)

    def test_validate_ip_address_ipv6_with_ipv4_required(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_ip_address("2001:db8::1", version=4)
        assert "IPv4 address required" in str(exc_info.value)

    def test_validate_ip_address_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            NetworkValidator.validate_ip_address("")
        assert "'ip_address' is required" in str(exc_info.value)

    def test_validate_network_valid(self):
        assert NetworkValidator.validate_network("10.0.0.0/24") == "10.0.0.0/24"
        assert NetworkValidator.validate_network("192.168.1.0/28") == "192.168.1.0/28"

    def test_validate_network_invalid_format(self):
        # Automatically adds /32 for IP without prefix
        result = NetworkValidator.validate_network("10.0.0.0")
        assert result == "10.0.0.0/32"

    def test_validate_network_invalid_prefix(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_network("10.0.0.0/33")
        assert "Invalid network" in str(exc_info.value)

    def test_validate_network_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            NetworkValidator.validate_network("")
        assert "'network' is required" in str(exc_info.value)

    def test_validate_port_valid(self):
        assert NetworkValidator.validate_port(8080) == 8080
        assert NetworkValidator.validate_port(443) == 443
        assert NetworkValidator.validate_port(1) == 1
        assert NetworkValidator.validate_port(65535) == 65535

    def test_validate_port_zero(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_port(0)
        assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_validate_port_too_large(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_port(70000)
        assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_validate_port_not_integer(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_port("8080")  # type: ignore
        assert "Port must be an integer" in str(exc_info.value)

    def test_validate_domain_valid(self):
        assert NetworkValidator.validate_domain("example.com") == "example.com"
        assert NetworkValidator.validate_domain("SUB.DOMAIN.EXAMPLE.COM") == "sub.domain.example.com"

    def test_validate_domain_invalid(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            NetworkValidator.validate_domain("invalid_domain")
        assert "Invalid domain name format" in str(exc_info.value)

    def test_validate_domain_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            NetworkValidator.validate_domain("")
        assert "'domain' is required" in str(exc_info.value)


class TestDNSValidator:

    def test_validate_dns_servers_valid(self):
        servers = ["8.8.8.8", "1.1.1.1"]
        assert DNSValidator.validate_dns_servers(servers) == servers

    def test_validate_dns_servers_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            DNSValidator.validate_dns_servers([])
        assert "At least one DNS server is required" in str(exc_info.value)

    def test_validate_dns_servers_not_list(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            DNSValidator.validate_dns_servers("8.8.8.8")  # type: ignore
        assert "DNS servers must be provided as a list" in str(exc_info.value)

    def test_validate_dns_servers_invalid_ip(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            DNSValidator.validate_dns_servers(["999.999.999.999"])
        assert "Invalid IP address" in str(exc_info.value)

    def test_validate_dns_servers_multiple(self):
        servers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        result = DNSValidator.validate_dns_servers(servers)
        assert len(result) == 3
        assert result == servers


class TestFileValidator:

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_validate_file_path_exists(self, mock_is_file, mock_exists):
        mock_exists.return_value = True
        mock_is_file.return_value = True
        result = FileValidator.validate_file_path("/path/to/file.txt")
        assert str(result) == "/path/to/file.txt"
        assert isinstance(result, Path)

    @patch('pathlib.Path.exists')
    def test_validate_file_path_not_exists(self, mock_exists):
        mock_exists.return_value = False
        with pytest.raises(InvalidParameterError) as exc_info:
            FileValidator.validate_file_path("/path/to/missing.txt")
        assert "File not found" in str(exc_info.value)

    @patch('pathlib.Path.exists')
    def test_validate_file_path_not_required_to_exist(self, mock_exists):
        mock_exists.return_value = False
        result = FileValidator.validate_file_path("/path/to/new.txt", must_exist=False)
        assert str(result) == "/path/to/new.txt"

    def test_validate_file_path_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            FileValidator.validate_file_path("")
        assert "'file_path' is required" in str(exc_info.value)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_validate_file_path_is_directory(self, mock_is_file, mock_exists):
        mock_exists.return_value = True
        mock_is_file.return_value = False
        with pytest.raises(InvalidParameterError) as exc_info:
            FileValidator.validate_file_path("/path/to/dir")
        assert "Not a file" in str(exc_info.value)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_directory_exists(self, mock_is_dir, mock_exists):
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        result = FileValidator.validate_directory("/path/to/dir")
        assert str(result) == "/path/to/dir"
        assert isinstance(result, Path)

    @patch('pathlib.Path.exists')
    def test_validate_directory_not_exists(self, mock_exists):
        mock_exists.return_value = False
        with pytest.raises(InvalidParameterError) as exc_info:
            FileValidator.validate_directory("/path/to/missing")
        assert "Directory not found" in str(exc_info.value)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_directory_is_file(self, mock_is_dir, mock_exists):
        mock_exists.return_value = True
        mock_is_dir.return_value = False
        with pytest.raises(InvalidParameterError) as exc_info:
            FileValidator.validate_directory("/path/to/file.txt")
        assert "Not a directory" in str(exc_info.value)

    def test_validate_directory_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            FileValidator.validate_directory("")
        assert "'directory_path' is required" in str(exc_info.value)


class TestConfigValidator:

    def test_validate_wg_config_valid(self):
        config = dedent("""[Interface]
            PrivateKey = abc123
            Address = 10.0.0.1/24
            ListenPort = 51820

            [Peer]
            PublicKey = xyz789
            AllowedIPs = 10.0.0.2/32""")
        assert ConfigValidator.validate_wg_config(config) == config

    def test_validate_wg_config_no_interface(self):
        config = dedent("""[Peer]
            PublicKey = xyz789""")
        with pytest.raises(InvalidParameterError) as exc_info:
            ConfigValidator.validate_wg_config(config)
        assert "Missing [Interface] section" in str(exc_info.value)

    def test_validate_wg_config_no_private_key(self):
        config = dedent("""[Interface]
            Address = 10.0.0.1/24""")
        with pytest.raises(InvalidParameterError) as exc_info:
            ConfigValidator.validate_wg_config(config)
        assert "Missing PrivateKey" in str(exc_info.value)

    def test_validate_wg_config_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            ConfigValidator.validate_wg_config("")
        assert "'config_content' is required" in str(exc_info.value)

    def test_validate_boolean_true_values(self):
        assert ConfigValidator.validate_boolean(True, "field") is True
        assert ConfigValidator.validate_boolean("true", "field") is True
        assert ConfigValidator.validate_boolean("True", "field") is True
        assert ConfigValidator.validate_boolean("yes", "field") is True
        assert ConfigValidator.validate_boolean("1", "field") is True
        assert ConfigValidator.validate_boolean("on", "field") is True

    def test_validate_boolean_false_values(self):
        assert ConfigValidator.validate_boolean(False, "field") is False
        assert ConfigValidator.validate_boolean("false", "field") is False
        assert ConfigValidator.validate_boolean("False", "field") is False
        assert ConfigValidator.validate_boolean("no", "field") is False
        assert ConfigValidator.validate_boolean("0", "field") is False
        assert ConfigValidator.validate_boolean("off", "field") is False

    def test_validate_boolean_invalid(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            ConfigValidator.validate_boolean("invalid", "field")
        assert "must be a boolean value" in str(exc_info.value)

    def test_validate_boolean_integer(self):
        # Integer values not supported
        with pytest.raises(InvalidParameterError) as exc_info:
            ConfigValidator.validate_boolean(1, "field")
        assert "must be a boolean value" in str(exc_info.value)
