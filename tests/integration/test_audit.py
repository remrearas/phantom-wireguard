from __future__ import annotations

from auth_service.middleware.rate_limit import RateLimiter


def test_audit_log_on_failed_login(auth_env):
    auth_env.create_user("audituser", "auditpw12")
    client = auth_env.make_client()
    client.post("/auth/login", json={"username": "audituser", "password": "wrong"})
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "login_failed" for l in logs)


def test_audit_log_on_successful_login(auth_env):
    auth_env.create_user("auditok", "auditpw12")
    client = auth_env.make_client()
    client.post("/auth/login", json={"username": "auditok", "password": "auditpw12"})
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "login_success" for l in logs)


def test_audit_log_on_user_create(auth_env):
    auth_env.create_user("audadmin", "adminpw12")
    token = auth_env.login("audadmin", "adminpw12")
    client = auth_env.make_client()
    client.post(
        "/auth/users",
        json={"username": "newaudit", "password": "newpw1234"},
        headers=auth_env.bearer(token),
    )
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "user_created" for l in logs)


def test_audit_log_on_logout(auth_env):
    auth_env.create_user("logoutaud", "logpw1234")
    token = auth_env.login("logoutaud", "logpw1234")
    client = auth_env.make_client()
    client.post("/auth/logout", headers=auth_env.bearer(token))
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "logout" for l in logs)


def test_audit_log_on_totp_enable(auth_env):
    auth_env.create_user("totpaud", "totppw123")
    token = auth_env.login("totpaud", "totppw123")
    client = auth_env.make_client()
    client.post("/auth/totp/enable", headers=auth_env.bearer(token))
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "totp_enabled" for l in logs)


def test_audit_log_on_rate_limit(auth_env):
    client = auth_env.make_client(rate_limiter=RateLimiter(window=60, max_attempts=1))
    client.post("/auth/login", json={"username": "x", "password": "y"})
    client.post("/auth/login", json={"username": "x", "password": "y"})
    logs = auth_env.db.get_audit_logs()
    assert any(l["action"] == "login_rate_limited" for l in logs)
