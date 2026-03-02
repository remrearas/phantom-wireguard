-- wstunnel_bridge v2.1 — SQLite schema
-- Server-only: singleton config row with embedded state
-- WAL mode for crash recovery

CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    bind_url TEXT NOT NULL DEFAULT '',
    restrict_to TEXT NOT NULL DEFAULT '',
    restrict_path_prefix TEXT NOT NULL DEFAULT '',
    tls_certificate TEXT NOT NULL DEFAULT '',
    tls_private_key TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'stopped',
    updated_at INTEGER NOT NULL DEFAULT 0
);
