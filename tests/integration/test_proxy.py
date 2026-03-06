from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from auth_service.middleware.rate_limit import RateLimiter


@pytest.fixture()
def mock_daemon():
    """Mock httpx async client returning daemon-like responses."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "data": {"clients": []}}
    mock_response.headers = {"content-type": "application/json"}

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    return mock_client


def test_proxy_get(auth_env, mock_daemon):
    auth_env.create_user("proxyuser", "proxypass1")
    token = auth_env.issue_token("proxyuser")
    client = auth_env.make_client(
        proxy_client=mock_daemon,
        rate_limiter=RateLimiter(window=60, max_attempts=100),
    )
    resp = client.get("/api/core/clients/list", headers=auth_env.bearer(token))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_proxy_post(auth_env, mock_daemon):
    auth_env.create_user("proxypost", "proxypass1")
    token = auth_env.issue_token("proxypost")
    client = auth_env.make_client(
        proxy_client=mock_daemon,
        rate_limiter=RateLimiter(window=60, max_attempts=100),
    )
    resp = client.post(
        "/api/core/clients/assign",
        json={"name": "test"},
        headers=auth_env.bearer(token),
    )
    assert resp.status_code == 200


def test_proxy_no_auth(auth_env, mock_daemon):
    client = auth_env.make_client(proxy_client=mock_daemon)
    resp = client.get("/api/core/clients/list")
    assert resp.status_code == 401


def test_proxy_revoked_token(auth_env, mock_daemon):
    auth_env.create_user("revoked", "revokepass")
    token = auth_env.issue_token("revoked")
    # Revoke the session
    from auth_service.crypto.jwt import decode_token
    payload = decode_token(auth_env.verify_key, token)
    auth_env.db.revoke_session(payload.jti)

    client = auth_env.make_client(proxy_client=mock_daemon)
    resp = client.get("/api/core/clients/list", headers=auth_env.bearer(token))
    assert resp.status_code == 401
