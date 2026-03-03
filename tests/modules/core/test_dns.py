"""Integration tests for /api/core/dns endpoints.

API call → response check → DB state exact verification.
Tests are ordered via pytest-dependency within the class.
"""

from __future__ import annotations

import pytest


class TestDnsEndpoints:

    def test_get_v4_default(self, client):
        resp = client.get("/api/core/dns/v4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["family"] == "v4"
        assert data["primary"] == "9.9.9.9"
        assert data["secondary"] == "149.112.112.112"

    def test_get_v6_default(self, client):
        resp = client.get("/api/core/dns/v6")
        assert resp.status_code == 200
        data = resp.json()
        assert data["family"] == "v6"
        assert data["primary"] == "2620:fe::fe"
        assert data["secondary"] == "2620:fe::9"

    @pytest.mark.dependency()
    def test_change_v4(self, client, wallet):
        resp = client.put("/api/core/dns/v4", json={
            "primary": "1.1.1.1",
            "secondary": "1.0.0.1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["family"] == "v4"
        assert data["primary"] == "1.1.1.1"
        assert data["secondary"] == "1.0.0.1"

        # DB state
        dns = wallet.get_dns("v4")
        assert dns["primary"] == "1.1.1.1"
        assert dns["secondary"] == "1.0.0.1"

    @pytest.mark.dependency(depends=["TestDnsEndpoints::test_change_v4"])
    def test_get_v4_after_change(self, client):
        resp = client.get("/api/core/dns/v4")
        data = resp.json()
        assert data["primary"] == "1.1.1.1"
        assert data["secondary"] == "1.0.0.1"

    @pytest.mark.dependency()
    def test_change_v6(self, client, wallet):
        resp = client.put("/api/core/dns/v6", json={
            "primary": "2001:4860:4860::8888",
            "secondary": "2001:4860:4860::8844",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["primary"] == "2001:4860:4860::8888"
        assert data["secondary"] == "2001:4860:4860::8844"

        # DB state
        dns = wallet.get_dns("v6")
        assert dns["primary"] == "2001:4860:4860::8888"
        assert dns["secondary"] == "2001:4860:4860::8844"

    @pytest.mark.dependency(depends=["TestDnsEndpoints::test_change_v6"])
    def test_get_v6_after_change(self, client):
        resp = client.get("/api/core/dns/v6")
        data = resp.json()
        assert data["primary"] == "2001:4860:4860::8888"
        assert data["secondary"] == "2001:4860:4860::8844"

    def test_invalid_family(self, client):
        resp = client.get("/api/core/dns/v5")
        assert resp.status_code == 422

    def test_change_invalid_ip(self, client):
        resp = client.put("/api/core/dns/v4", json={
            "primary": "not-an-ip",
            "secondary": "1.0.0.1",
        })
        assert resp.status_code == 400
        assert resp.json()["error"] == "wallet_error"
