"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Unit tests for phantom.api.response module

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import json
from unittest.mock import patch
from datetime import datetime

from phantom.api.response import APIResponse


class TestAPIResponse:

    def test_init_success_with_data(self):

        response = APIResponse(
            success=True,
            data={"result": "success"}
        )
        assert response.success is True
        assert response.data == {"result": "success"}
        assert response.error is None
        assert response.code is None
        assert response.metadata is not None

    def test_init_error_with_message(self):

        response = APIResponse(
            success=False,
            error="Something went wrong",
            code="ERROR_001",
            data={"details": "Additional info"}
        )
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.code == "ERROR_001"
        assert response.data == {"details": "Additional info"}

    def test_post_init_adds_metadata(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse(success=True)

            assert "timestamp" in response.metadata
            assert "version" in response.metadata
            assert response.metadata["version"] == '1.0.0'
            assert response.metadata["timestamp"].endswith('Z')

    def test_post_init_preserves_existing_metadata(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse(
                success=True,
                metadata={"module": "core", "action": "list_clients"}
            )

            assert response.metadata["module"] == "core"
            assert response.metadata["action"] == "list_clients"
            assert "timestamp" in response.metadata
            assert "version" in response.metadata

    def test_to_dict(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse(
                success=True,
                data={"clients": ["client1", "client2"]},
                metadata={"module": "core"}
            )

            result = response.to_dict()

            assert result["success"] is True
            assert result["data"] == {"clients": ["client1", "client2"]}
            assert "error" not in result
            assert "code" not in result
            assert result["metadata"]["module"] == "core"
            assert "timestamp" in result["metadata"]
            assert "version" in result["metadata"]

    def test_to_dict_with_error(self):

        response = APIResponse(
            success=False,
            error="Client not found",
            code="CLIENT_NOT_FOUND",
            data={"client_name": "test_client"}
        )

        result = response.to_dict()

        assert result["success"] is False
        assert result["error"] == "Client not found"
        assert result["code"] == "CLIENT_NOT_FOUND"
        assert result["data"] == {"client_name": "test_client"}

    def test_to_json(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse(
                success=True,
                data={"message": "Hello World"}
            )

            json_str = response.to_json()
            parsed = json.loads(json_str)

            assert parsed["success"] is True
            assert parsed["data"]["message"] == "Hello World"
            assert "metadata" in parsed

    def test_to_json_with_custom_indent(self):
        response = APIResponse(
            success=True,
            data={"test": "data"}
        )

        json_str = response.to_json(indent=4)
        parsed = json.loads(json_str)
        assert parsed["success"] is True

        lines = json_str.split('\n')
        # Find a line with indentation and check it has 4 spaces
        for line in lines:
            if line.startswith('    ') and not line.startswith('        '):
                assert line.startswith('    ')  # 4 spaces
                break

    def test_to_json_preserves_turkish_characters(self):

        response = APIResponse(
            success=True,
            data={"message": "Türkçe karakterler: ğüşıöç"}
        )

        json_str = response.to_json()
        assert "Türkçe karakterler: ğüşıöç" in json_str
        # Ensure Turkish chars are not escaped
        assert "\\u" not in json_str

    def test_success_response_classmethod(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse.success_response(
                data={"status": "healthy"},
                metadata={"endpoint": "health_check"}
            )

            assert response.success is True
            assert response.data == {"status": "healthy"}
            assert response.error is None
            assert response.code is None
            assert response.metadata["endpoint"] == "health_check"
            assert "timestamp" in response.metadata
            assert "version" in response.metadata

    def test_success_response_without_metadata(self):

        response = APIResponse.success_response(
            data=["item1", "item2", "item3"]
        )

        assert response.success is True
        assert response.data == ["item1", "item2", "item3"]
        assert response.metadata is not None  # Should have default metadata

    def test_error_response_classmethod(self):

        with patch('phantom.api.response.__version__', '1.0.0'):
            response = APIResponse.error_response(
                error="Invalid parameter",
                code="INVALID_PARAMETER",
                data={"parameter": "ip_address", "value": "invalid"},
                metadata={"module": "validation"}
            )

            assert response.success is False
            assert response.error == "Invalid parameter"
            assert response.code == "INVALID_PARAMETER"
            assert response.data == {"parameter": "ip_address", "value": "invalid"}
            assert response.metadata["module"] == "validation"

    def test_error_response_minimal(self):

        response = APIResponse.error_response(
            error="Service error",
            code="SERVICE_ERROR"
        )

        assert response.success is False
        assert response.error == "Service error"
        assert response.code == "SERVICE_ERROR"
        assert response.data is None
        assert response.metadata is not None  # Should have default metadata

    def test_str_method(self):

        response = APIResponse(
            success=True,
            data={"test": "data"}
        )

        str_repr = str(response)
        # Should be valid JSON
        parsed = json.loads(str_repr)
        assert parsed["success"] is True
        assert parsed["data"]["test"] == "data"

    def test_response_with_list_data(self):

        response = APIResponse(
            success=True,
            data=[
                {"id": 1, "name": "client1"},
                {"id": 2, "name": "client2"}
            ]
        )

        assert isinstance(response.data, list)
        assert len(response.data) == 2
        assert response.data[0]["name"] == "client1"

    def test_response_with_complex_nested_data(self):

        complex_data = {
            "clients": [
                {
                    "name": "client1",
                    "config": {
                        "ip": "10.0.0.2",
                        "public_key": "abc123",
                        "allowed_ips": ["10.0.0.0/24", "192.168.1.0/24"]
                    }
                },
                {
                    "name": "client2",
                    "config": {
                        "ip": "10.0.0.3",
                        "public_key": "def456",
                        "allowed_ips": ["10.0.0.0/24"]
                    }
                }
            ],
            "server": {
                "interface": "wg0",
                "port": 51820,
                "network": "10.0.0.0/24"
            },
            "stats": {
                "total_clients": 2,
                "active_clients": 1,
                "total_transfer": {
                    "rx": 1024000,
                    "tx": 2048000
                }
            }
        }

        response = APIResponse.success_response(data=complex_data)
        result = response.to_dict()

        assert result["data"]["clients"][0]["config"]["ip"] == "10.0.0.2"
        assert result["data"]["server"]["port"] == 51820
        assert result["data"]["stats"]["total_transfer"]["rx"] == 1024000

    def test_response_with_none_values_in_data(self):

        response = APIResponse(
            success=True,
            data={
                "field1": "value1",
                "field2": None,
                "field3": "",
                "field4": 0,
                "field5": False
            }
        )

        result = response.to_dict()
        # Data should preserve all values including None, empty, 0, False
        assert result["data"]["field1"] == "value1"
        assert result["data"]["field2"] is None
        assert result["data"]["field3"] == ""
        assert result["data"]["field4"] == 0
        assert result["data"]["field5"] is False

    def test_metadata_timestamp_format(self):
        response = APIResponse(success=True)

        timestamp = response.metadata["timestamp"]
        # Should end with Z (Zulu time)
        assert timestamp.endswith('Z')
        # Should be parseable as datetime - Remove Z and add +00:00 for parsing
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert dt.tzinfo is not None  # Should have timezone info

    def test_response_equality(self):

        response1 = APIResponse(
            success=True,
            data={"test": "data"}
        )
        response2 = APIResponse(
            success=True,
            data={"test": "data"}
        )
        response3 = APIResponse(
            success=False,
            error="Error",
            code="ERR"
        )

        # Same data but different metadata (timestamps will differ)
        assert response1.success == response2.success
        assert response1.data == response2.data

        # Different responses
        assert response1.success != response3.success
        assert response1.data != response3.data
