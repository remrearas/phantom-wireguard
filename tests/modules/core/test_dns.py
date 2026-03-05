"""Integration tests for /api/dns endpoints.

API call → response check → DB state exact verification.
Tests are ordered via pytest-dependency within the class.
"""

from __future__ import annotations

import pytest


class TestDnsEndpoints:

    def test_get_v4_default(self, client, test_env):
        resp = client.post("/api/dns/get", json={"family": "v4"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["family"] == "v4"
        assert data["primary"] == "9.9.9.9"
        assert data["secondary"] == "149.112.112.112"

    def test_get_v6_default(self, client, test_env):
        resp = client.post("/api/dns/get", json={"family": "v6"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["family"] == "v6"
        assert data["primary"] == "2620:fe::fe"
        assert data["secondary"] == "2620:fe::9"

    @pytest.mark.dependency()
    def test_change_v4(self, client, test_env):
        resp = client.post("/api/dns/change", json={
            "family": "v4",
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["family"] == "v4"
        assert data["primary"] == "1.1.1.1"
        assert data["secondary"] == "1.0.0.1"

        # DB state
        dns = test_env.wallet.get_dns("v4")
        assert dns["primary"] == "1.1.1.1"
        assert dns["secondary"] == "1.0.0.1"

    @pytest.mark.dependency(depends=["TestDnsEndpoints::test_change_v4"])
    def test_get_v4_after_change(self, client):
        resp = client.post("/api/dns/get", json={"family": "v4"})
        data = resp.json()["data"]
        assert data["primary"] == "1.1.1.1"
        assert data["secondary"] == "1.0.0.1"

    @pytest.mark.dependency()
    def test_change_v6(self, client, test_env):
        resp = client.post("/api/dns/change", json={
            "family": "v6",
            "primary": "2001:4860:4860::8888",
            "secondary": "2001:4860:4860::8844",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["primary"] == "2001:4860:4860::8888"
        assert data["secondary"] == "2001:4860:4860::8844"

        # DB state
        dns = test_env.wallet.get_dns("v6")
        assert dns["primary"] == "2001:4860:4860::8888"
        assert dns["secondary"] == "2001:4860:4860::8844"

    @pytest.mark.dependency(depends=["TestDnsEndpoints::test_change_v6"])
    def test_get_v6_after_change(self, client):
        resp = client.post("/api/dns/get", json={"family": "v6"})
        data = resp.json()["data"]
        assert data["primary"] == "2001:4860:4860::8888"
        assert data["secondary"] == "2001:4860:4860::8844"

    def test_invalid_family(self, client):
        resp = client.post("/api/dns/get", json={"family": "v5"})
        assert resp.status_code == 422
        assert resp.json()["ok"] is False

    def test_change_invalid_ip(self, client):
        resp = client.post("/api/dns/change", json={
            "family": "v4",
            "primary": "not-an-ip",
            "secondary": "1.0.0.1",
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert "error" in body
