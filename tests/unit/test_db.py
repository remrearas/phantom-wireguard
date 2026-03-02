"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge.db — schema, config CRUD, state transitions.
"""

import os
import tempfile

import pytest

from wstunnel_bridge.db import WstunnelDB
from wstunnel_bridge.models import ServerConfig


@pytest.fixture
def db():
    """In-memory WstunnelDB instance."""
    d = WstunnelDB(":memory:")
    yield d
    d.close()


@pytest.fixture
def db_file():
    """File-backed WstunnelDB for persistence tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = WstunnelDB(path)
    yield d, path
    d.close()
    for ext in ("", "-wal", "-shm"):
        p = path + ext
        if os.path.exists(p):
            os.remove(p)


class TestSchema:
    """Schema creation and migration."""

    def test_wal_mode(self, tmp_path):
        d = WstunnelDB(str(tmp_path / "test.db"))
        mode = d._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        d.close()

    def test_config_table_exists(self, db):
        row = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='config'"
        ).fetchone()
        assert row is not None

    def test_singleton_row_created(self, db):
        row = db._conn.execute("SELECT id FROM config WHERE id = 1").fetchone()
        assert row is not None

    def test_singleton_constraint(self, db):
        with pytest.raises(Exception):
            db._conn.execute(
                "INSERT INTO config (id, bind_url, updated_at) VALUES (2, '', 0)"
            )

    def test_default_values(self, db):
        cfg = db.get_config()
        assert cfg.bind_url == ""
        assert cfg.restrict_to == ""
        assert cfg.restrict_path_prefix == ""
        assert cfg.tls_certificate == ""
        assert cfg.tls_private_key == ""
        assert cfg.state == "stopped"

    def test_no_old_tables(self, db):
        tables = [r[0] for r in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        assert "client_config" not in tables
        assert "tunnels" not in tables
        assert "server_restrictions" not in tables
        assert "http_headers" not in tables
        assert "server_config" not in tables

    def test_schema_loaded_from_file(self, db):
        """Schema is loaded from schemas/schema.sql, not inline DDL."""
        from wstunnel_bridge.db import _SCHEMA_PATH
        assert _SCHEMA_PATH.exists()
        assert _SCHEMA_PATH.name == "schema.sql"

    def test_idempotent_init(self, db):
        db._ensure_config()
        cfg = db.get_config()
        assert cfg.state == "stopped"


class TestReturnType:
    """get_config() returns ServerConfig dataclass."""

    def test_returns_server_config(self, db):
        cfg = db.get_config()
        assert isinstance(cfg, ServerConfig)

    def test_dataclass_fields(self, db):
        cfg = db.get_config()
        assert hasattr(cfg, "bind_url")
        assert hasattr(cfg, "restrict_to")
        assert hasattr(cfg, "restrict_path_prefix")
        assert hasattr(cfg, "tls_certificate")
        assert hasattr(cfg, "tls_private_key")
        assert hasattr(cfg, "state")
        assert hasattr(cfg, "updated_at")


class TestConfigCRUD:
    """set_config / get_config."""

    def test_set_bind_url(self, db):
        db.set_config(bind_url="wss://[::]:443")
        cfg = db.get_config()
        assert cfg.bind_url == "wss://[::]:443"

    def test_set_multiple_fields(self, db):
        db.set_config(
            bind_url="wss://0.0.0.0:8443",
            restrict_to="127.0.0.1:51820",
            restrict_path_prefix="secret",
        )
        cfg = db.get_config()
        assert cfg.bind_url == "wss://0.0.0.0:8443"
        assert cfg.restrict_to == "127.0.0.1:51820"
        assert cfg.restrict_path_prefix == "secret"

    def test_set_tls_fields(self, db):
        db.set_config(
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        cfg = db.get_config()
        assert cfg.tls_certificate == "/certs/cert.pem"
        assert cfg.tls_private_key == "/certs/key.pem"

    def test_partial_update(self, db):
        db.set_config(bind_url="wss://[::]:443", restrict_to="a:1")
        db.set_config(restrict_to="b:2")
        cfg = db.get_config()
        assert cfg.bind_url == "wss://[::]:443"
        assert cfg.restrict_to == "b:2"

    def test_empty_update_noop(self, db):
        db.set_config(bind_url="wss://test")
        db.set_config()  # no-op
        cfg = db.get_config()
        assert cfg.bind_url == "wss://test"

    def test_unknown_column_raises(self, db):
        with pytest.raises(ValueError, match="Unknown columns"):
            db.set_config(nonexistent="value")

    def test_updated_at_changes(self, db):
        cfg1 = db.get_config()
        ts1 = cfg1.updated_at
        db.set_config(bind_url="wss://new")
        cfg2 = db.get_config()
        assert cfg2.updated_at >= ts1


class TestState:
    """get_state / set_state."""

    def test_default_state(self, db):
        assert db.get_state() == "stopped"

    def test_set_started(self, db):
        db.set_state("started")
        assert db.get_state() == "started"

    def test_set_stopped(self, db):
        db.set_state("started")
        db.set_state("stopped")
        assert db.get_state() == "stopped"

    def test_state_reflects_in_config(self, db):
        db.set_state("started")
        cfg = db.get_config()
        assert cfg.state == "started"


class TestPersistence:
    """File-backed DB persistence across reopen."""

    def test_config_persists(self, db_file):
        d, path = db_file
        d.set_config(
            bind_url="wss://[::]:443",
            restrict_to="127.0.0.1:51820",
            restrict_path_prefix="secret",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        d.set_state("started")
        d.close()

        d2 = WstunnelDB(path)
        cfg = d2.get_config()
        assert cfg.bind_url == "wss://[::]:443"
        assert cfg.restrict_to == "127.0.0.1:51820"
        assert cfg.restrict_path_prefix == "secret"
        assert cfg.tls_certificate == "/certs/cert.pem"
        assert cfg.tls_private_key == "/certs/key.pem"
        assert cfg.state == "started"
        d2.close()


class TestClose:
    """close() releases connection."""

    def test_close_then_query_fails(self):
        d = WstunnelDB(":memory:")
        d.close()
        with pytest.raises(Exception):
            d.get_config()
