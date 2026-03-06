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

Manual Ed25519 JWT implementation (no PyJWT dependency).
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass

from nacl.signing import SigningKey, VerifyKey

from auth_service.errors import AuthTokenError

_HEADER = {"alg": "EdDSA", "typ": "JWT"}


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Decoded JWT payload."""

    sub: str
    jti: str
    iat: int
    exp: int
    typ: str
    role: str


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def token_hash(token: str) -> str:
    """SHA-256 hash of a JWT token for secure storage."""
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def encode_token(
    signing_key: SigningKey,
    sub: str,
    jti: str,
    lifetime: int,
    typ: str = "access",
    extra: dict | None = None,
) -> str:
    """Create a signed JWT token."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "jti": jti,
        "iat": now,
        "exp": now + lifetime,
        "typ": typ,
    }
    if extra:
        payload.update(extra)
    header_b64 = _b64url_encode(json.dumps(_HEADER, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_b64}.{payload_b64}".encode("ascii")
    signed = signing_key.sign(message)
    signature = signed.signature
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _verify_and_decode(verify_key: VerifyKey, token: str) -> dict:
    """Verify JWT signature, check expiration, return raw payload dict."""
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthTokenError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
    except (json.JSONDecodeError, Exception) as exc:
        raise AuthTokenError(f"Invalid token header: {exc}") from exc

    if header.get("alg") != "EdDSA":
        raise AuthTokenError(f"Unsupported algorithm: {header.get('alg')}")

    try:
        signature = _b64url_decode(sig_b64)
    except Exception as exc:
        raise AuthTokenError(f"Invalid signature encoding: {exc}") from exc

    message = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        verify_key.verify(message, signature)
    except Exception as exc:
        raise AuthTokenError(f"Signature verification failed: {exc}") from exc

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, Exception) as exc:
        raise AuthTokenError(f"Invalid token payload: {exc}") from exc

    now = int(time.time())
    exp = payload.get("exp", 0)
    if now >= exp:
        raise AuthTokenError("Token expired")

    return payload


def decode_token(verify_key: VerifyKey, token: str) -> TokenPayload:
    """Verify and decode a JWT token. Returns standard claims only."""
    payload = _verify_and_decode(verify_key, token)
    try:
        return TokenPayload(
            sub=payload["sub"],
            jti=payload["jti"],
            iat=payload["iat"],
            exp=payload["exp"],
            typ=payload.get("typ", "access"),
            role=payload.get("role", "admin"),
        )
    except KeyError as exc:
        raise AuthTokenError(f"Missing claim: {exc}") from exc


def decode_token_claims(verify_key: VerifyKey, token: str) -> dict:
    """Verify and decode a JWT token. Returns full payload dict (extra claims included)."""
    return _verify_and_decode(verify_key, token)
