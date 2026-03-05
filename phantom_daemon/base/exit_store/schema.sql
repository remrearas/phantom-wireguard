PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS exits (
    id                TEXT    PRIMARY KEY,
    name              TEXT    UNIQUE NOT NULL,
    endpoint          TEXT    NOT NULL,
    address           TEXT    NOT NULL,
    private_key_hex   TEXT    NOT NULL,
    public_key_hex    TEXT    NOT NULL,
    preshared_key_hex TEXT    NOT NULL DEFAULT '',
    allowed_ips       TEXT    NOT NULL DEFAULT '0.0.0.0/0, ::/0',
    keepalive         INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO config (key, value) VALUES ('active_exit', '');
INSERT OR IGNORE INTO config (key, value) VALUES ('multihop_enabled', '0');

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    action    TEXT NOT NULL,
    detail    TEXT NOT NULL DEFAULT '{}',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log (timestamp);
