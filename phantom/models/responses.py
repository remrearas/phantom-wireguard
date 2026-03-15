"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

API Response Wrapper Models - API Yanıt Sarmalayıcı Modelleri

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Dict, Any

from .base import BaseModel

T = TypeVar('T')


@dataclass
class TypedAPIResponse(Generic[T], BaseModel):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "metadata": self.metadata
        }

        if self.data is not None:
            # Serialize data based on type
            if hasattr(self.data, 'to_dict'):
                # Model object with to_dict method
                result["data"] = self.data.to_dict()
            elif isinstance(self.data, list):
                # List of models or primitives
                result["data"] = [  # type: ignore
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in self.data
                ]
            elif isinstance(self.data, dict):
                result["data"] = self.data
            else:
                result["data"] = self.data

        if self.error:
            result["error"] = self.error  # type: ignore
            if self.code:
                result["code"] = self.code  # type: ignore

        # Filter out None values except metadata (kept for API compatibility)
        filtered_result = {}
        for k, v in result.items():
            if k == "metadata":
                # Keep metadata even if None
                filtered_result[k] = v
            elif v is not None:
                filtered_result[k] = v
        return filtered_result

    @classmethod
    def success_response(cls, data: T, metadata: Optional[Dict[str, Any]] = None) -> 'TypedAPIResponse[T]':
        return cls(
            success=True,
            data=data,
            metadata=metadata
        )

    @classmethod
    def error_response(cls, error: str, code: str,
                       data: Optional[Any] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> 'TypedAPIResponse[T]':
        return cls(
            success=False,
            error=error,
            code=code,
            data=data,
            metadata=metadata
        )


__all__ = ['TypedAPIResponse']
