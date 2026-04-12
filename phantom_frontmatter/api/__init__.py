"""
Phantom-WG Frontmatter API — Public interface

Exports:
    FrontmatterAPI   — Main API orchestrator
    APIResponse      — Unified response envelope
    KVStore          — SQLite key/value store backing all module state
    All exception classes
"""

from .core import FrontmatterAPI
from .response import APIResponse
from .store import KVStore
from .exceptions import (
    ConfigurationError,
    FrontmatterException,
    FrontmatterModuleNotFoundError,
    GhostError,
    ServiceError,
    SetupError,
    ValidationError,
)

__all__ = [
    "FrontmatterAPI",
    "APIResponse",
    "KVStore",
    "FrontmatterException",
    "ConfigurationError",
    "ValidationError",
    "FrontmatterModuleNotFoundError",
    "ServiceError",
    "SetupError",
    "GhostError",
]
