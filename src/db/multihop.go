package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"
)

// MultihopTunnel represents an upstream VPN tunnel in a multihop chain.
// When enabled=1, this tunnel is automatically restored on daemon startup.
type MultihopTunnel struct {
	ID   int64  `json:"id"`
	Name string `json:"name"` // 'exit-us-1', 'relay-de-1'

	// Enabled — crash recovery flag.
	// If true, daemon restores this tunnel on startup without user intervention.
	Enabled bool `json:"enabled"`

	// Our WireGuard interface for this tunnel
	InterfaceName string `json:"interface_name"` // 'wg-hop0'
	ListenPort    int    `json:"listen_port"`    // 0 = random
	PrivateKey    string `json:"private_key"`    // our client key (hex)
	PublicKey     string `json:"public_key"`     // our client pub (hex)

	// Remote endpoint (the VPN server we connect to)
	RemoteEndpoint     string `json:"remote_endpoint"`      // '203.0.113.5:51820'
	RemotePublicKey    string `json:"remote_public_key"`    // server pub key (hex)
	RemotePresharedKey string `json:"remote_preshared_key"` // optional PSK (hex)
	RemoteAllowedIPs   string `json:"remote_allowed_ips"`   // '0.0.0.0/0'
	RemoteKeepalive    int    `json:"remote_keepalive"`     // 25

	// Policy routing
	FWMark         int    `json:"fwmark"`           // SO_MARK on this tunnel's socket
	RoutingTable   string `json:"routing_table"`    // 'phantom_multihop'
	RoutingTableID int    `json:"routing_table_id"` // 100
	Priority       int    `json:"priority"`         // ip rule priority

	// Runtime state (ephemeral)
	Status    string `json:"status"`               // 'running', 'stopped', 'error'
	ErrorMsg  string `json:"error_msg,omitempty"`
	StartedAt *int64 `json:"started_at,omitempty"`
	CreatedAt int64  `json:"created_at"`
}

// --- CRUD ---

// InsertMultihopTunnel creates a new multihop tunnel record.
func (b *BridgeDB) InsertMultihopTunnel(t *MultihopTunnel) error {
	t.CreatedAt = time.Now().Unix()
	t.Status = "stopped"
	result, err := b.db.Exec(`
		INSERT INTO multihop_tunnels
			(name, enabled, interface_name, listen_port, private_key, public_key,
			 remote_endpoint, remote_public_key, remote_preshared_key, remote_allowed_ips, remote_keepalive,
			 fwmark, routing_table, routing_table_id, priority,
			 status, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		t.Name, boolToInt(t.Enabled), t.InterfaceName, t.ListenPort, t.PrivateKey, t.PublicKey,
		t.RemoteEndpoint, t.RemotePublicKey, t.RemotePresharedKey, t.RemoteAllowedIPs, t.RemoteKeepalive,
		t.FWMark, t.RoutingTable, t.RoutingTableID, t.Priority,
		t.Status, t.CreatedAt)
	if err != nil {
		return err
	}
	t.ID, _ = result.LastInsertId()
	return nil
}

// GetMultihopTunnel retrieves a tunnel by name.
func (b *BridgeDB) GetMultihopTunnel(name string) (*MultihopTunnel, error) {
	row := b.db.QueryRow(`
		SELECT id, name, enabled, interface_name, listen_port, private_key, public_key,
		       remote_endpoint, remote_public_key, remote_preshared_key, remote_allowed_ips, remote_keepalive,
		       fwmark, routing_table, routing_table_id, priority,
		       status, error_msg, started_at, created_at
		FROM multihop_tunnels WHERE name = ?`, name)
	return scanMultihopTunnel(row)
}

// DeleteMultihopTunnel removes a tunnel by name.
func (b *BridgeDB) DeleteMultihopTunnel(name string) error {
	result, err := b.db.Exec("DELETE FROM multihop_tunnels WHERE name = ?", name)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// ListMultihopTunnels returns all tunnels.
func (b *BridgeDB) ListMultihopTunnels() ([]MultihopTunnel, error) {
	rows, err := b.db.Query(`
		SELECT id, name, enabled, interface_name, listen_port, private_key, public_key,
		       remote_endpoint, remote_public_key, remote_preshared_key, remote_allowed_ips, remote_keepalive,
		       fwmark, routing_table, routing_table_id, priority,
		       status, error_msg, started_at, created_at
		FROM multihop_tunnels ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	var tunnels []MultihopTunnel
	for rows.Next() {
		t, err := scanMultihopTunnel(rows)
		if err != nil {
			return nil, err
		}
		tunnels = append(tunnels, *t)
	}
	return tunnels, nil
}

// EnabledMultihopTunnels returns tunnels with enabled=1 for crash recovery.
func (b *BridgeDB) EnabledMultihopTunnels() ([]MultihopTunnel, error) {
	rows, err := b.db.Query(`
		SELECT id, name, enabled, interface_name, listen_port, private_key, public_key,
		       remote_endpoint, remote_public_key, remote_preshared_key, remote_allowed_ips, remote_keepalive,
		       fwmark, routing_table, routing_table_id, priority,
		       status, error_msg, started_at, created_at
		FROM multihop_tunnels WHERE enabled = 1 ORDER BY priority`)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	var tunnels []MultihopTunnel
	for rows.Next() {
		t, err := scanMultihopTunnel(rows)
		if err != nil {
			return nil, err
		}
		tunnels = append(tunnels, *t)
	}
	return tunnels, nil
}

// --- State updates ---

// SetMultihopEnabled sets the enabled (crash recovery) flag.
func (b *BridgeDB) SetMultihopEnabled(name string, enabled bool) error {
	result, err := b.db.Exec("UPDATE multihop_tunnels SET enabled = ? WHERE name = ?", boolToInt(enabled), name)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// SetMultihopStatus updates runtime status (running/stopped/error).
func (b *BridgeDB) SetMultihopStatus(name, status, errorMsg string, startedAt *int64) error {
	_, err := b.db.Exec(`
		UPDATE multihop_tunnels SET status = ?, error_msg = ?, started_at = ?
		WHERE name = ?`, status, errorMsg, startedAt, name)
	return err
}

// ClearMultihopRuntimeState resets all tunnel statuses to 'stopped' on startup.
func (b *BridgeDB) ClearMultihopRuntimeState() error {
	_, err := b.db.Exec("UPDATE multihop_tunnels SET status = 'stopped', error_msg = NULL, started_at = NULL")
	return err
}

// UpdateMultihopTunnel updates connection details for an existing tunnel.
func (b *BridgeDB) UpdateMultihopTunnel(t *MultihopTunnel) error {
	result, err := b.db.Exec(`
		UPDATE multihop_tunnels SET
			remote_endpoint = ?, remote_public_key = ?, remote_preshared_key = ?,
			remote_allowed_ips = ?, remote_keepalive = ?,
			fwmark = ?, routing_table = ?, routing_table_id = ?, priority = ?
		WHERE name = ?`,
		t.RemoteEndpoint, t.RemotePublicKey, t.RemotePresharedKey,
		t.RemoteAllowedIPs, t.RemoteKeepalive,
		t.FWMark, t.RoutingTable, t.RoutingTableID, t.Priority,
		t.Name)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// --- JSON ---

func (t *MultihopTunnel) ToJSON() string {
	b, _ := json.Marshal(t)
	return string(b)
}

func MultihopTunnelListToJSON(tunnels []MultihopTunnel) string {
	if tunnels == nil {
		tunnels = []MultihopTunnel{}
	}
	b, _ := json.Marshal(tunnels)
	return string(b)
}

// --- Helpers ---

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

func scanMultihopTunnel(s scanner) (*MultihopTunnel, error) {
	var t MultihopTunnel
	var enabled int
	var remotePSK, errorMsg sql.NullString
	var startedAt sql.NullInt64

	if err := s.Scan(
		&t.ID, &t.Name, &enabled, &t.InterfaceName, &t.ListenPort, &t.PrivateKey, &t.PublicKey,
		&t.RemoteEndpoint, &t.RemotePublicKey, &remotePSK, &t.RemoteAllowedIPs, &t.RemoteKeepalive,
		&t.FWMark, &t.RoutingTable, &t.RoutingTableID, &t.Priority,
		&t.Status, &errorMsg, &startedAt, &t.CreatedAt,
	); err != nil {
		return nil, fmt.Errorf("scan multihop: %w", err)
	}
	t.Enabled = enabled == 1
	if remotePSK.Valid {
		t.RemotePresharedKey = remotePSK.String
	}
	if errorMsg.Valid {
		t.ErrorMsg = errorMsg.String
	}
	if startedAt.Valid {
		v := startedAt.Int64
		t.StartedAt = &v
	}
	return &t, nil
}
