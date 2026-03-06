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

Pydantic request/response models.
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Envelope ─────────────────────────────────────────────────────


class ApiOk(BaseModel, Generic[T]):
    ok: Literal[True] = True
    data: T


class ApiErr(BaseModel):
    ok: Literal[False] = False
    error: str


# ── Auth Requests ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    password: str = Field(min_length=8, max_length=256)


class ChangePasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class MFAVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=8)


class TOTPDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


# ── Auth Responses ───────────────────────────────────────────────


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class MFARequiredResponse(BaseModel):
    mfa_required: Literal[True] = True
    mfa_token: str


class UserInfo(BaseModel):
    id: str
    username: str
    totp_enabled: bool
    created_at: str
    updated_at: str


class TOTPEnableResponse(BaseModel):
    secret: str
    uri: str
    backup_codes: list[str]
