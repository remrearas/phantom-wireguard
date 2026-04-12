"""
Setup Module — Secret Generation

Generates the wstunnel ``--restrict-http-upgrade-path-prefix`` value
using ``secrets.token_urlsafe`` (32 bytes of CSPRNG entropy from the
Python standard library).

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import secrets


# 32 bytes → 43 URL-safe base64 characters.
DEFAULT_SECRET_BYTES = 32


def generate_secret(byte_length: int = DEFAULT_SECRET_BYTES) -> str:
    """Return a fresh URL-safe random string for the wstunnel HTTP
    upgrade path prefix.
    """
    while True:
        secret = secrets.token_urlsafe(byte_length)
        if not secret.startswith("-"):
            return secret


def secret_fingerprint(secret: str, length: int = 8) -> str:
    """Return a short prefix of the secret for logging / status output."""
    if not secret:
        return "<unset>"
    return f"{secret[:length]}..."