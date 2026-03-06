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

Auth service configuration from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthConfig:
    """Immutable auth service configuration."""

    daemon_socket: str
    db_dir: str
    secrets_dir: str
    token_lifetime: int
    inactivity_timeout: int
    mfa_token_lifetime: int
    rate_limit_window: int
    rate_limit_max: int


def load_auth_config() -> AuthConfig:
    """Load configuration from environment variables."""
    return AuthConfig(
        daemon_socket=os.environ.get(
            "PHANTOM_DAEMON_SOCKET", "/var/run/phantom/daemon.sock"
        ),
        db_dir=os.environ.get("AUTH_DB_DIR", "/var/lib/phantom/auth"),
        secrets_dir=os.environ.get("AUTH_SECRETS_DIR", "/run/secrets"),
        token_lifetime=int(os.environ.get("AUTH_TOKEN_LIFETIME", "86400")),
        inactivity_timeout=int(os.environ.get("AUTH_INACTIVITY_TIMEOUT", "1800")),
        mfa_token_lifetime=int(os.environ.get("AUTH_MFA_TOKEN_LIFETIME", "300")),
        rate_limit_window=int(os.environ.get("AUTH_RATE_LIMIT_WINDOW", "60")),
        rate_limit_max=int(os.environ.get("AUTH_RATE_LIMIT_MAX", "5")),
    )
