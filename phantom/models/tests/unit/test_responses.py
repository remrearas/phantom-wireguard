"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Response Models Unit Test

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from phantom.models.responses import TypedAPIResponse
from phantom.models.base import BaseModel


class TestTypedAPIResponse:

    def test_init_success(self):
        response = TypedAPIResponse(
            success=True,
            data="test_data"
        )
        assert response.success is True
        assert response.data == "test_data"
        assert response.error is None
        assert response.code is None
        assert response.metadata is None

    def test_init_error(self):
        response = TypedAPIResponse(
            success=False,
            error="Something went wrong",
            code="ERR_001"
        )
        assert response.success is False
        assert response.data is None
        assert response.error == "Something went wrong"
        assert response.code == "ERR_001"
        assert response.metadata is None

    def test_init_with_metadata(self):
        metadata = {"timestamp": "2025-01-01T12:00:00", "version": "1.0"}
        response = TypedAPIResponse(
            success=True,
            data={"result": "ok"},
            metadata=metadata
        )
        assert response.metadata == metadata
        assert response.metadata["version"] == "1.0"

    def test_to_dict_simple_data(self):
        response = TypedAPIResponse(
            success=True,
            data="simple string",
            metadata={"type": "string"}
        )
        result = response.to_dict()
        assert result == {
            "success": True,
            "data": "simple string",
            "metadata": {"type": "string"}
        }

    def test_to_dict_with_model_data(self):

        @dataclass
        class TestModel(BaseModel):
            name: str
            value: int

            def to_dict(self) -> Dict[str, Any]:
                return {"name": self.name, "value": self.value}

        model = TestModel(name="test", value=42)
        response = TypedAPIResponse(
            success=True,
            data=model
        )
        result = response.to_dict()
        assert result["data"] == {"name": "test", "value": 42}

    def test_to_dict_with_list_of_models(self):

        @dataclass
        class Item(BaseModel):
            id: int
            name: str

            def to_dict(self) -> Dict[str, Any]:
                return {"id": self.id, "name": self.name}

        items = [
            Item(id=1, name="item1"),
            Item(id=2, name="item2")
        ]
        response = TypedAPIResponse(
            success=True,
            data=items
        )
        result = response.to_dict()
        assert result["data"] == [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2"}
        ]

    def test_to_dict_with_list_of_primitives(self):
        response = TypedAPIResponse(
            success=True,
            data=[1, 2, 3, 4, 5]
        )
        result = response.to_dict()
        assert result["data"] == [1, 2, 3, 4, 5]

    def test_to_dict_with_dict_data(self):
        data = {
            "key1": "value1",
            "key2": 123,
            "nested": {"inner": "data"}
        }
        response = TypedAPIResponse(
            success=True,
            data=data
        )
        result = response.to_dict()
        assert result["data"] == data

    def test_to_dict_with_error(self):
        response = TypedAPIResponse(
            success=False,
            error="Invalid request",
            code="INVALID_REQUEST"
        )
        result = response.to_dict()
        assert result == {
            "success": False,
            "error": "Invalid request",
            "code": "INVALID_REQUEST",
            "metadata": None
        }

    def test_to_dict_error_without_code(self):
        response = TypedAPIResponse(
            success=False,
            error="Generic error"
        )
        result = response.to_dict()
        assert result == {
            "success": False,
            "error": "Generic error",
            "metadata": None
        }

    def test_to_dict_metadata_always_included(self):
        response = TypedAPIResponse(
            success=True,
            data="test"
        )
        result = response.to_dict()
        assert "metadata" in result
        assert result["metadata"] is None

    def test_to_dict_filters_none_except_metadata(self):
        response = TypedAPIResponse(
            success=True,
            data=None,
            error=None,
            code=None,
            metadata=None
        )
        result = response.to_dict()
        # Only success and metadata remain
        assert result == {
            "success": True,
            "metadata": None
        }

    def test_success_response_classmethod(self):
        data = {"result": "success"}
        metadata = {"processed_at": "2025-01-01"}

        response = TypedAPIResponse.success_response(
            data=data,
            metadata=metadata
        )

        assert response.success is True
        assert response.data == data
        assert response.metadata == metadata
        assert response.error is None
        assert response.code is None

    def test_success_response_without_metadata(self):
        response = TypedAPIResponse.success_response(
            data="simple_data"
        )

        assert response.success is True
        assert response.data == "simple_data"
        assert response.metadata is None

    def test_error_response_classmethod(self):
        response = TypedAPIResponse.error_response(
            error="Database connection failed",
            code="DB_CONNECTION_ERROR",
            data={"attempts": 3},
            metadata={"timestamp": "2025-01-01T12:00:00"}
        )

        assert response.success is False
        assert response.error == "Database connection failed"
        assert response.code == "DB_CONNECTION_ERROR"
        assert response.data == {"attempts": 3}
        assert response.metadata["timestamp"] == "2025-01-01T12:00:00"

    def test_error_response_minimal(self):
        response = TypedAPIResponse.error_response(
            error="Not found",
            code="NOT_FOUND"
        )

        assert response.success is False
        assert response.error == "Not found"
        assert response.code == "NOT_FOUND"
        assert response.data is None
        assert response.metadata is None

    def test_mixed_list_data(self):

        @dataclass
        class MixedItem(BaseModel):
            value: str

            def to_dict(self) -> Dict[str, Any]:
                return {"value": self.value}

        # List with both models and primitives
        mixed_data = [
            MixedItem(value="model1"),
            "plain_string",
            MixedItem(value="model2"),
            123
        ]

        response = TypedAPIResponse(
            success=True,
            data=mixed_data
        )

        result = response.to_dict()
        assert result["data"] == [
            {"value": "model1"},
            "plain_string",
            {"value": "model2"},
            123
        ]

    def test_nested_models(self):

        @dataclass
        class InnerModel(BaseModel):
            inner_value: str

            def to_dict(self) -> Dict[str, Any]:
                return {"inner_value": self.inner_value}

        @dataclass
        class OuterModel(BaseModel):
            outer_value: str
            inner: InnerModel

            def to_dict(self) -> Dict[str, Any]:
                return {
                    "outer_value": self.outer_value,
                    "inner": self.inner.to_dict()
                }

        nested = OuterModel(
            outer_value="outer",
            inner=InnerModel(inner_value="inner")
        )

        response = TypedAPIResponse(
            success=True,
            data=nested
        )

        result = response.to_dict()
        assert result["data"] == {
            "outer_value": "outer",
            "inner": {"inner_value": "inner"}
        }

    def test_empty_metadata(self):
        response = TypedAPIResponse(
            success=True,
            data="test",
            metadata={}
        )
        result = response.to_dict()
        assert result["metadata"] == {}

    def test_complex_metadata(self):
        metadata = {
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5
            },
            "filters": ["active", "verified"],
            "sort": "created_at",
            "api_version": "2.0",
            "request_id": "req_123456"
        }

        response = TypedAPIResponse(
            success=True,
            data=[],
            metadata=metadata
        )

        result = response.to_dict()
        assert result["metadata"] == metadata
        assert result["metadata"]["pagination"]["total"] == 100

    def test_various_data_types(self):
        test_cases = [
            (None, None),
            (True, True),
            (False, False),
            (0, 0),
            (42, 42),
            (3.14, 3.14),
            ("", ""),
            ("text", "text"),
            ([], []),
            ({}, {}),
            ([1, 2, 3], [1, 2, 3]),
            ({"a": 1}, {"a": 1})
        ]

        for input_data, expected in test_cases:
            response = TypedAPIResponse(
                success=True,
                data=input_data
            )
            result = response.to_dict()
            if input_data is not None:
                assert result["data"] == expected
            else:
                assert "data" not in result

    def test_type_ignore_comments(self):
        # Verify type handling in list comprehension
        response = TypedAPIResponse(
            success=True,
            data=[{"id": 1}, {"id": 2}]
        )
        result = response.to_dict()
        assert isinstance(result["data"], list)

        response_error = TypedAPIResponse(
            success=False,
            error="Test error"
        )
        result_error = response_error.to_dict()
        assert "error" in result_error

        response_code = TypedAPIResponse(
            success=False,
            error="Test error",
            code="TEST_CODE"
        )
        result_code = response_code.to_dict()
        assert "code" in result_code

    def test_generic_typing(self):
        str_response: TypedAPIResponse[str] = TypedAPIResponse(
            success=True,
            data="string data"
        )
        assert isinstance(str_response.data, str)

        list_response: TypedAPIResponse[List[int]] = TypedAPIResponse(
            success=True,
            data=[1, 2, 3]
        )
        assert isinstance(list_response.data, list)

        dict_response: TypedAPIResponse[Dict[str, Any]] = TypedAPIResponse(
            success=True,
            data={"key": "value"}
        )
        assert isinstance(dict_response.data, dict)

        optional_response: TypedAPIResponse[Optional[str]] = TypedAPIResponse(
            success=True,
            data=None
        )
        assert optional_response.data is None
