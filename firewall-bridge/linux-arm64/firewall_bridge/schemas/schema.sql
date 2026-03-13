-- firewall_bridge v2.1 — SQLite schema
-- ufw pattern: config singleton + rule groups + firewall/routing rules
-- WAL mode for crash recovery, foreign keys for cascade delete

CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL DEFAULT 'stopped',
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rule_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    group_type TEXT NOT NULL DEFAULT 'custom',
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS firewall_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES rule_groups(id) ON DELETE CASCADE,
    chain TEXT NOT NULL,
    action TEXT NOT NULL,
    family INTEGER NOT NULL DEFAULT 2,
    proto TEXT NOT NULL DEFAULT '',
    dport INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    destination TEXT NOT NULL DEFAULT '',
    in_iface TEXT NOT NULL DEFAULT '',
    out_iface TEXT NOT NULL DEFAULT '',
    state_match TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0,
    nft_handle INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES rule_groups(id) ON DELETE CASCADE,
    rule_type TEXT NOT NULL,
    from_network TEXT NOT NULL DEFAULT '',
    to_network TEXT NOT NULL DEFAULT '',
    table_name TEXT NOT NULL DEFAULT '',
    table_id INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    destination TEXT NOT NULL DEFAULT '',
    device TEXT NOT NULL DEFAULT '',
    applied INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
