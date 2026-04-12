"""
Phantom-WG Frontmatter — Exception hierarchy

Every exception raised by the frontmatter API and modules inherits
from FrontmatterException. Module-specific errors are grouped under
short umbrella classes (SetupError, GhostError) that the API core
recognizes when wrapping them into APIResponse failures.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""


class FrontmatterException(Exception):
    """Base exception for all Phantom-WG Frontmatter errors."""

    def __init__(self, message: str, *, code: str = "FRONTMATTER_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


# ── Configuration & validation ─────────────────────────────────────

class ConfigurationError(FrontmatterException):
    """Configuration is missing, malformed, or out of order.

    Used by ``setup`` when a re-init is attempted on a populated
    state DB and by ``ghost`` when the prerequisites for a runtime
    action are missing.
    """

    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR")


class ValidationError(FrontmatterException):
    """An input parameter failed validation."""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


# ── Module discovery / dispatch ────────────────────────────────────

class FrontmatterModuleNotFoundError(FrontmatterException):
    """Requested module is not loaded or does not exist."""

    def __init__(self, module_name: str):
        super().__init__(
            f"Module '{module_name}' not found",
            code="MODULE_NOT_FOUND",
        )
        self.module_name = module_name


# ── Service errors (generic) ───────────────────────────────────────

class ServiceError(FrontmatterException):
    """Generic service operation failure (systemd, subprocess, etc)."""

    def __init__(self, message: str, *, code: str = "SERVICE_ERROR"):
        super().__init__(message, code=code)


# ── Setup module ───────────────────────────────────────────────────

class SetupError(ServiceError):
    """A setup module operation (init / clean / status) failed."""

    def __init__(self, message: str, *, code: str = "SETUP_ERROR"):
        super().__init__(message, code=code)


# ── Ghost module ───────────────────────────────────────────────────

class GhostError(ServiceError):
    """A ghost module operation (start / stop / restart / status) failed."""

    def __init__(self, message: str, *, code: str = "GHOST_ERROR"):
        super().__init__(message, code=code)
