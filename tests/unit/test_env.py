"""Tests for phantom_daemon.base.env — environment variable loading."""

from __future__ import annotations

import pytest

from phantom_daemon.base.env import DaemonEnv, load_env


class TestLoadEnv:
    def test_defaults(self, monkeypatch):
        # Clear all relevant env vars
        for var in (
            "PHANTOM_DB_DIR",
            "WIREGUARD_LISTEN_PORT",
            "WIREGUARD_MTU",
            "WIREGUARD_KEEPALIVE",
            "WIREGUARD_ENDPOINT_V4",
            "WIREGUARD_ENDPOINT_V6",
        ):
            monkeypatch.delenv(var, raising=False)

        env = load_env()
        assert env.db_dir == "/var/lib/phantom/db"
        assert env.listen_port == 51820
        assert env.mtu == 1420
        assert env.keepalive == 25
        assert env.endpoint_v4 == ""
        assert env.endpoint_v6 == ""

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("PHANTOM_DB_DIR", "/tmp/test-db")
        monkeypatch.setenv("WIREGUARD_LISTEN_PORT", "12345")
        monkeypatch.setenv("WIREGUARD_MTU", "1500")
        monkeypatch.setenv("WIREGUARD_KEEPALIVE", "10")
        monkeypatch.setenv("WIREGUARD_ENDPOINT_V4", "1.2.3.4")
        monkeypatch.setenv("WIREGUARD_ENDPOINT_V6", "::1")

        env = load_env()
        assert env.db_dir == "/tmp/test-db"
        assert env.listen_port == 12345
        assert env.mtu == 1500
        assert env.keepalive == 10
        assert env.endpoint_v4 == "1.2.3.4"
        assert env.endpoint_v6 == "::1"

    def test_frozen(self, monkeypatch):
        for var in (
            "PHANTOM_DB_DIR",
            "WIREGUARD_LISTEN_PORT",
            "WIREGUARD_MTU",
            "WIREGUARD_KEEPALIVE",
            "WIREGUARD_ENDPOINT_V4",
            "WIREGUARD_ENDPOINT_V6",
        ):
            monkeypatch.delenv(var, raising=False)

        env = load_env()
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            env.db_dir = "/other"  # type: ignore[misc]

    def test_instance_type(self, monkeypatch):
        for var in (
            "PHANTOM_DB_DIR",
            "WIREGUARD_LISTEN_PORT",
            "WIREGUARD_MTU",
            "WIREGUARD_KEEPALIVE",
            "WIREGUARD_ENDPOINT_V4",
            "WIREGUARD_ENDPOINT_V6",
        ):
            monkeypatch.delenv(var, raising=False)

        env = load_env()
        assert isinstance(env, DaemonEnv)
