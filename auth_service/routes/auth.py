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

Auth API endpoints — login, MFA, user management.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from auth_service.audit import audit_log
from auth_service.crypto.jwt import TokenPayload, encode_token, token_hash
from auth_service.crypto.password import hash_password, verify_password
from auth_service.crypto.totp import (
    build_totp_uri,
    generate_backup_codes,
    generate_secret,
    hash_backup_code,
    verify_totp,
)
from auth_service.errors import AuthDatabaseError, AuthTokenError
from auth_service.middleware.auth import require_auth
from auth_service.models import (
    ApiOk,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    MFARequiredResponse,
    MFAVerifyRequest,
    TOTPDisableRequest,
    TOTPEnableResponse,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Login ────────────────────────────────────────────────────────


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate with username+password. Returns JWT or MFA challenge."""
    db = request.app.state.db
    rate_limiter = request.app.state.rate_limiter
    ip = _get_ip(request)

    if not rate_limiter.check(ip):
        audit_log(db, request, "login_rate_limited", {"username": body.username})
        raise HTTPException(status_code=429, detail="Too many login attempts")

    user = db.get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        audit_log(db, request, "login_failed", {"username": body.username})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rate_limiter.reset(ip)

    # TOTP enabled → issue short-lived MFA pending token
    if user.totp_secret is not None:
        config = request.app.state.config
        signing_key = request.app.state.signing_key
        mfa_jti = uuid.uuid4().hex
        mfa_token = encode_token(
            signing_key=signing_key,
            sub=user.username,
            jti=mfa_jti,
            lifetime=config.mfa_token_lifetime,
            typ="mfa_pending",
        )
        audit_log(db, request, "mfa_challenge", {"username": user.username}, user_id=user.id)
        return ApiOk(data=MFARequiredResponse(mfa_token=mfa_token))

    # No TOTP → issue access token directly
    return _issue_access_token(request, user.username, user.id)


# ── MFA Verify ───────────────────────────────────────────────────


@router.post("/mfa/verify")
def mfa_verify(body: MFAVerifyRequest, request: Request):
    """Verify TOTP code and issue access token."""
    verify_key = request.app.state.verify_key
    db = request.app.state.db

    try:
        payload = _decode_mfa_token(verify_key, body.mfa_token)
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user = db.get_user_by_username(payload.sub)
    if user is None or user.totp_secret is None:
        raise HTTPException(status_code=401, detail="Invalid MFA state")

    if not verify_totp(user.totp_secret, body.code):
        audit_log(db, request, "mfa_failed", {"username": user.username}, user_id=user.id)
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    audit_log(db, request, "mfa_success", {"username": user.username}, user_id=user.id)
    return _issue_access_token(request, user.username, user.id)


# ── MFA Backup Code ─────────────────────────────────────────────


@router.post("/totp/backup")
def mfa_backup(body: MFAVerifyRequest, request: Request):
    """Verify backup code and issue access token."""
    verify_key = request.app.state.verify_key
    db = request.app.state.db

    try:
        payload = _decode_mfa_token(verify_key, body.mfa_token)
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user = db.get_user_by_username(payload.sub)
    if user is None or user.totp_secret is None:
        raise HTTPException(status_code=401, detail="Invalid MFA state")

    code_hash = hash_backup_code(body.code)
    if not db.verify_backup_code(user.id, code_hash):
        audit_log(db, request, "backup_code_failed", {"username": user.username}, user_id=user.id)
        raise HTTPException(status_code=401, detail="Invalid backup code")

    remaining = db.count_remaining_backup_codes(user.id)
    audit_log(
        db, request, "backup_code_used",
        {"username": user.username, "remaining": remaining},
        user_id=user.id,
    )
    return _issue_access_token(request, user.username, user.id)


# ── TOTP Management ─────────────────────────────────────────────


@router.post("/totp/enable")
def totp_enable(request: Request, payload: TokenPayload = Depends(require_auth)):
    """Enable TOTP for current user. Returns secret, URI, and backup codes."""
    db = request.app.state.db
    user = db.get_user_by_username(payload.sub)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.totp_secret is not None:
        raise HTTPException(status_code=409, detail="TOTP already enabled")

    secret = generate_secret()
    uri = build_totp_uri(secret, user.username)
    backup_codes = generate_backup_codes()
    backup_hashes = [hash_backup_code(c) for c in backup_codes]

    db.set_totp_secret(user.id, secret)
    db.store_backup_codes(user.id, backup_hashes)

    audit_log(db, request, "totp_enabled", {"username": user.username}, user_id=user.id)
    return ApiOk(data=TOTPEnableResponse(secret=secret, uri=uri, backup_codes=backup_codes))


@router.post("/totp/disable")
def totp_disable(
    body: TOTPDisableRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
):
    """Disable TOTP for current user. Requires password confirmation."""
    db = request.app.state.db
    user = db.get_user_by_username(payload.sub)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.totp_secret is None:
        raise HTTPException(status_code=400, detail="TOTP not enabled")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    db.set_totp_secret(user.id, None)
    db.clear_backup_codes(user.id)

    audit_log(db, request, "totp_disabled", {"username": user.username}, user_id=user.id)
    return ApiOk(data={"message": "TOTP disabled"})


# ── Session Management ───────────────────────────────────────────


@router.post("/logout")
def logout(request: Request, payload: TokenPayload = Depends(require_auth)):
    """Revoke current session."""
    db = request.app.state.db
    db.revoke_session(payload.jti)
    audit_log(db, request, "logout", {"username": payload.sub})
    return ApiOk(data={"message": "Logged out"})


@router.get("/me")
def me(request: Request, payload: TokenPayload = Depends(require_auth)):
    """Get current user info."""
    db = request.app.state.db
    user = db.get_user_by_username(payload.sub)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ApiOk(data=_user_info(user))


# ── User Management ─────────────────────────────────────────────


@router.post("/users")
def create_user(
    body: CreateUserRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
):
    """Create a new user."""
    db = request.app.state.db
    pw_hash = hash_password(body.password)
    try:
        user = db.create_user(username=body.username, password_hash=pw_hash)
    except AuthDatabaseError:
        raise HTTPException(status_code=409, detail=f"User already exists: {body.username}")
    audit_log(
        db, request, "user_created",
        {"username": body.username, "by": payload.sub},
        user_id=user.id,
    )
    return ApiOk(data=_user_info(user))


@router.get("/users")
def list_users(
    request: Request,
    _payload: TokenPayload = Depends(require_auth),
):
    """List all users."""
    db = request.app.state.db
    users = db.list_users()
    return ApiOk(data=[_user_info(u) for u in users])


@router.delete("/users/{username}")
def delete_user(
    username: str,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
):
    """Delete a user. Cannot delete self."""
    if username == payload.sub:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db = request.app.state.db
    user = db.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.revoke_user_sessions(user.id)
    db.delete_user(username)
    audit_log(
        db, request, "user_deleted",
        {"username": username, "by": payload.sub},
        user_id=user.id,
    )
    return ApiOk(data={"message": f"User {username} deleted"})


@router.post("/users/{username}/password")
def change_password(
    username: str,
    body: ChangePasswordRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
):
    """Change password. Any authenticated user can change any password."""
    db = request.app.state.db
    pw_hash = hash_password(body.password)
    if not db.update_password(username, pw_hash):
        raise HTTPException(status_code=404, detail="User not found")
    audit_log(
        db, request, "password_changed",
        {"username": username, "by": payload.sub},
    )
    return ApiOk(data={"message": "Password changed"})


# ── Helpers ──────────────────────────────────────────────────────


def _issue_access_token(request: Request, username: str, user_id: str):
    """Create session + issue access JWT."""
    config = request.app.state.config
    signing_key = request.app.state.signing_key
    db = request.app.state.db

    jti = uuid.uuid4().hex
    token = encode_token(
        signing_key=signing_key,
        sub=username,
        jti=jti,
        lifetime=config.token_lifetime,
    )

    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=config.token_lifetime)
    db.create_session(
        user_id=user_id,
        token_jti=jti,
        token_hash=token_hash(token),
        issued_at=now.isoformat(),
        expires_at=expires.isoformat(),
    )

    audit_log(db, request, "login_success", {"username": username}, user_id=user_id)
    return ApiOk(data=LoginResponse(token=token, expires_in=config.token_lifetime))


def _decode_mfa_token(verify_key, mfa_token: str) -> TokenPayload:
    """Decode and validate an MFA pending token."""
    from auth_service.crypto.jwt import decode_token as _decode

    payload = _decode(verify_key, mfa_token)
    if payload.typ != "mfa_pending":
        raise AuthTokenError("Invalid MFA token type")
    return payload


def _user_info(user) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        totp_enabled=user.totp_secret is not None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""
