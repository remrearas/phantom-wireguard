"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Unit tests for phantom.api.exceptions module

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from phantom.api.exceptions import (
    PhantomException,
    ConfigurationError,
    ConfigNotFoundError,
    ClientError,
    ClientExistsError,
    ClientNotFoundError,
    InvalidClientNameError,
    ServiceError,
    ServiceNotRunningError,
    ServiceOperationError,
    NetworkError,
    IPAllocationError,
    PortInUseError,
    ModuleError,
    PhantomModuleNotFoundError,
    ActionNotFoundError,
    ValidationError,
    MissingParameterError,
    InvalidParameterError,
    PhantomPermissionError,
    InsufficientPrivilegesError,
    GhostModeError,
    GhostModeActiveError,
    CertificateError,
    MultihopError,
    VPNConfigError,
    ExitNodeError,
    InternalError
)


class TestPhantomException:

    def test_init_with_message_only(self):

        exc = PhantomException(message="Test error message")
        assert exc.code == "PHANTOM_ERROR"
        assert exc.status_code == 500
        assert exc.message == "Test error message"
        assert exc.data is None
        assert str(exc) == "Test error message"

    def test_init_with_message_and_data(self):

        exc = PhantomException(
            message="Custom error message",
            data={"key": "value"}
        )
        assert exc.code == "PHANTOM_ERROR"
        assert exc.status_code == 500
        assert exc.message == "Custom error message"
        assert exc.data == {"key": "value"}
        assert str(exc) == "Custom error message"

    def test_to_dict_without_data(self):

        exc = PhantomException(message="Test error message")
        result = exc.to_dict()

        assert result == {
            "error": "Test error message",
            "code": "PHANTOM_ERROR"
        }

        # No data field when None
        assert "data" not in result

    def test_to_dict_with_data(self):

        test_data = {
            "field1": "value1",
            "field2": 42,
            "field3": ["item1", "item2"]
        }

        exc = PhantomException(
            message="Error with data",
            data=test_data
        )
        result = exc.to_dict()

        assert result == {
            "error": "Error with data",
            "code": "PHANTOM_ERROR",
            "data": test_data
        }

        assert "data" in result
        assert result["data"] == test_data

    def test_to_dict_with_empty_data(self):

        exc = PhantomException(
            message="Error with empty data",
            data={}
        )
        result = exc.to_dict()

        assert result == {
            "error": "Error with empty data",
            "code": "PHANTOM_ERROR"
        }
        assert "data" not in result

    def test_to_dict_with_various_data_types(self):
        # Test various data types to ensure only truthy values are included
        test_cases = [
            (None, False),
            ({}, False),
            ([], False),
            ("", False),
            (0, False),
            (False, False),
            ({"key": "value"}, True),
            ([1, 2, 3], True),
            ("non-empty string", True),
            (42, True),
            (True, True),
        ]

        for data, should_include in test_cases:
            exc = PhantomException(
                message="Test",
                data=data
            )
            result = exc.to_dict()

            if should_include:
                assert "data" in result
                assert result["data"] == data
            else:
                assert "data" not in result

    def test_to_dict_preserves_complex_data_structure(self):

        complex_data = {
            "client": {
                "name": "test_client",
                "ip": "10.0.0.2",
                "public_key": "abc123"
            },
            "interface": {
                "name": "wg0",
                "port": 51820,
                "active": True
            },
            "errors": [
                {"code": "E001", "msg": "Error 1"},
                {"code": "E002", "msg": "Error 2"}
            ],
            "metadata": {
                "timestamp": "2025-01-01T12:00:00",
                "version": "1.0.0"
            }
        }

        exc = PhantomException(
            message="Complex error",
            data=complex_data
        )
        result = exc.to_dict()

        assert result["data"] == complex_data
        assert result["data"]["client"]["ip"] == "10.0.0.2"
        assert result["data"]["errors"][0]["code"] == "E001"
        assert result["data"]["metadata"]["version"] == "1.0.0"


class TestConfigurationErrors:

    def test_configuration_error(self):
        exc = ConfigurationError(message="Configuration error")
        assert exc.code == "CONFIG_ERROR"
        assert exc.status_code == 500
        result = exc.to_dict()
        assert result["code"] == "CONFIG_ERROR"

    def test_config_not_found_error(self):
        exc = ConfigNotFoundError(message="Config not found")
        assert exc.code == "CONFIG_NOT_FOUND"
        assert exc.status_code == 404
        result = exc.to_dict()
        assert result["code"] == "CONFIG_NOT_FOUND"


class TestClientErrors:

    def test_client_error(self):
        exc = ClientError(message="Client error")
        assert exc.code == "CLIENT_ERROR"
        assert exc.status_code == 400
        result = exc.to_dict()
        assert result["code"] == "CLIENT_ERROR"

    def test_client_exists_error(self):
        exc = ClientExistsError(message="Client exists")
        assert exc.code == "CLIENT_EXISTS"
        assert exc.status_code == 409
        exc_with_data = ClientExistsError(
            message="Client already exists",
            data={"client_name": "test_client"}
        )
        result = exc_with_data.to_dict()
        assert result["data"]["client_name"] == "test_client"

    def test_client_not_found_error(self):
        exc = ClientNotFoundError(message="Client not found")
        assert exc.code == "CLIENT_NOT_FOUND"
        assert exc.status_code == 404

    def test_invalid_client_name_error(self):
        exc = InvalidClientNameError(message="Invalid client name")
        assert exc.code == "INVALID_CLIENT_NAME"
        assert exc.status_code == 400


class TestServiceErrors:

    def test_service_error(self):
        exc = ServiceError(message="Service error")
        assert exc.code == "SERVICE_ERROR"

    def test_service_not_running_error(self):
        exc = ServiceNotRunningError(message="Service not running")
        assert exc.code == "SERVICE_NOT_RUNNING"

    def test_service_operation_error(self):
        exc = ServiceOperationError(message="Service operation error")
        assert exc.code == "SERVICE_OPERATION_FAILED"


class TestNetworkErrors:

    def test_network_error(self):
        exc = NetworkError(message="Network error")
        assert exc.code == "NETWORK_ERROR"

    def test_ip_allocation_error(self):
        exc = IPAllocationError(message="IP allocation error")
        assert exc.code == "IP_ALLOCATION_ERROR"

    def test_port_in_use_error(self):
        exc = PortInUseError(message="Port in use")
        assert exc.code == "PORT_IN_USE"


class TestModuleErrors:

    def test_module_error(self):
        exc = ModuleError(message="Module error")
        assert exc.code == "MODULE_ERROR"

    def test_phantom_module_not_found_error(self):
        exc = PhantomModuleNotFoundError(message="Module not found")
        assert exc.code == "MODULE_NOT_FOUND"

    def test_action_not_found_error(self):
        exc = ActionNotFoundError(message="Action not found")
        assert exc.code == "ACTION_NOT_FOUND"


class TestValidationErrors:

    def test_validation_error(self):
        exc = ValidationError(message="Validation error")
        assert exc.code == "VALIDATION_ERROR"

    def test_missing_parameter_error(self):
        exc = MissingParameterError(message="Missing parameter")
        assert exc.code == "MISSING_PARAMETER"

    def test_invalid_parameter_error(self):
        exc = InvalidParameterError(message="Invalid parameter")
        assert exc.code == "INVALID_PARAMETER"


class TestPermissionErrors:

    def test_phantom_permission_error(self):
        exc = PhantomPermissionError(message="Permission error")
        assert exc.code == "PERMISSION_ERROR"

    def test_insufficient_privileges_error(self):
        exc = InsufficientPrivilegesError(message="Insufficient privileges")
        assert exc.code == "INSUFFICIENT_PRIVILEGES"


class TestGhostModeErrors:

    def test_ghost_mode_error(self):
        exc = GhostModeError(message="Ghost mode error")
        assert exc.code == "GHOST_MODE_ERROR"

    def test_ghost_mode_active_error(self):
        exc = GhostModeActiveError(message="Ghost mode active")
        assert exc.code == "GHOST_MODE_ACTIVE"

    def test_certificate_error(self):
        exc = CertificateError(message="Certificate error")
        assert exc.code == "CERTIFICATE_ERROR"


class TestMultihopErrors:

    def test_multihop_error(self):
        exc = MultihopError(message="Multihop error")
        assert exc.code == "MULTIHOP_ERROR"

    def test_vpn_config_error(self):
        exc = VPNConfigError(message="VPN config error")
        assert exc.code == "VPN_CONFIG_ERROR"

    def test_exit_node_error(self):
        exc = ExitNodeError(message="Exit node error")
        assert exc.code == "EXIT_NODE_ERROR"


class TestInternalError:

    def test_internal_error(self):
        exc = InternalError(message="Internal error")
        assert exc.code == "INTERNAL_ERROR"
