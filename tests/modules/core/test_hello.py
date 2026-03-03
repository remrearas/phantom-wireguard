"""Tests for GET /api/core/hello endpoint."""

from __future__ import annotations

from starlette.testclient import TestClient

from phantom_daemon import __version__


class TestHelloEndpoint:
    def test_status_code(self, client: TestClient) -> None:
        resp = client.get("/api/core/hello")
        assert resp.status_code == 200

    def test_content_type(self, client: TestClient) -> None:
        resp = client.get("/api/core/hello")
        assert resp.headers["content-type"] == "application/json"

    def test_body_message(self, client: TestClient) -> None:
        resp = client.get("/api/core/hello")
        data = resp.json()
        assert data["message"] == "phantom-daemon is alive"

    def test_body_version(self, client: TestClient) -> None:
        resp = client.get("/api/core/hello")
        data = resp.json()
        assert data["version"] == __version__

    def test_response_keys(self, client: TestClient) -> None:
        resp = client.get("/api/core/hello")
        assert set(resp.json().keys()) == {"message", "version"}
