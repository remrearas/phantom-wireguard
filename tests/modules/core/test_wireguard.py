"""Integration tests for /api/core/wireguard endpoints.

Device status overview and peer lookup with client enrichment.
"""

from __future__ import annotations

import pytest


class TestWireGuardStatus:

    @pytest.mark.dependency()
    def test_status_overview(self, client, test_env):
        """Device overview — response structure and consistency."""
        # Sync IPC so device has listen_port set
        te = test_env
        te.wg.fast_sync(
            wallet=te.wallet, server_keys=te.server_keys, env=te.env,
        )

        resp = client.get("/api/core/wireguard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]

        # Interface info
        assert "interface" in data
        assert data["interface"]["listen_port"] == te.env.listen_port
        assert "public_key" in data["interface"]

        # Peers match wallet
        wallet_count = te.wallet.count_assigned()
        assert data["total_peers"] == wallet_count
        assert len(data["peers"]) == wallet_count

    @pytest.mark.dependency(depends=["TestWireGuardStatus::test_status_overview"])
    def test_status_with_peer(self, client, test_env):
        """After assign, peer appears in status with name enrichment."""
        te = test_env
        if te.wallet.get_client("wg_alice") is None:
            result = te.wallet.assign_client("wg_alice")
            te.wg.add_peer(result, te.env.keepalive)

        resp = client.get("/api/core/wireguard")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["total_peers"] >= 1
        names = [p["name"] for p in data["peers"]]
        assert "wg_alice" in names

        # Verify enriched peer fields
        alice = next(p for p in data["peers"] if p["name"] == "wg_alice")
        assert "public_key" in alice
        assert isinstance(alice["allowed_ips"], list)
        assert isinstance(alice["rx_bytes"], int)
        assert isinstance(alice["tx_bytes"], int)

    @pytest.mark.dependency(depends=["TestWireGuardStatus::test_status_with_peer"])
    def test_peer_by_name(self, client):
        """Lookup specific peer by client name."""
        resp = client.post(
            "/api/core/wireguard/peer",
            json={"name": "wg_alice"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["name"] == "wg_alice"
        assert "public_key" in data
        assert isinstance(data["allowed_ips"], list)

    def test_peer_not_found(self, client):
        """404 for nonexistent client."""
        resp = client.post(
            "/api/core/wireguard/peer",
            json={"name": "ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["ok"] is False
