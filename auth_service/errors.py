"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Auth service error hierarchy.
"""


class AuthError(Exception):
    """Base error for auth service."""


class AuthSecretsError(AuthError):
    """Key loading / validation failures."""


class AuthDatabaseError(AuthError):
    """Database operation failures."""


class AuthTokenError(AuthError):
    """JWT encode / decode / validation failures."""


class AuthCredentialsError(AuthError):
    """Login credential failures."""


class AuthRateLimitError(AuthError):
    """Rate limit exceeded."""


class AuthMFARequiredError(AuthError):
    """TOTP verification required to complete login."""


class AuthMFAError(AuthError):
    """TOTP setup / verification failures."""


class AuthInactivityError(AuthError):
    """Session expired due to inactivity."""
