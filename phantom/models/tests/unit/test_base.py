"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Base Models Unit Test

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import pytest
from typing import Dict, Any
from dataclasses import dataclass

from phantom.models.base import CommandResult, BaseModel, Result


class TestCommandResult:

    def test_init_minimal(self):
        result = CommandResult(success=True)
        assert result.success is True
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.returncode == 0
        assert result.error is None

    def test_init_complete(self):
        result = CommandResult(
            success=True,
            stdout="Command output",
            stderr="",
            returncode=0,
            error=None
        )
        assert result.success is True
        assert result.stdout == "Command output"
        assert result.stderr == ""
        assert result.returncode == 0
        assert result.error is None

    def test_init_with_error(self):
        result = CommandResult(
            success=False,
            stdout="",
            stderr="Error occurred",
            returncode=1,
            error="Command failed"
        )
        assert result.success is False
        assert result.stdout == ""
        assert result.stderr == "Error occurred"
        assert result.returncode == 1
        assert result.error == "Command failed"

    def test_to_dict(self):
        result = CommandResult(
            success=True,
            stdout="ls output",
            stderr="",
            returncode=0,
            error=None
        )
        dict_result = result.to_dict()
        assert dict_result == {
            "success": True,
            "stdout": "ls output",
            "stderr": "",
            "returncode": 0,
            "error": None
        }

    def test_to_dict_with_error(self):
        result = CommandResult(
            success=False,
            stdout="",
            stderr="Permission denied",
            returncode=126,
            error="Access denied"
        )
        dict_result = result.to_dict()
        assert dict_result["success"] is False
        assert dict_result["stderr"] == "Permission denied"
        assert dict_result["returncode"] == 126
        assert dict_result["error"] == "Access denied"

    def test_various_return_codes(self):
        test_cases = [
            (0, True, "Success"),
            (1, False, "General error"),
            (2, False, "Misuse of shell command"),
            (126, False, "Permission problem"),
            (127, False, "Command not found"),
            (128, False, "Invalid argument"),
            (130, False, "Script terminated by Ctrl+C"),
            (255, False, "Exit status out of range")
        ]

        for returncode, success, error in test_cases:
            result = CommandResult(
                success=success,
                returncode=returncode,
                error=error
            )
            assert result.returncode == returncode
            assert result.success == success
            assert result.error == error


class TestBaseModel:

    def test_concrete_implementation(self):
        @dataclass
        class ConcreteModel(BaseModel):
            name: str
            value: int
            optional: str = None

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "name": self.name,
                    "value": self.value,
                    "optional": self.optional
                }

        model = ConcreteModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42
        assert model.optional is None

    def test_to_json_dict_removes_none(self):
        @dataclass
        class TestModel(BaseModel):
            required: str
            optional1: str = None
            optional2: int = None

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "required": self.required,
                    "optional1": self.optional1,
                    "optional2": self.optional2
                }

        model = TestModel(required="value")
        dict_result = model.to_dict()
        json_dict_result = model.to_json_dict()

        # to_dict includes None values
        assert dict_result == {
            "required": "value",
            "optional1": None,
            "optional2": None
        }

        # to_json_dict excludes None values
        assert json_dict_result == {
            "required": "value"
        }

    def test_to_json_dict_with_values(self):
        @dataclass
        class FullModel(BaseModel):
            field1: str
            field2: int
            field3: bool

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "field1": self.field1,
                    "field2": self.field2,
                    "field3": self.field3
                }

        model = FullModel(field1="text", field2=100, field3=True)
        json_dict = model.to_json_dict()

        assert json_dict == {
            "field1": "text",
            "field2": 100,
            "field3": True
        }

    def test_to_json_dict_empty_strings(self):
        @dataclass
        class StringModel(BaseModel):
            empty: str
            none_value: str

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "empty": self.empty,
                    "none_value": self.none_value
                }

        model = StringModel(empty="", none_value=None)  # type: ignore
        json_dict = model.to_json_dict()

        # Empty strings are preserved, None values removed
        assert json_dict == {
            "empty": ""
        }

    def test_abstract_method_enforcement(self):
        with pytest.raises(TypeError) as exc_info:
            # noinspection PyAbstractClass
            class IncompleteModel(BaseModel):
                pass

            # noinspection PyTypeChecker,PyAbstractClass
            IncompleteModel()

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_abstract_to_dict_method(self):
        assert hasattr(BaseModel, 'to_dict')
        assert callable(getattr(BaseModel, 'to_dict', None))

        import inspect
        assert inspect.isabstract(BaseModel)
        abstract_methods = BaseModel.__abstractmethods__
        assert 'to_dict' in abstract_methods

        @dataclass
        class ValidModel(BaseModel):
            interface: str
            port: int

            def to_dict(self) -> Dict[str, Any]:
                return {"interface": self.interface, "port": self.port}

        model = ValidModel(interface="wg0", port=51820)
        result = model.to_dict()
        assert result == {"interface": "wg0", "port": 51820}

        to_dict_method = BaseModel.to_dict
        # noinspection PyUnresolvedReferences
        assert to_dict_method.__isabstractmethod__ is True

        # noinspection PyAbstractClass
        class PartialModel(BaseModel):
            def __init__(self):
                super().__init__()

            def call_parent_to_dict(self):
                return BaseModel.to_dict(self)

        with pytest.raises(TypeError):
            # noinspection PyAbstractClass
            PartialModel()

        assert BaseModel.to_dict is not None
        assert hasattr(BaseModel.to_dict, '__isabstractmethod__')


class TestResult:

    def test_init_success_with_data(self):
        result = Result(success=True, data="test_data")
        assert result.success is True
        assert result.data == "test_data"
        assert result.error is None

    def test_init_failure_with_error(self):
        result = Result(success=False, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_init_failure_with_both(self):
        result = Result(success=False, data="partial_data", error="Partial failure")
        assert result.success is False
        assert result.data == "partial_data"
        assert result.error == "Partial failure"

    def test_with_different_types(self):
        str_result = Result(success=True, data="string value")
        assert str_result.data == "string value"

        int_result = Result(success=True, data=42)
        assert int_result.data == 42

        list_result = Result(success=True, data=[1, 2, 3])
        assert list_result.data == [1, 2, 3]

        dict_result = Result(success=True, data={"key": "value"})
        assert dict_result.data == {"key": "value"}

        none_result = Result(success=True, data=None)
        assert none_result.data is None

    def test_with_complex_object(self):
        @dataclass
        class WireGuardPeer:
            peer_id: int
            public_key: str
            allowed_ips: list

        complex_obj = WireGuardPeer(peer_id=1, public_key="abc123def456", allowed_ips=["10.0.0.2/32"])
        result = Result(success=True, data=complex_obj)

        assert result.success is True
        assert result.data.peer_id == 1
        assert result.data.public_key == "abc123def456"
        assert result.data.allowed_ips == ["10.0.0.2/32"]

    def test_boolean_evaluation(self):
        success_result = Result(success=True, data="data")
        failure_result = Result(success=False, error="error")
        assert success_result.success is True
        assert failure_result.success is False

    def test_typed_result(self):
        from typing import List, Dict
        list_result: Result[List[int]] = Result(success=True, data=[1, 2, 3])
        assert isinstance(list_result.data, list)

        dict_result: Result[Dict[str, str]] = Result(
            success=True,
            data={"key1": "value1", "key2": "value2"}
        )
        assert isinstance(dict_result.data, dict)

        @dataclass
        class ClientConfig:
            client_name: str
            ip_address: str

        client_result: Result[ClientConfig] = Result(
            success=True,
            data=ClientConfig(client_name="phantom_client_01", ip_address="10.8.0.2")
        )
        assert isinstance(client_result.data, ClientConfig)

    def test_error_scenarios(self):
        error_cases = [
            "Connection timeout",
            "Invalid input",
            "Permission denied",
            "Resource not found",
            ""
        ]

        for error_msg in error_cases:
            result = Result(success=False, error=error_msg)
            assert result.success is False
            assert result.error == error_msg
            assert result.data is None
