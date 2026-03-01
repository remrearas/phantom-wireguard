"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge.db — in-memory SQLite, no native library needed.
"""

import pytest

from wstunnel_bridge.db import WstunnelDB, SCHEMA_VERSION


@pytest.fixture
def db():
    d = WstunnelDB(":memory:")
    d.init_config()
    yield d
    d.close()


class TestOpenAndMigrate:
    """Database opens, migrates schema, sets user_version."""

    def test_tables_created(self, db):
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        assert tables == [
            "client_config", "config", "http_headers",
            "server_config", "server_restrictions", "tunnels",
        ]

    def test_user_version(self, db):
        ver = db._conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION

    def test_wal_mode(self, tmp_path):
        d = WstunnelDB(str(tmp_path / "test.db"))
        mode = d._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        d.close()

    def test_idempotent_migration(self):
        d = WstunnelDB(":memory:")
        d.init_config()
        # Second open on same connection should not fail
        d._migrate()
        ver = d._conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION
        d.close()


class TestConfig:
    """Singleton config row lifecycle."""

    def test_init_creates_config(self, db):
        cfg = db.get_config()
        assert cfg["state"] == "initialized"
        assert cfg["mode"] == "client"

    def test_set_state(self, db):
        db.set_state("started")
        assert db.get_config()["state"] == "started"

    def test_set_mode(self, db):
        db.set_mode("server")
        assert db.get_config()["mode"] == "server"

    def test_init_idempotent(self, db):
        db.set_state("started")
        db.init_config()  # OR IGNORE — should not reset
        assert db.get_config()["state"] == "started"

    def test_get_config_before_init_raises(self):
        d = WstunnelDB(":memory:")
        with pytest.raises(LookupError):
            d.get_config()
        d.close()

    def test_get_client_config_before_init_raises(self):
        d = WstunnelDB(":memory:")
        with pytest.raises(LookupError):
            d.get_client_config()
        d.close()

    def test_get_server_config_before_init_raises(self):
        d = WstunnelDB(":memory:")
        with pytest.raises(LookupError):
            d.get_server_config()
        d.close()

    def test_updated_at_changes(self, db):
        ts1 = db.get_config()["updated_at"]
        db.set_state("stopped")
        ts2 = db.get_config()["updated_at"]
        assert ts2 >= ts1


class TestClientConfig:
    """Client config singleton — partial update pattern."""

    def test_defaults(self, db):
        cfg = db.get_client_config()
        assert cfg["remote_url"] == ""
        assert cfg["http_upgrade_path_prefix"] == "v1"
        assert cfg["tls_verify"] == 0
        assert cfg["websocket_ping_frequency"] == 30
        assert cfg["connection_retry_max_backoff"] == 300
        assert cfg["worker_threads"] == 2

    def test_partial_update(self, db):
        db.set_client_config(remote_url="wss://vpn.example.com:443")
        cfg = db.get_client_config()
        assert cfg["remote_url"] == "wss://vpn.example.com:443"
        assert cfg["http_upgrade_path_prefix"] == "v1"  # unchanged

    def test_multi_field_update(self, db):
        db.set_client_config(
            remote_url="wss://vpn.example.com:443",
            tls_verify=1,
            worker_threads=4,
        )
        cfg = db.get_client_config()
        assert cfg["remote_url"] == "wss://vpn.example.com:443"
        assert cfg["tls_verify"] == 1
        assert cfg["worker_threads"] == 4

    def test_unknown_column_raises(self, db):
        with pytest.raises(ValueError, match="Unknown columns"):
            db.set_client_config(nonexistent_field="bad")

    def test_empty_update_noop(self, db):
        ts1 = db.get_client_config()["updated_at"]
        db.set_client_config()  # no kwargs
        ts2 = db.get_client_config()["updated_at"]
        assert ts2 == ts1


class TestServerConfig:
    """Server config singleton — partial update pattern."""

    def test_defaults(self, db):
        cfg = db.get_server_config()
        assert cfg["bind_url"] == ""
        assert cfg["tls_certificate"] == ""
        assert cfg["tls_private_key"] == ""
        assert cfg["worker_threads"] == 2

    def test_partial_update(self, db):
        db.set_server_config(
            bind_url="wss://0.0.0.0:443",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        cfg = db.get_server_config()
        assert cfg["bind_url"] == "wss://0.0.0.0:443"
        assert cfg["tls_certificate"] == "/certs/cert.pem"
        assert cfg["tls_private_key"] == "/certs/key.pem"
        assert cfg["tls_client_ca_certs"] == ""  # unchanged

    def test_unknown_column_raises(self, db):
        with pytest.raises(ValueError, match="Unknown columns"):
            db.set_server_config(remote_url="wss://bad")


class TestTunnels:
    """Multi-row tunnel CRUD."""

    def test_add_and_list(self, db):
        tid = db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        assert tid > 0
        tunnels = db.list_tunnels()
        assert len(tunnels) == 1
        assert tunnels[0]["tunnel_type"] == "udp"
        assert tunnels[0]["local_port"] == 51820

    def test_multiple_tunnels(self, db):
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        db.add_tunnel("tcp", "127.0.0.1", 8080, "10.0.0.1", 80)
        db.add_tunnel("socks5", "127.0.0.1", 1080)
        assert len(db.list_tunnels()) == 3

    def test_delete(self, db):
        tid = db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        db.delete_tunnel(tid)
        assert len(db.list_tunnels()) == 0

    def test_clear(self, db):
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        db.add_tunnel("tcp", "127.0.0.1", 8080, "10.0.0.1", 80)
        db.clear_tunnels()
        assert len(db.list_tunnels()) == 0

    def test_timeout_secs(self, db):
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820, timeout_secs=60)
        t = db.list_tunnels()[0]
        assert t["timeout_secs"] == 60


class TestServerRestrictions:
    """Multi-row server restriction CRUD."""

    def test_add_target(self, db):
        rid = db.add_restriction("target", "127.0.0.1:51820")
        assert rid > 0
        rests = db.list_restrictions()
        assert len(rests) == 1
        assert rests[0]["restriction_type"] == "target"
        assert rests[0]["value"] == "127.0.0.1:51820"

    def test_add_path_prefix(self, db):
        db.add_restriction("path_prefix", "secret-path")
        rests = db.list_restrictions()
        assert rests[0]["restriction_type"] == "path_prefix"

    def test_delete(self, db):
        rid = db.add_restriction("target", "127.0.0.1:51820")
        db.delete_restriction(rid)
        assert len(db.list_restrictions()) == 0

    def test_clear(self, db):
        db.add_restriction("target", "127.0.0.1:51820")
        db.add_restriction("path_prefix", "secret")
        db.clear_restrictions()
        assert len(db.list_restrictions()) == 0


class TestHttpHeaders:
    """Multi-row HTTP header CRUD."""

    def test_add_and_list(self, db):
        hid = db.add_http_header("X-Custom", "value1")
        assert hid > 0
        headers = db.list_http_headers()
        assert len(headers) == 1
        assert headers[0]["name"] == "X-Custom"
        assert headers[0]["value"] == "value1"

    def test_multiple(self, db):
        db.add_http_header("X-First", "a")
        db.add_http_header("X-Second", "b")
        assert len(db.list_http_headers()) == 2

    def test_delete(self, db):
        hid = db.add_http_header("X-Delete", "val")
        db.delete_http_header(hid)
        assert len(db.list_http_headers()) == 0

    def test_clear(self, db):
        db.add_http_header("X-A", "1")
        db.add_http_header("X-B", "2")
        db.clear_http_headers()
        assert len(db.list_http_headers()) == 0
