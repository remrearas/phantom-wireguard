"""Integration tests for /api/core/network endpoints.

API call → response check → DB state exact verification.
Tests are ordered via pytest-dependency within the class.
"""

from __future__ import annotations

import pytest


class TestNetworkEndpoints:

    def test_get_status(self, client, test_env):
        resp = client.get("/api/core/network")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]

        # Structure
        assert "ipv4_subnet" in data
        assert "ipv6_subnet" in data
        assert "dns_v4" in data
        assert "dns_v6" in data
        assert "pool" in data

        # DB consistency
        wallet = test_env.wallet
        assert data["ipv4_subnet"] == wallet.get_config("ipv4_subnet")
        assert data["ipv6_subnet"] == wallet.get_config("ipv6_subnet")
        assert data["pool"]["total"] == wallet.count_users()
        assert data["pool"]["assigned"] == wallet.count_assigned()
        assert data["pool"]["free"] == wallet.count_free()

    def test_validate_pool(self, client):
        resp = client.get("/api/core/network/validate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["valid"] is True
        assert data["errors"] == []

    @pytest.mark.dependency()
    def test_change_cidr(self, client, test_env):
        resp = client.post("/api/core/network/cidr", json={"prefix": 22})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["ipv4_subnet"] == "10.8.0.0/22"
        assert data["ipv6_subnet"] == "fd00:70:68::/118"
        assert data["pool"]["total"] == 1021

        # DB state
        wallet = test_env.wallet
        assert wallet.get_config("ipv4_subnet") == "10.8.0.0/22"
        assert wallet.get_config("ipv6_subnet") == "fd00:70:68::/118"
        assert wallet.count_users() == 1021

    @pytest.mark.dependency(depends=["TestNetworkEndpoints::test_change_cidr"])
    def test_get_status_after_cidr(self, client, test_env):
        resp = client.get("/api/core/network")
        data = resp.json()["data"]
        wallet = test_env.wallet
        assert data["ipv4_subnet"] == "10.8.0.0/22"
        assert data["ipv6_subnet"] == "fd00:70:68::/118"
        assert data["pool"]["total"] == wallet.count_users()
        assert data["pool"]["assigned"] == wallet.count_assigned()

    @pytest.mark.dependency(depends=["TestNetworkEndpoints::test_change_cidr"])
    def test_validate_after_cidr(self, client):
        resp = client.get("/api/core/network/validate")
        data = resp.json()["data"]
        assert data["valid"] is True
        assert data["errors"] == []

    def test_invalid_prefix_low(self, client):
        resp = client.post("/api/core/network/cidr", json={"prefix": 8})
        assert resp.status_code == 422
        assert resp.json()["ok"] is False

    def test_invalid_prefix_high(self, client):
        resp = client.post("/api/core/network/cidr", json={"prefix": 31})
        assert resp.status_code == 422
        assert resp.json()["ok"] is False
