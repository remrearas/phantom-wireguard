from __future__ import annotations

from auth_service.middleware.rate_limit import RateLimiter


def test_rate_limit_blocks_login_endpoint(auth_env):
    client = auth_env.make_client(rate_limiter=RateLimiter(window=60, max_attempts=2))
    for _ in range(2):
        client.post("/auth/login", json={"username": "x", "password": "y"})
    resp = client.post("/auth/login", json={"username": "x", "password": "y"})
    assert resp.status_code == 429
