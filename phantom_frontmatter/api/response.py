"""
Phantom-WG Frontmatter — Unified API Response

All module actions return an APIResponse object for consistent
handling by the CLI and programmatic consumers.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class APIResponse:
    """Unified response envelope for all module actions.

    Attributes:
        success:   True if the action completed without errors
        data:      Action result payload (any JSON-serializable value)
        error:     Human-readable error message (only when success=False)
        code:      Machine-readable error/status code
        module:    Module name that produced the response
        action:    Action name that was executed
        metadata:  Additional key-value metadata (timestamps, etc.)
    """

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    code: Optional[str] = None
    module: Optional[str] = None
    action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

    # ── Factory methods ────────────────────────────────────────────

    @classmethod
    def ok(
        cls,
        data: Any = None,
        *,
        module: Optional[str] = None,
        action: Optional[str] = None,
        **metadata: Any,
    ) -> "APIResponse":
        """Create a successful response."""
        return cls(
            success=True,
            data=data,
            module=module,
            action=action,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        error: str,
        *,
        code: str = "ERROR",
        module: Optional[str] = None,
        action: Optional[str] = None,
        **metadata: Any,
    ) -> "APIResponse":
        """Create a failure response."""
        return cls(
            success=False,
            error=error,
            code=code,
            module=module,
            action=action,
            metadata=metadata or {},
        )

    # ── Serialization ──────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting None fields for cleaner output."""
        result = asdict(self)
        # Remove None fields for cleaner JSON output
        return {k: v for k, v in result.items() if v is not None}

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def __bool__(self) -> bool:
        """Truthiness based on success flag."""
        return self.success
