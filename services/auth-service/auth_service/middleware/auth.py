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

FastAPI auth dependency — Bearer extraction, JWT verify, inactivity check.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request

from auth_service.crypto.jwt import TokenPayload, decode_token, token_hash
from auth_service.errors import AuthTokenError


def require_auth(request: Request) -> TokenPayload:
    """Extract and verify Bearer token. Check session validity and inactivity."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = auth_header[7:]
    verify_key = request.app.state.verify_key
    db = request.app.state.db
    config = request.app.state.config

    try:
        payload = decode_token(verify_key, raw_token)
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.typ != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    session = db.get_session_by_jti(payload.jti)
    if session is None or session.revoked:
        raise HTTPException(status_code=401, detail="Session revoked or not found")

    # Verify token hash matches stored hash
    if token_hash(raw_token) != session.token_hash:
        raise HTTPException(status_code=401, detail="Token mismatch")

    # Inactivity timeout check
    last_activity = datetime.fromisoformat(session.last_activity_at)
    now = datetime.now(timezone.utc)
    elapsed = (now - last_activity).total_seconds()
    if elapsed > config.inactivity_timeout:
        db.revoke_session(payload.jti)
        raise HTTPException(status_code=401, detail="Session expired due to inactivity")

    # Update last activity
    db.update_last_activity(payload.jti)

    return payload
