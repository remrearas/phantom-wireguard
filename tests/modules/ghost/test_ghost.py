"""Integration tests for /api/ghost endpoints.

TLS validation (invalid cert, invalid key, keypair mismatch)
+ full enable/disable lifecycle with wstunnel + firewall presets.

Tests run inside the daemon container via tools/dev.sh test.
"""

from __future__ import annotations

import base64
import subprocess
import tempfile

import pytest


# ── Helpers ─────────────────────────────────────────────────────


def _generate_keypair(cn: str = "ghost.test.local") -> tuple[str, str]:
    """Generate ECDSA P-256 self-signed cert + key pair via openssl."""
    with tempfile.TemporaryDirectory() as d:
        key = f"{d}/key.pem"
        cert = f"{d}/cert.pem"
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "ec",
                "-pkeyopt", "ec_paramgen_curve:prime256v1",
                "-keyout", key, "-out", cert,
                "-days", "1", "-nodes", "-subj", f"/CN={cn}",
            ],
            check=True,
            capture_output=True,
        )
        with open(cert) as f:
            cert_pem = f.read()
        with open(key) as f:
            key_pem = f.read()
    return cert_pem, key_pem


def _b64(pem: str) -> str:
    """Base64-encode a PEM string (daemon expects this format)."""
    return base64.b64encode(pem.encode()).decode()


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def ghost_cert_a():
    """Matching cert + key pair A."""
    return _generate_keypair()


@pytest.fixture(scope="session")
def ghost_cert_b():
    """Matching cert + key pair B (different key — for mismatch test)."""
    return _generate_keypair("other.test.local")


# ── Tests ───────────────────────────────────────────────────────


class TestGhostEndpoints:

    # ── Status baseline ────────────────────────────────────────

    def test_status_disabled_by_default(self, client):
        resp = client.get("/api/ghost/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["enabled"] is False
        assert data["running"] is False
        assert data["bind_url"] == ""
        assert data["restrict_path_prefix"] == ""
        assert data["tls_configured"] is False

    # ── TLS validation ─────────────────────────────────────────

    def test_enable_invalid_cert_base64(self, client):
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": "!!!not-base64!!!",
            "tls_private_key": _b64("dummy"),
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert body["code"] == "INVALID_TLS_CERTIFICATE"

    def test_enable_invalid_key_base64(self, client, ghost_cert_a):
        cert_pem, _ = ghost_cert_a
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": _b64(cert_pem),
            "tls_private_key": "!!!not-base64!!!",
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert body["code"] == "INVALID_TLS_PRIVATE_KEY"

    def test_enable_keypair_mismatch(self, client, ghost_cert_a, ghost_cert_b):
        cert_pem_a, _ = ghost_cert_a
        _, key_pem_b = ghost_cert_b
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": _b64(cert_pem_a),
            "tls_private_key": _b64(key_pem_b),
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert body["code"] == "TLS_KEYPAIR_MISMATCH"

    def test_enable_garbage_cert_content(self, client):
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": _b64("not a certificate"),
            "tls_private_key": _b64("not a key"),
        })
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert body["code"] == "TLS_KEYPAIR_MISMATCH"

    # ── Full lifecycle ─────────────────────────────────────────

    def test_enable_disable_lifecycle(self, client, ghost_cert_a):
        """Single test covering the complete ghost mode lifecycle.

        Uses one client fixture invocation so app.state.wstunnel
        persists across all assertions within the test.
        """
        cert_pem, key_pem = ghost_cert_a

        # ── Enable ─────────────────────────────────────────
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": _b64(cert_pem),
            "tls_private_key": _b64(key_pem),
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert data["status"] == "enabled"
        assert data["code"] == "GHOST_ENABLED"
        assert data["domain"] == "ghost.test.local"
        assert data["protocol"] == "wss"
        assert data["port"] == 443
        assert len(data["restrict_path_prefix"]) == 32

        # ── Status (enabled) ──────────────────────────────
        resp = client.get("/api/ghost/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["enabled"] is True
        assert data["running"] is True
        assert data["bind_url"] == "wss://[::]:443"
        assert data["tls_configured"] is True
        assert len(data["restrict_path_prefix"]) == 32

        # ── Enable again → conflict ──────────────────────
        resp = client.post("/api/ghost/enable", json={
            "domain": "ghost.test.local",
            "tls_certificate": _b64(cert_pem),
            "tls_private_key": _b64(key_pem),
        })
        assert resp.status_code == 409
        assert resp.json()["code"] == "GHOST_ALREADY_ACTIVE"

        # ── Disable ───────────────────────────────────────
        resp = client.post("/api/ghost/disable")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["code"] == "GHOST_DISABLED"

        # ── Status (disabled) ─────────────────────────────
        resp = client.get("/api/ghost/status")
        data = resp.json()["data"]
        assert data["enabled"] is False
        assert data["running"] is False

        # ── Disable again → idempotent ────────────────────
        resp = client.post("/api/ghost/disable")
        assert resp.status_code == 200
        assert resp.json()["data"]["code"] == "GHOST_ALREADY_DISABLED"

    # ── Pydantic validation ────────────────────────────────────

    def test_enable_missing_domain(self, client, ghost_cert_a):
        cert_pem, key_pem = ghost_cert_a
        resp = client.post("/api/ghost/enable", json={
            "domain": "",
            "tls_certificate": _b64(cert_pem),
            "tls_private_key": _b64(key_pem),
        })
        assert resp.status_code == 422
        assert resp.json()["ok"] is False

    def test_enable_missing_fields(self, client):
        resp = client.post("/api/ghost/enable", json={"domain": "ghost.test.local"})
        assert resp.status_code == 422
        assert resp.json()["ok"] is False
