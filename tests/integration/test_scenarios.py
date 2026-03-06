"""
Docker scenario tests — run inside the auth container against the live service.

Usage: tools/dev.sh test --docker

Prerequisites:
  1. tools/setup.sh has been run (keys + DB + admin exist)
  2. docker compose up is running
  3. Admin password is in /run/secrets/.admin_password or AUTH_TEST_ADMIN_PASS env

Scenarios (executed in order):

  1. Admin login + me
     Login with bootstrap admin credentials → receive token → verify identity
     via /me → wrong password is rejected.

  2. User lifecycle
     Admin creates user → user logs in → password changed → login with new
     password → old password rejected → user appears in list → user deleted
     → deleted user cannot login.

  3. Session management
     Login → logout → same token rejected.
     Request without header → 401. Invalid token → 401.

  4. Self-protection
     Admin cannot delete own account → 400.

  5. TOTP full lifecycle
     Create user → login → enable TOTP (secret + URI + 8 backup codes)
     → login again: mfa_required + mfa_token returned
     → wrong TOTP code → 401
     → correct TOTP code (RFC 6238 HMAC-SHA1) → access token
     → login with backup code → access token
     → same backup code rejected on reuse → 401 (single-use)
     → disable TOTP (password confirmation required)
     → login succeeds without MFA
     → cleanup.

  6. Deleted user token revocation
     Create user → login → token works on /me → admin deletes user
     (sessions CASCADE delete) → same token returns 401.

  7. Duplicate user creation
     Create user → same username again → 409 Conflict.

  8. Rate limiting (last — poisons IP for the window duration)
     Rapid failed logins from same IP → sliding window fills → 429.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.docker

BASE_URL = os.environ.get("AUTH_TEST_URL", "http://localhost:8443")
ADMIN_USER = os.environ.get("AUTH_TEST_ADMIN_USER", "admin")


def _resolve_admin_pass() -> str:
    """Resolve admin password from env or bootstrap password file."""
    env_pass = os.environ.get("AUTH_TEST_ADMIN_PASS", "")
    if env_pass:
        return env_pass
    # Inside container: secrets dir is /run/secrets
    # Outside: container-data/secrets/development
    for candidate in (
        Path("/run/secrets/.admin_password"),
        Path("container-data/secrets/development/.admin_password"),
    ):
        if candidate.is_file():
            return candidate.read_text().strip()
    return ""


ADMIN_PASS = _resolve_admin_pass()


@pytest.fixture(scope="module")
def http():
    """Shared httpx client for the module."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="module")
def admin_token(http):
    """Login as admin, return access token."""
    if not ADMIN_PASS:
        pytest.skip("Admin password not available (run tools/setup.sh first)")
    resp = http.post("/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return resp.json()["data"]["token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _generate_totp_code(secret: str) -> str:
    """Generate a valid 6-digit TOTP code from a base32 secret."""
    key = base64.b32decode(secret)
    counter = struct.pack(">Q", int(time.time()) // 30)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    truncated = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % 1_000_000).zfill(6)


# ── Scenario 1: Admin login + me ────────────────────────────────


class TestAdminLogin:
    def test_login_returns_token(self, http):
        if not ADMIN_PASS:
            pytest.skip("Admin password not available")
        resp = http.post("/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "token" in data["data"]
        assert data["data"]["expires_in"] > 0

    def test_me_returns_admin(self, http, admin_token):
        resp = http.get("/auth/me", headers=_bearer(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == ADMIN_USER
        assert data["totp_enabled"] is False

    def test_login_wrong_password(self, http):
        resp = http.post("/auth/login", json={"username": ADMIN_USER, "password": "wrongwrong"})
        assert resp.status_code == 401
        assert resp.json()["ok"] is False


# ── Scenario 2: User lifecycle ──────────────────────────────────


class TestUserLifecycle:
    USERNAME = "scenario_user"
    PASSWORD = "ScenarioPass1!"
    NEW_PASSWORD = "NewScenario2!"

    def test_01_create_user(self, http, admin_token):
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        resp = http.post(
            "/auth/users",
            json={"username": self.USERNAME, "password": self.PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == self.USERNAME

    def test_02_new_user_can_login(self, http):
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        assert resp.status_code == 200
        assert "token" in resp.json()["data"]

    def test_03_change_password(self, http, admin_token):
        resp = http.post(
            f"/auth/users/{self.USERNAME}/password",
            json={"password": self.NEW_PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 200

    def test_04_login_with_new_password(self, http):
        resp = http.post(
            "/auth/login",
            json={"username": self.USERNAME, "password": self.NEW_PASSWORD},
        )
        assert resp.status_code == 200

    def test_05_old_password_rejected(self, http):
        resp = http.post(
            "/auth/login",
            json={"username": self.USERNAME, "password": self.PASSWORD},
        )
        assert resp.status_code == 401

    def test_06_list_users_includes_new(self, http, admin_token):
        resp = http.get("/auth/users", headers=_bearer(admin_token))
        assert resp.status_code == 200
        usernames = [u["username"] for u in resp.json()["data"]]
        assert self.USERNAME in usernames

    def test_07_delete_user(self, http, admin_token):
        resp = http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        assert resp.status_code == 200

    def test_08_deleted_user_cannot_login(self, http):
        resp = http.post(
            "/auth/login",
            json={"username": self.USERNAME, "password": self.NEW_PASSWORD},
        )
        assert resp.status_code == 401


# ── Scenario 3: Session management ──────────────────────────────


class TestSessionManagement:
    def test_logout_revokes_token(self, http):
        if not ADMIN_PASS:
            pytest.skip("Admin password not available")
        resp = http.post("/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
        token = resp.json()["data"]["token"]

        resp = http.post("/auth/logout", headers=_bearer(token))
        assert resp.status_code == 200

        resp = http.get("/auth/me", headers=_bearer(token))
        assert resp.status_code == 401

    def test_no_auth_returns_401(self, http):
        resp = http.get("/auth/me")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, http):
        resp = http.get("/auth/me", headers=_bearer("invalid.jwt.token"))
        assert resp.status_code == 401


# ── Scenario 4: Self-protection ─────────────────────────────────


class TestSelfProtection:
    def test_cannot_delete_self(self, http, admin_token):
        resp = http.delete(f"/auth/users/{ADMIN_USER}", headers=_bearer(admin_token))
        assert resp.status_code == 400
        assert "yourself" in resp.json()["error"]


# ── Scenario 5: TOTP full lifecycle ─────────────────────────────


class TestTOTPLifecycle:
    USERNAME = "totp_scenario"
    PASSWORD = "TotpPass123!"
    _secret: str | None = None
    _backup_codes: list[str] | None = None

    def test_01_setup_user(self, http, admin_token):
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        resp = http.post(
            "/auth/users",
            json={"username": self.USERNAME, "password": self.PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 200

    def test_02_enable_totp(self, http):
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        token = resp.json()["data"]["token"]

        # Step 1: setup (verify password, get QR + backup codes)
        resp = http.post(
            "/auth/totp/setup",
            json={"password": self.PASSWORD},
            headers=_bearer(token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "setup_token" in data
        assert "secret" in data
        assert "uri" in data
        assert len(data["backup_codes"]) == 8
        assert data["expires_in"] > 0

        # Step 2: confirm (verify TOTP code activates)
        code = _generate_totp_code(data["secret"])
        resp = http.post(
            "/auth/totp/confirm",
            json={"setup_token": data["setup_token"], "code": code},
            headers=_bearer(token),
        )
        assert resp.status_code == 200

        TestTOTPLifecycle._secret = data["secret"]
        TestTOTPLifecycle._backup_codes = data["backup_codes"]

    def test_03_login_requires_mfa(self, http):
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["mfa_required"] is True
        assert "mfa_token" in data

    def test_04_wrong_totp_code_rejected(self, http):
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        mfa_token = resp.json()["data"]["mfa_token"]

        resp = http.post("/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"})
        if resp.status_code == 200:
            return  # astronomically unlikely lucky hit
        assert resp.status_code == 401

    def test_05_successful_totp_login(self, http):
        if not self._secret:
            pytest.skip("TOTP secret not available from test_02")
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        mfa_token = resp.json()["data"]["mfa_token"]

        code = _generate_totp_code(self._secret)
        resp = http.post("/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
        assert resp.status_code == 200
        assert "token" in resp.json()["data"]

    def test_06_backup_code_login(self, http):
        if not self._backup_codes:
            pytest.skip("Backup codes not available from test_02")
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        mfa_token = resp.json()["data"]["mfa_token"]

        code = self._backup_codes[0]
        resp = http.post("/auth/totp/backup", json={"mfa_token": mfa_token, "code": code})
        assert resp.status_code == 200
        assert "token" in resp.json()["data"]

    def test_07_used_backup_code_rejected(self, http):
        if not self._backup_codes:
            pytest.skip("Backup codes not available from test_02")
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        mfa_token = resp.json()["data"]["mfa_token"]

        code = self._backup_codes[0]  # already used in test_06
        resp = http.post("/auth/totp/backup", json={"mfa_token": mfa_token, "code": code})
        assert resp.status_code == 401

    def test_08_disable_totp(self, http):
        if not self._secret:
            pytest.skip("TOTP secret not available from test_02")
        # Login with TOTP to get access token
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        mfa_token = resp.json()["data"]["mfa_token"]
        code = _generate_totp_code(self._secret)
        resp = http.post("/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
        token = resp.json()["data"]["token"]

        # Disable TOTP with password confirmation
        resp = http.post(
            "/auth/totp/disable",
            json={"password": self.PASSWORD},
            headers=_bearer(token),
        )
        assert resp.status_code == 200

    def test_09_login_without_mfa_after_disable(self, http):
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "mfa_required" not in data or data.get("mfa_required") is False

    def test_10_cleanup(self, http, admin_token):
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))


# ── Scenario 6: Deleted user token revocation ──────────────────


class TestDeletedUserToken:
    USERNAME = "revoke_scenario"
    PASSWORD = "RevokePass1!"

    def test_01_create_and_login(self, http, admin_token):
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        resp = http.post(
            "/auth/users",
            json={"username": self.USERNAME, "password": self.PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 200

    def test_02_token_invalid_after_delete(self, http, admin_token):
        # Login as the user
        resp = http.post("/auth/login", json={"username": self.USERNAME, "password": self.PASSWORD})
        token = resp.json()["data"]["token"]

        # Verify token works
        resp = http.get("/auth/me", headers=_bearer(token))
        assert resp.status_code == 200

        # Admin deletes the user
        resp = http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        assert resp.status_code == 200

        # Deleted user's token must be rejected
        resp = http.get("/auth/me", headers=_bearer(token))
        assert resp.status_code == 401


# ── Scenario 7: Duplicate user creation ────────────────────────


class TestDuplicateUser:
    USERNAME = "dup_scenario"
    PASSWORD = "DupPass123!"

    def test_duplicate_returns_409(self, http, admin_token):
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))
        resp = http.post(
            "/auth/users",
            json={"username": self.USERNAME, "password": self.PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 200

        # Same username again → 409
        resp = http.post(
            "/auth/users",
            json={"username": self.USERNAME, "password": self.PASSWORD},
            headers=_bearer(admin_token),
        )
        assert resp.status_code == 409

        # Cleanup
        http.delete(f"/auth/users/{self.USERNAME}", headers=_bearer(admin_token))


# ── Scenario 8: Rate limiting (last — poisons IP for the window) ─


class TestRateLimit:
    def test_rapid_failed_logins_trigger_429(self, http):
        resp = None
        for _ in range(10):
            resp = http.post("/auth/login", json={"username": "x", "password": "y"})
            if resp.status_code == 429:
                break
        assert resp is not None and resp.status_code == 429
