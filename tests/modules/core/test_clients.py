"""Integration tests for /api/core/clients endpoints.

API call → response check → DB state exact verification.
Tests are ordered via pytest-dependency within the class.
"""

from __future__ import annotations

import pytest


class TestClientEndpoints:

    @pytest.mark.dependency()
    def test_assign_first(self, client, wallet):
        resp = client.post("/api/core/clients", json={"name": "alice"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "alice"
        assert "ipv4_address" in data
        assert "private_key_hex" in data
        assert "preshared_key_hex" in data
        assert "created_at" in data

        # DB state
        db = wallet.get_client("alice")
        assert db is not None
        assert db["name"] == "alice"
        assert db["ipv4_address"] == data["ipv4_address"]
        assert db["ipv6_address"] == data["ipv6_address"]
        assert db["private_key_hex"] == data["private_key_hex"]
        assert db["public_key_hex"] == data["public_key_hex"]

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_assign_first"])
    def test_assign_second(self, client, wallet):
        resp = client.post("/api/core/clients", json={"name": "bob"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "bob"

        # DB state
        assert wallet.count_assigned() == 2

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_assign_second"])
    def test_list_all(self, client, wallet):
        resp = client.get("/api/core/clients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {c["name"] for c in data["clients"]}
        assert names == {"alice", "bob"}

        # Summary format — no secret keys
        for c in data["clients"]:
            assert "public_key_hex" in c
            assert "private_key_hex" not in c
            assert "preshared_key_hex" not in c

        # DB state
        assert data["total"] == wallet.count_assigned()

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_assign_first"])
    def test_get_detail(self, client, wallet):
        resp = client.get("/api/core/clients/alice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "alice"
        assert "private_key_hex" in data
        assert "preshared_key_hex" in data

        # Exact match with DB
        db = wallet.get_client("alice")
        for key in ("id", "name", "ipv4_address", "ipv6_address",
                     "private_key_hex", "public_key_hex", "preshared_key_hex"):
            assert data[key] == db[key], f"Mismatch on {key}"

    def test_get_nonexistent(self, client):
        resp = client.get("/api/core/clients/ghost")
        assert resp.status_code == 404

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_assign_first"])
    def test_assign_duplicate(self, client):
        resp = client.post("/api/core/clients", json={"name": "alice"})
        assert resp.status_code == 400
        assert resp.json()["error"] == "wallet_error"

    def test_assign_invalid_name(self, client):
        resp = client.post("/api/core/clients", json={"name": "bad name!"})
        assert resp.status_code == 422

    def test_assign_empty_name(self, client):
        resp = client.post("/api/core/clients", json={"name": ""})
        assert resp.status_code == 422

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_list_all"])
    def test_revoke(self, client, wallet):
        resp = client.delete("/api/core/clients/alice")
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

        # DB state
        assert wallet.get_client("alice") is None

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_revoke"])
    def test_revoke_already_revoked(self, client):
        resp = client.delete("/api/core/clients/alice")
        assert resp.status_code == 400
        assert resp.json()["error"] == "wallet_error"

    @pytest.mark.dependency(depends=["TestClientEndpoints::test_revoke"])
    def test_list_after_revoke(self, client, wallet):
        resp = client.get("/api/core/clients")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["clients"][0]["name"] == "bob"

        # DB state
        assert wallet.count_assigned() == 1
        assert wallet.count_free() == wallet.count_users() - 1
