package db

import (
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"net"
	"time"
)

// peerColumns is the canonical SELECT column list for peers table.
const peerColumns = `id, public_key, preshared_key, private_key, allowed_ip, allowed_ip_v6,
	keepalive, enabled, created_at, peer_index, endpoint, last_handshake, rx_bytes, tx_bytes`

// ClientRecord represents a peer/client in bridge-db.
type ClientRecord struct {
	ID            int64  `json:"id"`
	PublicKey     string `json:"public_key"`
	PresharedKey  string `json:"preshared_key,omitempty"`
	PrivateKey    string `json:"private_key"`
	AllowedIP     string `json:"allowed_ip"`
	AllowedIPv6   string `json:"allowed_ip_v6,omitempty"`
	Keepalive     int    `json:"keepalive"`
	Enabled       bool   `json:"enabled"`
	CreatedAt     int64  `json:"created_at"`
	PeerIndex     *int64 `json:"peer_index,omitempty"`
	Endpoint      string `json:"endpoint,omitempty"`
	LastHandshake *int64 `json:"last_handshake,omitempty"`
	RxBytes       int64  `json:"rx_bytes"`
	TxBytes       int64  `json:"tx_bytes"`
}

// ClientList is a paginated list of clients.
type ClientList struct {
	Clients []ClientRecord `json:"clients"`
	Total   int            `json:"total"`
	Page    int            `json:"page"`
	Limit   int            `json:"limit"`
}

// DeviceRecord represents the WireGuard device in bridge-db.
type DeviceRecord struct {
	Name       string `json:"name"`
	PrivateKey string `json:"private_key"`
	PublicKey  string `json:"public_key"`
	ListenPort int    `json:"listen_port"`
	StartedAt  *int64 `json:"started_at,omitempty"`
}

// --- Device operations ---

// UpsertDevice creates or replaces the device record (singleton, id=1).
func (b *BridgeDB) UpsertDevice(name, privKey, pubKey string, port int) error {
	_, err := b.db.Exec(`
		INSERT OR REPLACE INTO device (id, name, private_key, public_key, listen_port)
		VALUES (1, ?, ?, ?, ?)`,
		name, privKey, pubKey, port)
	return err
}

// GetDevice returns the device record.
func (b *BridgeDB) GetDevice() (*DeviceRecord, error) {
	row := b.db.QueryRow("SELECT name, private_key, public_key, listen_port, started_at FROM device WHERE id = 1")
	var d DeviceRecord
	if err := row.Scan(&d.Name, &d.PrivateKey, &d.PublicKey, &d.ListenPort, &d.StartedAt); err != nil {
		return nil, err
	}
	return &d, nil
}

// SetDeviceStartedAt updates the started_at timestamp.
func (b *BridgeDB) SetDeviceStartedAt(t *int64) error {
	_, err := b.db.Exec("UPDATE device SET started_at = ? WHERE id = 1", t)
	return err
}

// --- Client (peer) operations ---

// InsertClient adds a new client to bridge-db.
func (b *BridgeDB) InsertClient(rec *ClientRecord) error {
	rec.CreatedAt = time.Now().Unix()
	var ipv6 interface{}
	if rec.AllowedIPv6 != "" {
		ipv6 = rec.AllowedIPv6
	}
	result, err := b.db.Exec(`
		INSERT INTO peers (public_key, preshared_key, private_key, allowed_ip, allowed_ip_v6, keepalive, enabled, created_at)
		VALUES (?, ?, ?, ?, ?, ?, 1, ?)`,
		rec.PublicKey, rec.PresharedKey, rec.PrivateKey, rec.AllowedIP, ipv6, rec.Keepalive, rec.CreatedAt)
	if err != nil {
		return err
	}
	rec.ID, _ = result.LastInsertId()
	rec.Enabled = true
	return nil
}

// DeleteClient removes a client by public key and releases its IP(s).
func (b *BridgeDB) DeleteClient(pubKey string) error {
	tx, err := b.db.Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	// Release IPs back to pool
	_, _ = tx.Exec("UPDATE ip_pool SET assigned = 0, peer_id = NULL WHERE peer_id = (SELECT id FROM peers WHERE public_key = ?)", pubKey)

	result, err := tx.Exec("DELETE FROM peers WHERE public_key = ?", pubKey)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return tx.Commit()
}

// GetClient retrieves a client by public key.
func (b *BridgeDB) GetClient(pubKey string) (*ClientRecord, error) {
	row := b.db.QueryRow("SELECT "+peerColumns+" FROM peers WHERE public_key = ?", pubKey)
	return scanClient(row)
}

// ListClients returns a paginated list of all clients.
func (b *BridgeDB) ListClients(page, limit int) (*ClientList, error) {
	if page < 1 {
		page = 1
	}
	if limit < 1 || limit > 100 {
		limit = 50
	}
	offset := (page - 1) * limit

	var total int
	if err := b.db.QueryRow("SELECT COUNT(*) FROM peers").Scan(&total); err != nil {
		return nil, err
	}

	rows, err := b.db.Query("SELECT "+peerColumns+" FROM peers ORDER BY id LIMIT ? OFFSET ?", limit, offset)
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	var clients []ClientRecord
	for rows.Next() {
		c, err := scanClient(rows)
		if err != nil {
			return nil, err
		}
		clients = append(clients, *c)
	}
	if clients == nil {
		clients = []ClientRecord{}
	}

	return &ClientList{
		Clients: clients,
		Total:   total,
		Page:    page,
		Limit:   limit,
	}, nil
}

// SetEnabled toggles the enabled status of a client.
func (b *BridgeDB) SetEnabled(pubKey string, enabled bool) error {
	val := 0
	if enabled {
		val = 1
	}
	result, err := b.db.Exec("UPDATE peers SET enabled = ?, peer_index = NULL WHERE public_key = ?", val, pubKey)
	if err != nil {
		return err
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// SetPeerIndex updates the bridge handle for a peer.
func (b *BridgeDB) SetPeerIndex(pubKey string, idx *int64) error {
	_, err := b.db.Exec("UPDATE peers SET peer_index = ? WHERE public_key = ?", idx, pubKey)
	return err
}

// EnabledClients returns all enabled clients for startup restoration.
func (b *BridgeDB) EnabledClients() ([]ClientRecord, error) {
	rows, err := b.db.Query("SELECT "+peerColumns+" FROM peers WHERE enabled = 1 ORDER BY id")
	if err != nil {
		return nil, err
	}
	defer func() { _ = rows.Close() }()

	var clients []ClientRecord
	for rows.Next() {
		c, err := scanClient(rows)
		if err != nil {
			return nil, err
		}
		clients = append(clients, *c)
	}
	return clients, nil
}

// UpdateStats updates runtime stats for a client (called by stats syncer).
func (b *BridgeDB) UpdateStats(pubKey string, endpoint string, lastHandshake *int64, rxBytes, txBytes int64) error {
	_, err := b.db.Exec(`
		UPDATE peers SET endpoint = ?, last_handshake = ?, rx_bytes = ?, tx_bytes = ?
		WHERE public_key = ?`,
		endpoint, lastHandshake, rxBytes, txBytes, pubKey)
	return err
}

// ClearRuntimeState resets ephemeral fields on shutdown.
func (b *BridgeDB) ClearRuntimeState() error {
	_, err := b.db.Exec("UPDATE peers SET peer_index = NULL")
	return err
}

// ============================================================================
// IP Pool — per-address tracking with gap reuse
// ============================================================================

// InitIPPool populates the ip_pool table from a CIDR network.
// Skips .0 (network) and .1 (gateway). Idempotent — skips if already populated.
// If networkV6 is non-empty, also populates IPv6 addresses.
func (b *BridgeDB) InitIPPool(network, networkV6 string) error {
	var count int
	if err := b.db.QueryRow("SELECT COUNT(*) FROM ip_pool WHERE family = 4").Scan(&count); err != nil {
		return err
	}
	if count > 0 {
		return b.initIPPoolV6(networkV6) // only add v6 if missing
	}

	// Populate IPv4
	ips, err := expandSubnet(network, 4)
	if err != nil {
		return fmt.Errorf("expand v4: %w", err)
	}

	tx, err := b.db.Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	stmt, err := tx.Prepare("INSERT INTO ip_pool (ip, family, assigned) VALUES (?, 4, 0)")
	if err != nil {
		return err
	}
	defer func() { _ = stmt.Close() }()

	for _, ip := range ips {
		if _, err := stmt.Exec(ip); err != nil {
			return err
		}
	}

	if err := tx.Commit(); err != nil {
		return err
	}

	return b.initIPPoolV6(networkV6)
}

func (b *BridgeDB) initIPPoolV6(networkV6 string) error {
	if networkV6 == "" {
		return nil
	}
	var count int
	if err := b.db.QueryRow("SELECT COUNT(*) FROM ip_pool WHERE family = 6").Scan(&count); err != nil {
		return err
	}
	if count > 0 {
		return nil
	}

	ips, err := expandSubnet(networkV6, 6)
	if err != nil {
		return fmt.Errorf("expand v6: %w", err)
	}

	tx, err := b.db.Begin()
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	stmt, err := tx.Prepare("INSERT INTO ip_pool (ip, family, assigned) VALUES (?, 6, 0)")
	if err != nil {
		return err
	}
	defer func() { _ = stmt.Close() }()

	for _, ip := range ips {
		if _, err := stmt.Exec(ip); err != nil {
			return err
		}
	}

	return tx.Commit()
}

// AllocateIP finds the first unassigned IP, marks it assigned, and links to peer.
// Returns CIDR notation (e.g. "10.8.0.2/32" or "fd00::2/128").
func (b *BridgeDB) AllocateIP(peerID int64, family int) (string, error) {
	tx, err := b.db.Begin()
	if err != nil {
		return "", err
	}
	defer func() { _ = tx.Rollback() }()

	var ip string
	err = tx.QueryRow("SELECT ip FROM ip_pool WHERE family = ? AND assigned = 0 ORDER BY rowid LIMIT 1", family).Scan(&ip)
	if err != nil {
		return "", fmt.Errorf("ip pool exhausted (family=%d): %w", family, err)
	}

	if _, err := tx.Exec("UPDATE ip_pool SET assigned = 1, peer_id = ? WHERE ip = ?", peerID, ip); err != nil {
		return "", err
	}

	if err := tx.Commit(); err != nil {
		return "", err
	}

	cidr := "/32"
	if family == 6 {
		cidr = "/128"
	}
	return ip + cidr, nil
}

// ReleaseIP marks an IP as unassigned.
func (b *BridgeDB) ReleaseIP(ip string) error {
	// Strip CIDR suffix if present
	for i := len(ip) - 1; i >= 0; i-- {
		if ip[i] == '/' {
			ip = ip[:i]
			break
		}
	}
	_, err := b.db.Exec("UPDATE ip_pool SET assigned = 0, peer_id = NULL WHERE ip = ?", ip)
	return err
}

// expandSubnet generates usable host IPs from a CIDR.
// For IPv4: skips .0 (network) and .1 (gateway).
// For IPv6: generates first 253 hosts after ::1 (practical limit for WG peers).
func expandSubnet(cidr string, family int) ([]string, error) {
	_, ipNet, err := net.ParseCIDR(cidr)
	if err != nil {
		return nil, fmt.Errorf("parse cidr: %w", err)
	}

	if family == 4 {
		return expandV4(ipNet), nil
	}
	return expandV6(ipNet), nil
}

func expandV4(ipNet *net.IPNet) []string {
	base := ipNet.IP.To4()
	if base == nil {
		return nil
	}

	ones, bits := ipNet.Mask.Size()
	hostCount := (1 << (bits - ones)) - 2 // exclude network + broadcast
	if hostCount <= 1 {
		return nil
	}

	baseInt := binary.BigEndian.Uint32(base)
	var ips []string
	// Start from .2 (skip .0 network, .1 gateway)
	for i := 2; i <= hostCount; i++ {
		ip := make(net.IP, 4)
		binary.BigEndian.PutUint32(ip, baseInt+uint32(i))
		if ipNet.Contains(ip) {
			ips = append(ips, ip.String())
		}
	}
	return ips
}

func expandV6(ipNet *net.IPNet) []string {
	base := ipNet.IP.To16()
	if base == nil {
		return nil
	}

	// Generate first 253 usable addresses (::2 through ::fe)
	var ips []string
	for i := 2; i <= 254; i++ {
		ip := make(net.IP, 16)
		copy(ip, base)
		ip[15] = byte(i)
		if ipNet.Contains(ip) {
			ips = append(ips, ip.String())
		}
	}
	return ips
}

// --- JSON helpers ---

// ToJSON marshals the record to JSON string.
func (c *ClientRecord) ToJSON() string {
	b, _ := json.Marshal(c)
	return string(b)
}

// ToJSON marshals the list to JSON string.
func (cl *ClientList) ToJSON() string {
	b, _ := json.Marshal(cl)
	return string(b)
}

// --- scan helpers ---

type scanner interface {
	Scan(dest ...interface{}) error
}

func scanClient(s scanner) (*ClientRecord, error) {
	var c ClientRecord
	var enabled int
	var psk, ipv6, endpoint sql.NullString
	var peerIdx, handshake sql.NullInt64
	if err := s.Scan(
		&c.ID, &c.PublicKey, &psk, &c.PrivateKey, &c.AllowedIP, &ipv6,
		&c.Keepalive, &enabled, &c.CreatedAt, &peerIdx, &endpoint, &handshake, &c.RxBytes, &c.TxBytes,
	); err != nil {
		return nil, err
	}
	c.Enabled = enabled == 1
	if psk.Valid {
		c.PresharedKey = psk.String
	}
	if ipv6.Valid {
		c.AllowedIPv6 = ipv6.String
	}
	if endpoint.Valid {
		c.Endpoint = endpoint.String
	}
	if peerIdx.Valid {
		v := peerIdx.Int64
		c.PeerIndex = &v
	}
	if handshake.Valid {
		v := handshake.Int64
		c.LastHandshake = &v
	}
	return &c, nil
}