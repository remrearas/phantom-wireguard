"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel_bridge.db — Server-only SQLite persistence.

Schema loaded from schemas/schema.sql (firewall-bridge pattern).
Returns ServerConfig dataclass objects, not raw dicts.
WAL mode, singleton row.
"""

import sqlite3
import time
from pathlib import Path

from .models import ServerConfig


_SCHEMA_PATH = Path(__file__).parent / "schemas" / "schema.sql"
_SCHEMA = _SCHEMA_PATH.read_text(encoding="utf-8")


def _now() -> int:
    return int(time.time())


class WstunnelDB:
    """SQLite persistence — server config state store."""

    __slots__ = ("_conn",)

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._ensure_config()

    def _ensure_config(self) -> None:
        row = self._conn.execute("SELECT id FROM config WHERE id=1").fetchone()
        if not row:
            self._conn.execute(
                "INSERT INTO config (id, updated_at) VALUES (1, ?)",
                (_now(),),
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ---- Config ----

    _CONFIG_COLUMNS = frozenset({
        "bind_url", "restrict_to", "restrict_path_prefix",
        "tls_certificate", "tls_private_key",
    })

    def set_config(self, **kwargs) -> None:
        unknown = set(kwargs) - self._CONFIG_COLUMNS
        if unknown:
            raise ValueError(f"Unknown columns: {unknown}")
        if not kwargs:
            return
        sets = ", ".join(f"{col} = ?" for col in kwargs)
        vals = list(kwargs.values()) + [_now()]
        self._conn.execute(
            f"UPDATE config SET {sets}, updated_at = ? WHERE id = 1", vals
        )
        self._conn.commit()

    def get_config(self) -> ServerConfig:
        row = self._conn.execute("SELECT * FROM config WHERE id=1").fetchone()
        if row is None:
            raise LookupError("Config not initialized")
        return self._row_to_config(row)

    # ---- State ----

    def get_state(self) -> str:
        row = self._conn.execute(
            "SELECT state FROM config WHERE id=1"
        ).fetchone()
        if row is None:
            raise LookupError("Config not initialized")
        return row["state"]

    def set_state(self, state: str) -> None:
        self._conn.execute(
            "UPDATE config SET state=?, updated_at=? WHERE id=1",
            (state, _now()),
        )
        self._conn.commit()

    # ---- Internal ----

    @staticmethod
    def _row_to_config(row: sqlite3.Row) -> ServerConfig:
        return ServerConfig(
            bind_url=row["bind_url"],
            restrict_to=row["restrict_to"],
            restrict_path_prefix=row["restrict_path_prefix"],
            tls_certificate=row["tls_certificate"],
            tls_private_key=row["tls_private_key"],
            state=row["state"],
            updated_at=row["updated_at"],
        )
