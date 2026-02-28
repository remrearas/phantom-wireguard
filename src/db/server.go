package db

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
)

// ServerConfig holds the server-side configuration that persists across restarts.
// This is the "what should be configured" layer — read at startup to bootstrap the device.
type ServerConfig struct {
	DeviceID     int    `json:"device_id"`
	Endpoint     string `json:"endpoint,omitempty"`      // 'vpn.example.com:51820'
	EndpointV6   string `json:"endpoint_v6,omitempty"`   // '[2001:db8::1]:51820'
	Network      string `json:"network"`                 // '10.8.0.0/24'
	NetworkV6    string `json:"network_v6,omitempty"`    // 'fd00::/64' — NULL = no IPv6
	DNSPrimary   string `json:"dns_primary"`             // '1.1.1.1'
	DNSSecondary string `json:"dns_secondary,omitempty"` // '9.9.9.9'
	DNSV6        string `json:"dns_v6,omitempty"`        // '2606:4700:4700::1111'
	MTU          int    `json:"mtu"`                     // 1420
	FWMark       int    `json:"fwmark"`                  // SO_MARK for policy routing
	PostUp       string `json:"post_up,omitempty"`       // hook command
	PostDown     string `json:"post_down,omitempty"`     // hook command
}

// UpsertServerConfig creates or replaces the server configuration.
func (b *BridgeDB) UpsertServerConfig(cfg *ServerConfig) error {
	_, err := b.db.Exec(`
		INSERT OR REPLACE INTO server_config
			(device_id, endpoint, endpoint_v6, network, network_v6, dns_primary, dns_secondary, dns_v6, mtu, fwmark, post_up, post_down)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		cfg.DeviceID, cfg.Endpoint, nullStr(cfg.EndpointV6), cfg.Network, nullStr(cfg.NetworkV6),
		cfg.DNSPrimary, cfg.DNSSecondary, nullStr(cfg.DNSV6),
		cfg.MTU, cfg.FWMark,
		cfg.PostUp, cfg.PostDown)
	return err
}

// GetServerConfig retrieves the server configuration for a device.
func (b *BridgeDB) GetServerConfig(deviceID int) (*ServerConfig, error) {
	row := b.db.QueryRow(`
		SELECT device_id, endpoint, endpoint_v6, network, network_v6,
		       dns_primary, dns_secondary, dns_v6, mtu, fwmark, post_up, post_down
		FROM server_config WHERE device_id = ?`, deviceID)

	var cfg ServerConfig
	var endpoint, endpointV6, networkV6, dnsSecondary, dnsV6, postUp, postDown sql.NullString
	if err := row.Scan(
		&cfg.DeviceID, &endpoint, &endpointV6, &cfg.Network, &networkV6,
		&cfg.DNSPrimary, &dnsSecondary, &dnsV6,
		&cfg.MTU, &cfg.FWMark,
		&postUp, &postDown,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, fmt.Errorf("no server config for device %d", deviceID)
		}
		return nil, err
	}
	if endpoint.Valid {
		cfg.Endpoint = endpoint.String
	}
	if endpointV6.Valid {
		cfg.EndpointV6 = endpointV6.String
	}
	if networkV6.Valid {
		cfg.NetworkV6 = networkV6.String
	}
	if dnsSecondary.Valid {
		cfg.DNSSecondary = dnsSecondary.String
	}
	if dnsV6.Valid {
		cfg.DNSV6 = dnsV6.String
	}
	if postUp.Valid {
		cfg.PostUp = postUp.String
	}
	if postDown.Valid {
		cfg.PostDown = postDown.String
	}
	return &cfg, nil
}

// GetOrCreateServerConfig returns existing config or creates a default one.
func (b *BridgeDB) GetOrCreateServerConfig(deviceID int, listenPort int) (*ServerConfig, error) {
	cfg, err := b.GetServerConfig(deviceID)
	if err == nil {
		return cfg, nil
	}

	// Create default config
	cfg = &ServerConfig{
		DeviceID:     deviceID,
		Endpoint:     fmt.Sprintf("0.0.0.0:%d", listenPort),
		Network:      "10.8.0.0/24",
		DNSPrimary:   "1.1.1.1",
		DNSSecondary: "9.9.9.9",
		MTU:          1420,
		FWMark:       0,
	}
	if err := b.UpsertServerConfig(cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}

// ToJSON marshals the config to JSON string.
func (cfg *ServerConfig) ToJSON() string {
	b, _ := json.Marshal(cfg)
	return string(b)
}

// DNSString returns comma-separated DNS servers for WireGuard config.
func (cfg *ServerConfig) DNSString() string {
	s := cfg.DNSPrimary
	if cfg.DNSSecondary != "" {
		s += ", " + cfg.DNSSecondary
	}
	if cfg.DNSV6 != "" {
		s += ", " + cfg.DNSV6
	}
	return s
}

// HasIPv6 returns true if IPv6 is configured.
func (cfg *ServerConfig) HasIPv6() bool {
	return cfg.NetworkV6 != ""
}

// nullStr converts empty string to sql NULL.
func nullStr(s string) interface{} {
	if s == "" {
		return nil
	}
	return s
}
