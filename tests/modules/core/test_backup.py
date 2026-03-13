"""Integration tests for /api/core/backup endpoints.

TestBackupEndpoints:
    100 client oluştur → export → 50 revoke → import → doğrula.

TestLargeBackup (slow):
    CIDR /16 genişlet (65,533 slot) → full pool assign → large export →
    state sıfırla → large import → spot-check verify → pre-test state'e dön.

Tests are ordered via pytest-dependency within each class.
"""

from __future__ import annotations

import io
import json
import tarfile

import pytest


# noinspection PyUnresolvedReferences
class TestBackupEndpoints:

    @pytest.mark.dependency()
    def test_create_100_clients(self, client, test_env):
        """Assign 100 clients to populate the wallet."""
        for i in range(100):
            name = f"backup-client-{i:03d}"
            resp = client.post(
                "/api/core/clients/assign", json={"name": name}
            )
            assert resp.status_code == 201, f"Failed to assign {name}: {resp.text}"

        assert test_env.wallet.count_assigned() >= 100

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_create_100_clients"])
    def test_export(self, client, test_env):
        """Export backup — response is a valid tar with 3 members."""
        resp = client.post("/api/core/backup/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/x-tar"
        assert "phantom-backup-" in resp.headers.get("content-disposition", "")

        # Parse tar from response bytes
        tar_bytes = io.BytesIO(resp.content)
        with tarfile.open(fileobj=tar_bytes, mode="r") as tf:
            names = {m.name for m in tf.getmembers()}
            assert names == {"wallet.db", "exit.db", "manifest.json"}

            # Validate manifest
            manifest = json.load(tf.extractfile("manifest.json"))
            assert manifest["version"] == "1.0"
            assert manifest["wallet"]["clients"] >= 100
            assert manifest["wallet"]["subnet"] == "10.8.0.0/24"

        # Store backup bytes on class for later use
        TestBackupEndpoints._backup_bytes = resp.content
        TestBackupEndpoints._backup_manifest = manifest

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_export"])
    def test_revoke_50_clients(self, client, test_env):
        """Revoke 50 clients to change state before import."""
        for i in range(50):
            name = f"backup-client-{i:03d}"
            resp = client.post(
                "/api/core/clients/revoke", json={"name": name}
            )
            assert resp.status_code == 200, f"Failed to revoke {name}: {resp.text}"

        # State changed: 50 fewer assigned clients
        pre_import_count = test_env.wallet.count_assigned()
        TestBackupEndpoints._pre_import_count = pre_import_count

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_revoke_50_clients"])
    def test_import_restores_state(self, client, test_env):
        """Import the backup → all 100 clients should be back."""
        backup_bytes = TestBackupEndpoints._backup_bytes
        original_manifest = TestBackupEndpoints._backup_manifest
        pre_import_count = TestBackupEndpoints._pre_import_count

        resp = client.post(
            "/api/core/backup/import",
            files={"file": ("backup.tar", backup_bytes, "application/x-tar")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True

        result = body["data"]
        assert result["wallet_clients"] == original_manifest["wallet"]["clients"]
        assert result["wallet_subnet"] == "10.8.0.0/24"

        # Verify DB state matches the original backup
        post_import_count = test_env.wallet.count_assigned()
        assert post_import_count >= 100
        assert post_import_count > pre_import_count

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_import_restores_state"])
    def test_restored_clients_intact(self, client, test_env):
        """Verify individual client data is intact after restore."""
        # Check revoked clients are back
        for i in range(50):
            name = f"backup-client-{i:03d}"
            restored = test_env.wallet.get_client(name)
            assert restored is not None, f"Client {name} should exist after restore"
            assert restored["id"] is not None
            assert restored["private_key_hex"] is not None
            assert restored["public_key_hex"] is not None

        # Check remaining clients still intact
        for i in range(50, 100):
            name = f"backup-client-{i:03d}"
            restored = test_env.wallet.get_client(name)
            assert restored is not None, f"Client {name} should exist after restore"

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_restored_clients_intact"])
    def test_second_export_matches(self, client, test_env):
        """Export again after restore — manifest counts should match original."""
        resp = client.post("/api/core/backup/export")
        assert resp.status_code == 200

        tar_bytes = io.BytesIO(resp.content)
        with tarfile.open(fileobj=tar_bytes, mode="r") as tf:
            manifest = json.load(tf.extractfile("manifest.json"))

        original = TestBackupEndpoints._backup_manifest
        assert manifest["wallet"]["clients"] == original["wallet"]["clients"]
        assert manifest["wallet"]["pool_total"] == original["wallet"]["pool_total"]
        assert manifest["wallet"]["subnet"] == original["wallet"]["subnet"]

    @pytest.mark.dependency(depends=["TestBackupEndpoints::test_second_export_matches"])
    def test_cleanup(self, client, test_env):
        """Revoke all backup-client-* to leave clean state."""
        for i in range(100):
            name = f"backup-client-{i:03d}"
            if test_env.wallet.get_client(name) is not None:
                client.post("/api/core/clients/revoke", json={"name": name})


# ── Large Backup (slow) ──────────────────────────────────────────

@pytest.mark.slow
class TestLargeBackup:
    """CIDR /16 full-pool backup/restore stress test.

    Topology:
        1. Snapshot current session state (pre-test backup)
        2. Expand CIDR to /16 → 65,533 usable IP slots
        3. Fill entire pool via wallet.assign_client() (direct, no API overhead)
        4. Export large backup via API (~20 MB tar)
        5. Wipe pool + shrink CIDR back to /24
        6. Import large backup via API → full /16 state restored
        7. Spot-check clients across pool boundaries
        8. Cleanup: restore pre-test snapshot
    """

    _pre_test_backup: bytes = b""
    _large_backup: bytes = b""
    _total_clients: int = 0

    @pytest.mark.dependency()
    def test_snapshot_pre_state(self, client):
        """Save current session state for cleanup."""
        resp = client.post("/api/core/backup/export")
        assert resp.status_code == 200
        TestLargeBackup._pre_test_backup = resp.content

    @pytest.mark.dependency(depends=["TestLargeBackup::test_snapshot_pre_state"])
    def test_expand_cidr(self, client, test_env):
        """Expand CIDR to /16 — 65,533 usable slots."""
        test_env.wallet.change_cidr(16)
        total = test_env.wallet.count_users()
        assert total == 65533
        TestLargeBackup._total_clients = total

    @pytest.mark.dependency(depends=["TestLargeBackup::test_expand_cidr"])
    def test_fill_pool(self, client, test_env):
        """Assign all 65,533 slots (direct wallet, ~60s)."""
        total = TestLargeBackup._total_clients
        for i in range(total):
            test_env.wallet.assign_client(f"lg-{i:05d}")
        assert test_env.wallet.count_assigned() == total

    @pytest.mark.dependency(depends=["TestLargeBackup::test_fill_pool"])
    def test_export_large(self, client):
        """Export full /16 pool — large tar file."""
        resp = client.post("/api/core/backup/export")
        assert resp.status_code == 200

        tar_bytes = io.BytesIO(resp.content)
        with tarfile.open(fileobj=tar_bytes, mode="r") as tf:
            manifest = json.load(tf.extractfile("manifest.json"))

        assert manifest["wallet"]["clients"] == TestLargeBackup._total_clients
        assert manifest["wallet"]["pool_total"] == TestLargeBackup._total_clients
        assert manifest["wallet"]["pool_assigned"] == TestLargeBackup._total_clients
        TestLargeBackup._large_backup = resp.content

    @pytest.mark.dependency(depends=["TestLargeBackup::test_export_large"])
    def test_wipe_and_shrink(self, client, test_env):
        """Mass revoke + CIDR back to /24 — clean slate before import."""
        # Mass revoke via direct SQL (65K revoke API calls would be too slow)
        test_env.wallet._conn.execute(
            "UPDATE users SET id = NULL, name = NULL, "
            "private_key_hex = NULL, public_key_hex = NULL, "
            "preshared_key_hex = NULL, created_at = NULL, updated_at = NULL "
            "WHERE id IS NOT NULL"
        )
        test_env.wallet._conn.commit()
        assert test_env.wallet.count_assigned() == 0

        test_env.wallet.change_cidr(24)
        assert test_env.wallet.count_users() == 253

    @pytest.mark.dependency(depends=["TestLargeBackup::test_wipe_and_shrink"])
    def test_import_large(self, client, test_env):
        """Import large backup → full /16 state restored."""
        resp = client.post(
            "/api/core/backup/import",
            files={"file": ("large.tar", TestLargeBackup._large_backup, "application/x-tar")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["wallet_clients"] == TestLargeBackup._total_clients

        # Verify DB state
        assert test_env.wallet.count_users() == 65533
        assert test_env.wallet.count_assigned() == 65533

    @pytest.mark.dependency(depends=["TestLargeBackup::test_import_large"])
    def test_spot_check(self, client, test_env):
        """Spot-check clients across pool boundaries."""
        checkpoints = [0, 99, 500, 1000, 10000, 32000, 65532]
        for i in checkpoints:
            name = f"lg-{i:05d}"
            c = test_env.wallet.get_client(name)
            assert c is not None, f"{name} missing after import"
            assert c["id"] is not None
            assert c["private_key_hex"] is not None
            assert c["public_key_hex"] is not None

    @pytest.mark.dependency(depends=["TestLargeBackup::test_spot_check"])
    def test_cleanup(self, client, test_env):
        """Restore pre-test session state."""
        resp = client.post(
            "/api/core/backup/import",
            files={"file": ("pre.tar", TestLargeBackup._pre_test_backup, "application/x-tar")},
        )
        assert resp.status_code == 200
