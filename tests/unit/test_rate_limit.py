from __future__ import annotations

import time

from auth_service.middleware.rate_limit import RateLimiter


def test_allows_under_limit():
    rl = RateLimiter(window=60, max_attempts=3)
    assert rl.check("1.2.3.4") is True
    assert rl.check("1.2.3.4") is True
    assert rl.check("1.2.3.4") is True


def test_blocks_over_limit():
    rl = RateLimiter(window=60, max_attempts=2)
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is False


def test_different_ips_independent():
    rl = RateLimiter(window=60, max_attempts=1)
    assert rl.check("10.0.0.1") is True
    assert rl.check("10.0.0.1") is False
    assert rl.check("10.0.0.2") is True


def test_reset():
    rl = RateLimiter(window=60, max_attempts=1)
    assert rl.check("5.5.5.5") is True
    assert rl.check("5.5.5.5") is False
    rl.reset("5.5.5.5")
    assert rl.check("5.5.5.5") is True


def test_window_expiry():
    rl = RateLimiter(window=1, max_attempts=1)
    assert rl.check("9.9.9.9") is True
    assert rl.check("9.9.9.9") is False
    time.sleep(1.1)
    assert rl.check("9.9.9.9") is True
