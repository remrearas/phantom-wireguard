package db

import (
	"database/sql"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

// BridgeDB manages the SQLite bridge database (bridge-db).
// This is the single source of truth for WireGuard client state.
type BridgeDB struct {
	db *sql.DB
}

// Open creates or opens a bridge-db at the given path.
// Uses WAL mode for concurrent read access from Python daemon.
func Open(path string) (*BridgeDB, error) {
	dsn := path + "?_journal_mode=WAL&_synchronous=NORMAL&_busy_timeout=5000&_foreign_keys=ON"
	sqlDB, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := sqlDB.Ping(); err != nil {
		_ = sqlDB.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}
	bdb := &BridgeDB{db: sqlDB}
	if err := bdb.migrate(); err != nil {
		_ = sqlDB.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return bdb, nil
}

// Close closes the database connection.
func (b *BridgeDB) Close() error {
	return b.db.Close()
}

// DB returns the underlying sql.DB for advanced queries.
func (b *BridgeDB) DB() *sql.DB {
	return b.db
}

func (b *BridgeDB) migrate() error {
	schema := `
	PRAGMA user_version = 1;

	CREATE TABLE IF NOT EXISTS device (
		id              INTEGER PRIMARY KEY CHECK (id = 1),
		name            TEXT NOT NULL,
		private_key     TEXT NOT NULL,
		public_key      TEXT NOT NULL,
		listen_port     INTEGER NOT NULL,
		started_at      INTEGER
	);

	CREATE TABLE IF NOT EXISTS peers (
		id              INTEGER PRIMARY KEY AUTOINCREMENT,
		public_key      TEXT NOT NULL UNIQUE,
		preshared_key   TEXT,
		private_key     TEXT NOT NULL,
		allowed_ip      TEXT NOT NULL UNIQUE,
		allowed_ip_v6   TEXT UNIQUE,
		keepalive       INTEGER NOT NULL DEFAULT 25,
		enabled         INTEGER NOT NULL DEFAULT 1,
		created_at      INTEGER NOT NULL,
		peer_index      INTEGER,
		endpoint        TEXT,
		last_handshake  INTEGER,
		rx_bytes        INTEGER NOT NULL DEFAULT 0,
		tx_bytes        INTEGER NOT NULL DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS ip_pool (
		ip              TEXT NOT NULL UNIQUE,
		family          INTEGER NOT NULL DEFAULT 4,
		assigned        INTEGER NOT NULL DEFAULT 0,
		peer_id         INTEGER,
		FOREIGN KEY (peer_id) REFERENCES peers(id) ON DELETE SET NULL
	);

	CREATE TABLE IF NOT EXISTS server_config (
		device_id       INTEGER PRIMARY KEY DEFAULT 1,
		endpoint        TEXT,
		endpoint_v6     TEXT,
		network         TEXT NOT NULL DEFAULT '10.8.0.0/24',
		network_v6      TEXT,
		dns_primary     TEXT NOT NULL DEFAULT '1.1.1.1',
		dns_secondary   TEXT DEFAULT '9.9.9.9',
		dns_v6          TEXT,
		mtu             INTEGER NOT NULL DEFAULT 1420,
		fwmark          INTEGER NOT NULL DEFAULT 0,
		post_up         TEXT,
		post_down       TEXT,
		FOREIGN KEY (device_id) REFERENCES device(id)
	);

	CREATE TABLE IF NOT EXISTS multihop_tunnels (
		id                   INTEGER PRIMARY KEY AUTOINCREMENT,
		name                 TEXT NOT NULL UNIQUE,
		enabled              INTEGER NOT NULL DEFAULT 0,

		-- WireGuard interface (our side of the upstream tunnel)
		interface_name       TEXT NOT NULL UNIQUE,
		listen_port          INTEGER NOT NULL DEFAULT 0,
		private_key          TEXT NOT NULL,
		public_key           TEXT NOT NULL,

		-- Remote endpoint (the VPN server we connect to)
		remote_endpoint      TEXT NOT NULL,
		remote_public_key    TEXT NOT NULL,
		remote_preshared_key TEXT,
		remote_allowed_ips   TEXT NOT NULL DEFAULT '0.0.0.0/0',
		remote_keepalive     INTEGER NOT NULL DEFAULT 25,

		-- Routing (policy routing via fwmark)
		fwmark               INTEGER NOT NULL DEFAULT 0,
		routing_table        TEXT NOT NULL DEFAULT 'phantom_multihop',
		routing_table_id     INTEGER NOT NULL DEFAULT 100,
		priority             INTEGER NOT NULL DEFAULT 100,

		-- Runtime state (ephemeral, cleared on startup)
		status               TEXT NOT NULL DEFAULT 'stopped',
		error_msg            TEXT,
		started_at           INTEGER,
		created_at           INTEGER NOT NULL
	);
	`
	_, err := b.db.Exec(schema)
	return err
}