from __future__ import annotations

from auth_service.crypto.totp import generate_secret, hash_backup_code


# ── Login ────────────────────────────────────────────────────────


def test_login_success(auth_env):
    auth_env.create_user("testuser", "testpass1")
    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "testuser", "password": "testpass1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data["data"]
    assert data["data"]["expires_in"] == 3600


def test_login_wrong_password(auth_env):
    auth_env.create_user("wrongpw", "correct1")
    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "wrongpw", "password": "incorrect"})
    assert resp.status_code == 401
    assert resp.json()["ok"] is False


def test_login_nonexistent_user(auth_env):
    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "ghost", "password": "pass"})
    assert resp.status_code == 401


# ── Me / Logout ──────────────────────────────────────────────────


def test_me(auth_env):
    auth_env.create_user("meuser", "mepass123")
    token = auth_env.login("meuser", "mepass123")
    client = auth_env.make_client()
    resp = client.get("/auth/me", headers=auth_env.bearer(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "meuser"
    assert resp.json()["data"]["totp_enabled"] is False


def test_me_no_auth(auth_env):
    client = auth_env.make_client()
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_logout_revokes_token(auth_env):
    auth_env.create_user("logoutuser", "logpass12")
    token = auth_env.login("logoutuser", "logpass12")
    client = auth_env.make_client()
    resp = client.post("/auth/logout", headers=auth_env.bearer(token))
    assert resp.status_code == 200
    resp = client.get("/auth/me", headers=auth_env.bearer(token))
    assert resp.status_code == 401


# ── User Management ─────────────────────────────────────────────


def test_create_user(auth_env):
    auth_env.create_user("admin", "adminpass1")
    token = auth_env.login("admin", "adminpass1")
    client = auth_env.make_client()
    resp = client.post(
        "/auth/users",
        json={"username": "newuser", "password": "newpass123"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "newuser"


def test_list_users(auth_env):
    auth_env.create_user("admin", "adminpass1")
    token = auth_env.login("admin", "adminpass1")
    client = auth_env.make_client()
    resp = client.get("/auth/users", headers=auth_env.bearer(token))
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_delete_user(auth_env):
    auth_env.create_user("admin", "adminpass1")
    auth_env.create_user("todelete", "del12345")
    token = auth_env.login("admin", "adminpass1")
    client = auth_env.make_client()
    resp = client.delete("/auth/users/todelete", headers=auth_env.bearer(token))
    assert resp.status_code == 200


def test_delete_self_forbidden(auth_env):
    auth_env.create_user("admin", "adminpass1")
    token = auth_env.login("admin", "adminpass1")
    client = auth_env.make_client()
    resp = client.delete("/auth/users/admin", headers=auth_env.bearer(token))
    assert resp.status_code == 400
    assert "yourself" in resp.json()["error"]


def test_change_password(auth_env):
    auth_env.create_user("chpw", "oldpass12")
    token = auth_env.login("chpw", "oldpass12")
    client = auth_env.make_client()
    resp = client.post(
        "/auth/users/chpw/password",
        json={"password": "newpass123"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 200


def test_create_user_duplicate(auth_env):
    auth_env.create_user("admin", "adminpass1")
    auth_env.create_user("dup", "duppass12")
    token = auth_env.login("admin", "adminpass1")
    client = auth_env.make_client()
    resp = client.post(
        "/auth/users",
        json={"username": "dup", "password": "duppass12"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 409


# ── MFA Login Flow ───────────────────────────────────────────────


def test_login_with_totp_returns_mfa_required(auth_env):
    user = auth_env.create_user("mfauser", "mfapass12")
    secret = generate_secret()
    auth_env.db.set_totp_secret(user.id, secret)

    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "mfauser", "password": "mfapass12"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mfa_required"] is True
    assert "mfa_token" in data


def test_mfa_verify_success(auth_env):
    import base64, hashlib, hmac, struct, time

    user = auth_env.create_user("mfaver", "mfapass12")
    secret = generate_secret()
    auth_env.db.set_totp_secret(user.id, secret)

    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "mfaver", "password": "mfapass12"})
    mfa_token = resp.json()["data"]["mfa_token"]

    # Generate valid TOTP code
    key = base64.b32decode(secret)
    counter = struct.pack(">Q", int(time.time()) // 30)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    truncated = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    code = str(truncated % 1000000).zfill(6)

    resp = client.post("/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert resp.status_code == 200
    assert "token" in resp.json()["data"]


def test_mfa_backup_code_login(auth_env):
    user = auth_env.create_user("mfaback", "mfapass12")
    secret = generate_secret()
    auth_env.db.set_totp_secret(user.id, secret)

    backup_code = "testback"
    auth_env.db.store_backup_codes(user.id, [hash_backup_code(backup_code)])

    client = auth_env.make_client()
    resp = client.post("/auth/login", json={"username": "mfaback", "password": "mfapass12"})
    mfa_token = resp.json()["data"]["mfa_token"]

    resp = client.post("/auth/totp/backup", json={"mfa_token": mfa_token, "code": backup_code})
    assert resp.status_code == 200
    assert "token" in resp.json()["data"]


def test_mfa_backup_code_single_use(auth_env):
    user = auth_env.create_user("mfaonce", "mfapass12")
    secret = generate_secret()
    auth_env.db.set_totp_secret(user.id, secret)

    backup_code = "onceonly"
    auth_env.db.store_backup_codes(user.id, [hash_backup_code(backup_code)])

    client = auth_env.make_client()

    # First use — success
    resp = client.post("/auth/login", json={"username": "mfaonce", "password": "mfapass12"})
    mfa_token = resp.json()["data"]["mfa_token"]
    resp = client.post("/auth/totp/backup", json={"mfa_token": mfa_token, "code": backup_code})
    assert resp.status_code == 200

    # Second use — fail
    resp = client.post("/auth/login", json={"username": "mfaonce", "password": "mfapass12"})
    mfa_token2 = resp.json()["data"]["mfa_token"]
    resp = client.post("/auth/totp/backup", json={"mfa_token": mfa_token2, "code": backup_code})
    assert resp.status_code == 401


# ── TOTP Enable / Disable ───────────────────────────────────────


def test_totp_enable(auth_env):
    auth_env.create_user("totpuser", "totppass1")
    token = auth_env.login("totpuser", "totppass1")
    client = auth_env.make_client()
    resp = client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "secret" in data
    assert "uri" in data
    assert len(data["backup_codes"]) == 8


def test_totp_enable_already_enabled(auth_env):
    auth_env.create_user("totpdup", "totppass1")
    token = auth_env.login("totpdup", "totppass1")
    client = auth_env.make_client()
    client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    resp = client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    assert resp.status_code == 409


def test_totp_disable(auth_env):
    auth_env.create_user("totpdis", "totppass1")
    token = auth_env.login("totpdis", "totppass1")
    client = auth_env.make_client()
    client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    resp = client.post(
        "/auth/totp/disable",
        json={"password": "totppass1"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 200
    resp = client.get("/auth/me", headers=auth_env.bearer(token))
    assert resp.json()["data"]["totp_enabled"] is False


def test_totp_disable_wrong_password(auth_env):
    auth_env.create_user("totpwrg", "totppass1")
    token = auth_env.login("totpwrg", "totppass1")
    client = auth_env.make_client()
    client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    resp = client.post(
        "/auth/totp/disable",
        json={"password": "wrongpass1"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 401
