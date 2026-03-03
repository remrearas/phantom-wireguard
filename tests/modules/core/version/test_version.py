"""Tests for /api/core/version endpoints."""

from __future__ import annotations

from starlette.testclient import TestClient

from phantom_daemon import __version__


BRIDGE_SLUGS = ["wireguard-go-bridge", "firewall-bridge", "wstunnel-bridge"]


class TestAllVersions:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/api/core/version")
        assert resp.status_code == 200

    def test_daemon_version(self, client: TestClient) -> None:
        data = client.get("/api/core/version").json()
        assert data["daemon"] == __version__

    def test_all_bridges_listed(self, client: TestClient) -> None:
        bridges = client.get("/api/core/version").json()["bridges"]
        names = [b["name"] for b in bridges]
        assert names == BRIDGE_SLUGS

    def test_bridge_fields(self, client: TestClient) -> None:
        bridges = client.get("/api/core/version").json()["bridges"]
        for bridge in bridges:
            assert "name" in bridge
            assert "version" in bridge
            assert "available" in bridge


class TestIndividualBridge:
    def test_wireguard_go_bridge(self, client: TestClient) -> None:
        resp = client.get("/api/core/version/wireguard-go-bridge")
        assert resp.status_code == 200
        assert resp.json()["name"] == "wireguard-go-bridge"

    def test_firewall_bridge(self, client: TestClient) -> None:
        resp = client.get("/api/core/version/firewall-bridge")
        assert resp.status_code == 200
        assert resp.json()["name"] == "firewall-bridge"

    def test_wstunnel_bridge(self, client: TestClient) -> None:
        resp = client.get("/api/core/version/wstunnel-bridge")
        assert resp.status_code == 200
        assert resp.json()["name"] == "wstunnel-bridge"