"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge.db — SQLite state layer for wstunnel-bridge v2.

Mirrors firewall-bridge db.rs pattern but implemented in Python.
WAL mode, user_version migration, singleton config rows.
"""

import sqlite3
import time


SCHEMA_VERSION = 1

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL DEFAULT 'initialized',
    mode TEXT NOT NULL DEFAULT 'client',
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS client_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    remote_url TEXT NOT NULL DEFAULT '',
    http_upgrade_path_prefix TEXT NOT NULL DEFAULT 'v1',
    http_upgrade_credentials TEXT NOT NULL DEFAULT '',
    tls_verify INTEGER NOT NULL DEFAULT 0,
    tls_sni_override TEXT NOT NULL DEFAULT '',
    tls_sni_disable INTEGER NOT NULL DEFAULT 0,
    websocket_ping_frequency INTEGER NOT NULL DEFAULT 30,
    websocket_mask_frame INTEGER NOT NULL DEFAULT 0,
    connection_min_idle INTEGER NOT NULL DEFAULT 0,
    connection_retry_max_backoff INTEGER NOT NULL DEFAULT 300,
    http_proxy TEXT NOT NULL DEFAULT '',
    worker_threads INTEGER NOT NULL DEFAULT 2,
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS server_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    bind_url TEXT NOT NULL DEFAULT '',
    tls_certificate TEXT NOT NULL DEFAULT '',
    tls_private_key TEXT NOT NULL DEFAULT '',
    tls_client_ca_certs TEXT NOT NULL DEFAULT '',
    websocket_ping_frequency INTEGER NOT NULL DEFAULT 30,
    websocket_mask_frame INTEGER NOT NULL DEFAULT 0,
    worker_threads INTEGER NOT NULL DEFAULT 2,
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tunnels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tunnel_type TEXT NOT NULL,
    local_host TEXT NOT NULL DEFAULT '127.0.0.1',
    local_port INTEGER NOT NULL,
    remote_host TEXT NOT NULL DEFAULT '',
    remote_port INTEGER NOT NULL DEFAULT 0,
    timeout_secs INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS server_restrictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restriction_type TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS http_headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
"""


def _now() -> int:
    return int(time.time())


class WstunnelDB:
    """SQLite state database for wstunnel-bridge."""

    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            self._conn.executescript(SCHEMA_DDL)
            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._conn.commit()

    # ---- Config ----

    def init_config(self, mode: str = "client") -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO config (id, mode, updated_at) VALUES (1, ?, ?)",
            (mode, _now()),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO client_config (id, updated_at) VALUES (1, ?)",
            (_now(),),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO server_config (id, updated_at) VALUES (1, ?)",
            (_now(),),
        )
        self._conn.commit()

    def get_config(self) -> dict:
        row = self._conn.execute("SELECT * FROM config WHERE id = 1").fetchone()
        if row is None:
            raise LookupError("Config not initialized")
        return dict(row)

    def set_state(self, state: str) -> None:
        self._conn.execute(
            "UPDATE config SET state = ?, updated_at = ? WHERE id = 1",
            (state, _now()),
        )
        self._conn.commit()

    def set_mode(self, mode: str) -> None:
        self._conn.execute(
            "UPDATE config SET mode = ?, updated_at = ? WHERE id = 1",
            (mode, _now()),
        )
        self._conn.commit()

    # ---- Client Config ----

    _CLIENT_COLUMNS = frozenset({
        "remote_url", "http_upgrade_path_prefix", "http_upgrade_credentials",
        "tls_verify", "tls_sni_override", "tls_sni_disable",
        "websocket_ping_frequency", "websocket_mask_frame",
        "connection_min_idle", "connection_retry_max_backoff",
        "http_proxy", "worker_threads",
    })

    def set_client_config(self, **kwargs) -> None:
        self._partial_update("client_config", self._CLIENT_COLUMNS, kwargs)

    def get_client_config(self) -> dict:
        row = self._conn.execute("SELECT * FROM client_config WHERE id = 1").fetchone()
        if row is None:
            raise LookupError("Client config not initialized")
        return dict(row)

    # ---- Server Config ----

    _SERVER_COLUMNS = frozenset({
        "bind_url", "tls_certificate", "tls_private_key", "tls_client_ca_certs",
        "websocket_ping_frequency", "websocket_mask_frame", "worker_threads",
    })

    def set_server_config(self, **kwargs) -> None:
        self._partial_update("server_config", self._SERVER_COLUMNS, kwargs)

    def get_server_config(self) -> dict:
        row = self._conn.execute("SELECT * FROM server_config WHERE id = 1").fetchone()
        if row is None:
            raise LookupError("Server config not initialized")
        return dict(row)

    # ---- Tunnels ----

    def add_tunnel(
        self,
        tunnel_type: str,
        local_host: str,
        local_port: int,
        remote_host: str = "",
        remote_port: int = 0,
        timeout_secs: int = 0,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO tunnels (tunnel_type, local_host, local_port, "
            "remote_host, remote_port, timeout_secs, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tunnel_type, local_host, local_port, remote_host, remote_port,
             timeout_secs, _now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_tunnels(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM tunnels ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def delete_tunnel(self, tunnel_id: int) -> None:
        self._conn.execute("DELETE FROM tunnels WHERE id = ?", (tunnel_id,))
        self._conn.commit()

    def clear_tunnels(self) -> None:
        self._conn.execute("DELETE FROM tunnels")
        self._conn.commit()

    # ---- Server Restrictions ----

    def add_restriction(self, restriction_type: str, value: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO server_restrictions (restriction_type, value, created_at) "
            "VALUES (?, ?, ?)",
            (restriction_type, value, _now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_restrictions(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM server_restrictions ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_restriction(self, restriction_id: int) -> None:
        self._conn.execute(
            "DELETE FROM server_restrictions WHERE id = ?", (restriction_id,)
        )
        self._conn.commit()

    def clear_restrictions(self) -> None:
        self._conn.execute("DELETE FROM server_restrictions")
        self._conn.commit()

    # ---- HTTP Headers ----

    def add_http_header(self, name: str, value: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO http_headers (name, value, created_at) VALUES (?, ?, ?)",
            (name, value, _now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_http_headers(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM http_headers ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_http_header(self, header_id: int) -> None:
        self._conn.execute("DELETE FROM http_headers WHERE id = ?", (header_id,))
        self._conn.commit()

    def clear_http_headers(self) -> None:
        self._conn.execute("DELETE FROM http_headers")
        self._conn.commit()

    # ---- Lifecycle ----

    def close(self) -> None:
        self._conn.close()

    # ---- Internal ----

    def _partial_update(
        self, table: str, allowed: frozenset, kwargs: dict
    ) -> None:
        unknown = set(kwargs) - allowed
        if unknown:
            raise ValueError(f"Unknown columns: {unknown}")
        if not kwargs:
            return
        sets = ", ".join(f"{col} = ?" for col in kwargs)
        vals = list(kwargs.values()) + [_now()]
        self._conn.execute(
            f"UPDATE {table} SET {sets}, updated_at = ? WHERE id = 1", vals
        )
        self._conn.commit()
