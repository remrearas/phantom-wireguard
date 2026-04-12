"""
Phantom-WG Frontmatter — Key/Value Store

A pure key/value view over a single SQLite table. Each frontmatter
module owns one table with the same minimal schema:

    CREATE TABLE IF NOT EXISTS <table> (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

There is no schema evolution to worry about — adding a new piece of
state is just adding a new key. There is no ``updated_at`` column,
no JSON blobs, no nested structures: the abstraction is two columns
and the modules treat values as opaque strings.

The single SQLite database file lives at
``data/frontmatter.db`` underneath the install root. Every module
gets its own table; cross-module reads are done by instantiating a
second ``KVStore`` against the foreign table name.

State principle
    Tables hold **primitive runtime parameters** only — backend IP,
    cert paths, secret, listen port. They never hold derived /
    rendered output (systemd unit lines, ``[Wstunnel]`` snippets,
    command lines), nor do they hold service health flags
    (``is-active``, ``is-enabled``). Those are produced fresh from
    the parameters whenever someone asks, or queried from systemd
    on demand.

Concurrency
    Each write goes through ``BEGIN IMMEDIATE`` / ``COMMIT`` so
    cross-process and cross-module writes never tear or clobber
    each other.

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0
"""

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional


# Whitelist for table names that are safe to interpolate into SQL
# statements (sqlite3 does not support binding identifiers).
_TABLE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")


# ── Module-level connection helpers ─────────────────────────────────
@contextmanager
def _open_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection with sane defaults.

    ``isolation_level=None`` puts pysqlite in autocommit mode; the
    transaction wrapper below issues ``BEGIN IMMEDIATE`` /
    ``COMMIT`` explicitly to control the boundaries.
    """
    con = sqlite3.connect(
        str(db_path),
        isolation_level=None,
        timeout=30.0,
    )
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        yield con
    finally:
        con.close()


@contextmanager
def _open_transaction(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Wrap a write in ``BEGIN IMMEDIATE`` / ``COMMIT`` (or ROLLBACK)."""
    with _open_connection(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            yield con
        except Exception:
            con.execute("ROLLBACK")
            raise
        else:
            con.execute("COMMIT")


class KVStore:
    """Key/value view over a single SQLite table.

    The store auto-creates the backing table on construction. All
    operations are atomic at the SQL level.

    Args:
        db_path: Path to the SQLite database file. Parent directories
            are created if missing.
        table:   Table name (also the conceptual "section" name). Must
            match ``[a-zA-Z][a-zA-Z0-9_]{0,63}`` for safe interpolation.
    """

    def __init__(self, db_path: Path, table: str):
        if not _TABLE_NAME_RE.match(table):
            raise ValueError(
                f"Invalid table name {table!r} — must match "
                f"{_TABLE_NAME_RE.pattern}"
            )
        self._db_path = Path(db_path)
        self._table = table
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    # ── Schema ───────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        with _open_connection(self._db_path) as con:
            con.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                f"  key   TEXT PRIMARY KEY,"
                f"  value TEXT NOT NULL"
                f")"
            )

    # ── Core string K/V ──────────────────────────────────────────

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the value for ``key``, or ``default`` if missing."""
        with _open_connection(self._db_path) as con:
            row = con.execute(
                f"SELECT value FROM {self._table} WHERE key = ?",
                (key,),
            ).fetchone()
        return row[0] if row is not None else default

    def set(self, key: str, value: str) -> None:
        """Insert or replace a single key. Atomic."""
        if value is None:
            raise ValueError(f"value for {key!r} cannot be None")
        with _open_transaction(self._db_path) as con:
            con.execute(
                f"INSERT INTO {self._table} (key, value) VALUES (?, ?) "
                f"ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def items(self) -> Dict[str, str]:
        """Return the entire table as a dict."""
        with _open_connection(self._db_path) as con:
            return {
                row[0]: row[1] for row in con.execute(
                    f"SELECT key, value FROM {self._table}"
                )
            }

    def clear(self) -> None:
        """Remove every row from this table. Atomic."""
        with _open_transaction(self._db_path) as con:
            con.execute(f"DELETE FROM {self._table}")

    def replace(self, items: Dict[str, str]) -> None:
        """Atomically replace the entire table contents.

        Equivalent to ``clear()`` + ``set()`` for each pair, but
        wrapped in a single transaction so partial failures roll back.
        """
        with _open_transaction(self._db_path) as con:
            con.execute(f"DELETE FROM {self._table}")
            con.executemany(
                f"INSERT INTO {self._table} (key, value) VALUES (?, ?)",
                [(k, str(v)) for k, v in items.items()],
            )

    # ── Typed read helper ───────────────────────────────────────
    #
    # The store is text-only on disk. ``get_int`` parses an integer
    # value back out — used by modules that store port numbers.

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError as e:
            raise ValueError(
                f"value for {self._table}.{key} is not an int: {raw!r}"
            ) from e

    def __repr__(self) -> str:
        return f"<KVStore db={self._db_path} table={self._table!r}>"