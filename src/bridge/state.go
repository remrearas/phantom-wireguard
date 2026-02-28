package bridge

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun"

	"wireguard-go-bridge/core"
	"wireguard-go-bridge/db"
)

// Status represents the lifecycle state of the bridge.
type Status string

const (
	StatusUninitialized Status = "uninitialized" // BridgeInit not called
	StatusNeedsSetup    Status = "needs_setup"   // DB exists but server_config empty
	StatusReady         Status = "ready"          // Configured, not started
	StatusRunning       Status = "running"        // Device up, peers active
	StatusError         Status = "error"          // Something failed
)

// State manages the bridge-db backed WireGuard device.
// This is the high-level API — single source of truth for client state.
type State struct {
	mu          sync.RWMutex
	db          *db.BridgeDB
	dev         *device.Device
	tunDev      tun.Device
	logger      *device.Logger
	statsSyncer *db.StatsSyncer
	ifname      string
	status      Status
	lastError   string
}

// StatusInfo holds the full bridge status for Python to read.
type StatusInfo struct {
	Status     Status `json:"status"`
	Error      string       `json:"error,omitempty"`
	HasDevice  bool         `json:"has_device"`
	HasConfig  bool         `json:"has_config"`
	PeerCount  int          `json:"peer_count"`
	MultihopCount int       `json:"multihop_count"`
}

// DeviceInfo holds device metadata returned by GetDeviceInfo.
type DeviceInfo struct {
	Name       string `json:"name"`
	PublicKey  string `json:"public_key"`
	ListenPort int    `json:"listen_port"`
	PeerCount  int    `json:"peer_count"`
	StartedAt  *int64 `json:"started_at,omitempty"`
}

// New creates an uninitialized State.
func New() *State {
	return &State{status: StatusUninitialized}
}

// Init opens bridge-db, determines state, and prepares the bridge.
// If DB is fresh (no device record), status = needs_setup.
// If DB has device + server_config, status = ready (can Start).
// Device is NOT created here — Start() creates and configures the device.
func (s *State) Init(dbPath, ifname string, listenPort, logLevel int) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Auto-close previous state if re-initializing (singleton reset)
	if s.status != StatusUninitialized {
		s.closeInternal()
	}

	// Open SQLite
	database, err := db.Open(dbPath)
	if err != nil {
		s.status = StatusError
		s.lastError = err.Error()
		return fmt.Errorf("db open: %w", err)
	}

	s.db = database
	s.ifname = ifname
	s.logger = newCallbackLogger(logLevel, "("+ifname+") ")

	// Clear stale runtime state from previous crash
	_ = database.ClearRuntimeState()
	_ = database.ClearMultihopRuntimeState()

	// Check existing state
	devRec, devErr := database.GetDevice()
	_, cfgErr := database.GetServerConfig(1)

	if devErr != nil || devRec == nil {
		// Fresh DB — generate server keypair and write device record
		privKey, err := core.GeneratePrivateKey()
		if err != nil {
			_ = database.Close()
			return fmt.Errorf("keygen: %w", err)
		}
		pubKey, err := core.DerivePublicKey(privKey)
		if err != nil {
			_ = database.Close()
			return fmt.Errorf("derive pub: %w", err)
		}
		if err := database.UpsertDevice(ifname, privKey, pubKey, listenPort); err != nil {
			_ = database.Close()
			return fmt.Errorf("db upsert: %w", err)
		}
	}

	if cfgErr != nil {
		// No server_config — user must configure before Start
		s.status = StatusNeedsSetup
	} else {
		s.status = StatusReady
	}

	return nil
}

// Setup performs initial configuration: creates server_config and IP pool.
// Called by Python daemon after collecting user input on first run.
// Transitions: needs_setup → ready.
func (s *State) Setup(endpoint, network, dnsPrimary, dnsSecondary string, mtu, fwmark int) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status != StatusNeedsSetup && s.status != StatusReady {
		return fmt.Errorf("invalid state for setup: %s", s.status)
	}

	if network == "" {
		network = "10.8.0.0/24"
	}
	if dnsPrimary == "" {
		dnsPrimary = "1.1.1.1"
	}
	if mtu == 0 {
		mtu = 1420
	}

	cfg := &db.ServerConfig{
		DeviceID:     1,
		Endpoint:     endpoint,
		Network:      network,
		DNSPrimary:   dnsPrimary,
		DNSSecondary: dnsSecondary,
		MTU:          mtu,
		FWMark:       fwmark,
	}
	if err := s.db.UpsertServerConfig(cfg); err != nil {
		return fmt.Errorf("save config: %w", err)
	}

	// Initialize IP pool from network (v6 populated if non-empty)
	serverCfg, _ := s.db.GetServerConfig(1)
	v6Net := ""
	if serverCfg != nil {
		v6Net = serverCfg.NetworkV6
	}
	_ = s.db.InitIPPool(network, v6Net)

	s.status = StatusReady
	return nil
}

// Close shuts down everything and closes the database.
// Transitions: any → uninitialized.
func (s *State) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	s.closeInternal()
	return nil
}

// closeInternal performs cleanup without locking (caller must hold mu).
func (s *State) closeInternal() {
	if s.statsSyncer != nil {
		s.statsSyncer.Stop()
		s.statsSyncer = nil
	}

	// Close all multihop devices
	multihopRegistryMu.Lock()
	for name, entry := range multihopRegistry {
		entry.device.Close()
		delete(multihopRegistry, name)
	}
	multihopRegistryMu.Unlock()

	if s.db != nil {
		_ = s.db.ClearRuntimeState()
		_ = s.db.ClearMultihopRuntimeState()
		_ = s.db.SetDeviceStartedAt(nil)
	}

	if s.dev != nil {
		s.dev.Close()
		s.dev = nil
	}
	if s.db != nil {
		_ = s.db.Close()
		s.db = nil
	}

	s.status = StatusUninitialized
	s.lastError = ""
}

// Start creates the WireGuard device, configures it from DB, restores
// peers and multihop tunnels. Transitions: ready → running.
func (s *State) Start() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusRunning {
		return fmt.Errorf("already running")
	}
	if s.status != StatusReady {
		return fmt.Errorf("not ready (status=%s), run Setup first", s.status)
	}

	// Read device and server config from DB
	devRec, err := s.db.GetDevice()
	if err != nil {
		s.setError("read device: " + err.Error())
		return fmt.Errorf("read device: %w", err)
	}
	serverCfg, err := s.db.GetServerConfig(1)
	if err != nil {
		s.setError("read server config: " + err.Error())
		return fmt.Errorf("read server config: %w", err)
	}

	// Create TUN + WireGuard device
	tunDev, err := tun.CreateTUN(s.ifname, serverCfg.MTU)
	if err != nil {
		s.setError("tun create: " + err.Error())
		return fmt.Errorf("tun: %w", err)
	}

	dev := device.NewDevice(tunDev, conn.NewDefaultBind(), s.logger)
	if dev == nil {
		_ = tunDev.Close()
		s.setError("device create failed")
		return fmt.Errorf("device create failed")
	}

	// Configure device via IPC from DB state
	ipcConfig := fmt.Sprintf("private_key=%s\nlisten_port=%d\n", devRec.PrivateKey, devRec.ListenPort)
	if serverCfg.FWMark != 0 {
		ipcConfig += fmt.Sprintf("fwmark=%d\n", serverCfg.FWMark)
	}
	if err := dev.IpcSet(ipcConfig); err != nil {
		dev.Close()
		s.setError("ipc set: " + err.Error())
		return fmt.Errorf("ipc set: %w", err)
	}

	// Activate
	if err := dev.Up(); err != nil {
		dev.Close()
		s.setError("device up: " + err.Error())
		return fmt.Errorf("device up: %w", err)
	}

	s.dev = dev
	s.tunDev = tunDev

	now := time.Now().Unix()
	_ = s.db.SetDeviceStartedAt(&now)

	// Restore enabled peers from DB
	clients, err := s.db.EnabledClients()
	if err == nil {
		for _, c := range clients {
			s.addPeerToDevice(c)
		}
	}

	// Restore enabled multihop tunnels (crash recovery)
	s.restoreMultihopTunnels()

	s.status = StatusRunning
	s.lastError = ""
	return nil
}

// Stop deactivates the device. Transitions: running → ready.
func (s *State) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status != StatusRunning {
		return fmt.Errorf("not running")
	}

	if s.dev != nil {
		_ = s.dev.Down()
		s.dev.Close()
		s.dev = nil
	}

	_ = s.db.ClearRuntimeState()
	_ = s.db.ClearMultihopRuntimeState()
	_ = s.db.SetDeviceStartedAt(nil)

	s.status = StatusReady
	return nil
}

// AddClient generates keys, adds peer to device, writes to bridge-db.
// If allowedIP is empty, auto-allocates from the IPv4 pool.
// If server has IPv6 configured, also allocates an IPv6 address.
// Returns JSON with client info.
func (s *State) AddClient(allowedIP string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.requireRunning(); err != nil {
		return "", err
	}

	// Generate client keypair + PSK
	privKey, err := core.GeneratePrivateKey()
	if err != nil {
		return "", fmt.Errorf("keygen: %w", err)
	}
	pubKey, err := core.DerivePublicKey(privKey)
	if err != nil {
		return "", fmt.Errorf("derive pub: %w", err)
	}
	psk, err := core.GeneratePresharedKey()
	if err != nil {
		return "", fmt.Errorf("psk: %w", err)
	}

	// Write to bridge-db first (to get peer ID for pool allocation)
	rec := &db.ClientRecord{
		PublicKey:    pubKey,
		PresharedKey: psk,
		PrivateKey:  privKey,
		AllowedIP:   allowedIP, // may be empty, will be set below
		Keepalive:   25,
	}

	// Temporary insert to get ID (AllowedIP filled after allocation)
	if allowedIP == "" {
		rec.AllowedIP = "pending" // placeholder, updated below
	}
	if err := s.db.InsertClient(rec); err != nil {
		return "", fmt.Errorf("db insert: %w", err)
	}

	// Auto-allocate IPv4 if not provided
	if allowedIP == "" {
		ip, err := s.db.AllocateIP(rec.ID, 4)
		if err != nil {
			_ = s.db.DeleteClient(pubKey)
			return "", fmt.Errorf("ip alloc v4: %w", err)
		}
		rec.AllowedIP = ip
		_, _ = s.db.DB().Exec("UPDATE peers SET allowed_ip = ? WHERE id = ?", ip, rec.ID)
	}

	// Allocate IPv6 if server has it configured
	serverCfg, cfgErr := s.db.GetServerConfig(1)
	if cfgErr == nil && serverCfg.HasIPv6() {
		ipv6, err := s.db.AllocateIP(rec.ID, 6)
		if err == nil {
			rec.AllowedIPv6 = ipv6
			_, _ = s.db.DB().Exec("UPDATE peers SET allowed_ip_v6 = ? WHERE id = ?", ipv6, rec.ID)
		}
	}

	// Add peer to WireGuard device via IPC
	ipcConfig := fmt.Sprintf(
		"public_key=%s\npreshared_key=%s\nallowed_ip=%s\npersistent_keepalive_interval=25\n",
		pubKey, psk, rec.AllowedIP,
	)
	if rec.AllowedIPv6 != "" {
		ipcConfig += fmt.Sprintf("allowed_ip=%s\n", rec.AllowedIPv6)
	}
	if err := s.dev.IpcSet(ipcConfig); err != nil {
		// Rollback
		_ = s.db.DeleteClient(pubKey)
		return "", fmt.Errorf("ipc set peer: %w", err)
	}

	return rec.ToJSON(), nil
}

// RemoveClient removes peer from device and deletes from bridge-db.
func (s *State) RemoveClient(pubKeyHex string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.requireRunning(); err != nil {
		return err
	}

	// Remove from device
	config := fmt.Sprintf("public_key=%s\nremove=true\n", pubKeyHex)
	_ = s.dev.IpcSet(config)

	// Delete from DB
	return s.db.DeleteClient(pubKeyHex)
}

// EnableClient re-adds peer to device and sets enabled=1 in bridge-db.
func (s *State) EnableClient(pubKeyHex string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.requireRunning(); err != nil {
		return err
	}

	client, err := s.db.GetClient(pubKeyHex)
	if err != nil {
		return fmt.Errorf("get client: %w", err)
	}

	s.addPeerToDevice(*client)
	return s.db.SetEnabled(pubKeyHex, true)
}

// DisableClient removes peer from device and sets enabled=0 in bridge-db.
func (s *State) DisableClient(pubKeyHex string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if err := s.requireRunning(); err != nil {
		return err
	}

	config := fmt.Sprintf("public_key=%s\nremove=true\n", pubKeyHex)
	_ = s.dev.IpcSet(config)

	return s.db.SetEnabled(pubKeyHex, false)
}

// GetClient returns client info as JSON.
func (s *State) GetClient(pubKeyHex string) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	client, err := s.db.GetClient(pubKeyHex)
	if err != nil {
		return "", err
	}
	return client.ToJSON(), nil
}

// ListClients returns paginated client list as JSON.
func (s *State) ListClients(page, limit int) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	list, err := s.db.ListClients(page, limit)
	if err != nil {
		return "", err
	}
	return list.ToJSON(), nil
}

// ExportClientConfig generates a WireGuard client config file string.
// If serverEndpoint or dns are empty, values from server_config are used.
func (s *State) ExportClientConfig(pubKeyHex, serverEndpoint, dns string) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	client, err := s.db.GetClient(pubKeyHex)
	if err != nil {
		return "", fmt.Errorf("get client: %w", err)
	}
	devRec, err := s.db.GetDevice()
	if err != nil {
		return "", fmt.Errorf("get device: %w", err)
	}

	// Get server config once — used for defaults and MTU
	serverCfg, _ := s.db.GetServerConfig(1)
	if serverCfg != nil {
		if serverEndpoint == "" {
			serverEndpoint = serverCfg.Endpoint
		}
		if dns == "" {
			dns = serverCfg.DNSString()
		}
	}

	// Convert hex keys to base64 for WireGuard config
	privB64, err := core.HexToBase64(client.PrivateKey)
	if err != nil {
		return "", fmt.Errorf("key convert: %w", err)
	}
	serverPubB64, err := core.HexToBase64(devRec.PublicKey)
	if err != nil {
		return "", fmt.Errorf("key convert: %w", err)
	}
	pskB64, err := core.HexToBase64(client.PresharedKey)
	if err != nil {
		return "", fmt.Errorf("key convert: %w", err)
	}

	// Build Address field: IPv4 /24 + optional IPv6
	addr := client.AllowedIP
	if len(addr) > 3 && addr[len(addr)-3:] == "/32" {
		addr = addr[:len(addr)-3] + "/24"
	}
	if client.AllowedIPv6 != "" {
		v6Addr := client.AllowedIPv6
		if len(v6Addr) > 4 && v6Addr[len(v6Addr)-4:] == "/128" {
			v6Addr = v6Addr[:len(v6Addr)-4] + "/64"
		}
		addr += ", " + v6Addr
	}

	mtu := 1420
	if serverCfg != nil {
		mtu = serverCfg.MTU
	}

	// AllowedIPs: dual-stack if IPv6 configured
	allowedIPs := "0.0.0.0/0"
	if client.AllowedIPv6 != "" {
		allowedIPs = "0.0.0.0/0, ::/0"
	}

	config := fmt.Sprintf(`[Interface]
PrivateKey = %s
Address = %s
DNS = %s
MTU = %d

[Peer]
PublicKey = %s
PresharedKey = %s
AllowedIPs = %s
Endpoint = %s
PersistentKeepalive = 25
`, privB64, addr, dns, mtu, serverPubB64, pskB64, allowedIPs, serverEndpoint)

	return config, nil
}

// GetServerConfig returns server configuration as JSON.
func (s *State) GetServerConfig() (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	cfg, err := s.db.GetServerConfig(1)
	if err != nil {
		return "", err
	}
	return cfg.ToJSON(), nil
}

// SetServerConfig updates server configuration from JSON.
func (s *State) SetServerConfig(configJSON string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	var cfg db.ServerConfig
	if err := json.Unmarshal([]byte(configJSON), &cfg); err != nil {
		return fmt.Errorf("parse config: %w", err)
	}
	cfg.DeviceID = 1

	// Apply fwmark to device if changed
	if cfg.FWMark != 0 {
		fwConfig := fmt.Sprintf("fwmark=%d\n", cfg.FWMark)
		_ = s.dev.IpcSet(fwConfig)
	}

	return s.db.UpsertServerConfig(&cfg)
}

// StartStatsSync starts the background stats synchronization goroutine.
func (s *State) StartStatsSync(intervalSec int) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}
	if s.statsSyncer != nil {
		return fmt.Errorf("stats already running")
	}

	ipcGetFn := func() (string, error) {
		return s.dev.IpcGet()
	}
	s.statsSyncer = db.NewStatsSyncer(s.db, ipcGetFn, intervalSec)
	s.statsSyncer.Start()
	return nil
}

// StopStatsSync stops the background stats synchronization.
func (s *State) StopStatsSync() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.statsSyncer == nil {
		return nil
	}
	s.statsSyncer.Stop()
	s.statsSyncer = nil
	return nil
}

// GetDeviceInfo returns device metadata as JSON.
func (s *State) GetDeviceInfo() (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	devRec, err := s.db.GetDevice()
	if err != nil {
		return "", err
	}

	list, err := s.db.ListClients(1, 1)
	if err != nil {
		return "", err
	}

	info := DeviceInfo{
		Name:       devRec.Name,
		PublicKey:  devRec.PublicKey,
		ListenPort: devRec.ListenPort,
		PeerCount:  list.Total,
		StartedAt:  devRec.StartedAt,
	}
	b, _ := json.Marshal(info)
	return string(b), nil
}

// ============================================================================
// Status
// ============================================================================

// GetStatus returns the current bridge status as JSON.
func (s *State) GetStatus() string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	info := StatusInfo{
		Status: s.status,
		Error:  s.lastError,
	}

	if s.db != nil {
		if devRec, err := s.db.GetDevice(); err == nil && devRec != nil {
			info.HasDevice = true
		}
		if _, err := s.db.GetServerConfig(1); err == nil {
			info.HasConfig = true
		}
		if list, err := s.db.ListClients(1, 1); err == nil {
			info.PeerCount = list.Total
		}
		if tunnels, err := s.db.ListMultihopTunnels(); err == nil {
			info.MultihopCount = len(tunnels)
		}
	}

	b, _ := json.Marshal(info)
	return string(b)
}

func (s *State) setError(msg string) {
	s.status = StatusError
	s.lastError = msg
}

func (s *State) requireRunning() error {
	if s.status != StatusRunning {
		return fmt.Errorf("not running (status=%s)", s.status)
	}
	return nil
}

// ============================================================================
// Multihop Tunnel Lifecycle
// ============================================================================

// CreateMultihopTunnel creates a new multihop tunnel config in bridge-db.
// Keys are auto-generated. The tunnel is created in 'stopped' state.
func (s *State) CreateMultihopTunnel(name, ifaceName, remoteEndpoint, remotePubKey string, fwmark int) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	privKey, err := core.GeneratePrivateKey()
	if err != nil {
		return "", fmt.Errorf("keygen: %w", err)
	}
	pubKey, err := core.DerivePublicKey(privKey)
	if err != nil {
		return "", fmt.Errorf("derive pub: %w", err)
	}

	t := &db.MultihopTunnel{
		Name:             name,
		Enabled:          false,
		InterfaceName:    ifaceName,
		ListenPort:       0,
		PrivateKey:       privKey,
		PublicKey:        pubKey,
		RemoteEndpoint:   remoteEndpoint,
		RemotePublicKey:  remotePubKey,
		RemoteAllowedIPs: "0.0.0.0/0",
		RemoteKeepalive:  25,
		FWMark:           fwmark,
		RoutingTable:     "phantom_multihop",
		RoutingTableID:   100,
		Priority:         100,
	}
	if err := s.db.InsertMultihopTunnel(t); err != nil {
		return "", fmt.Errorf("db insert: %w", err)
	}
	return t.ToJSON(), nil
}

// StartMultihopTunnel creates the WireGuard device for a tunnel,
// configures the peer, sets fwmark, and marks it running + enabled.
// On next restart, this tunnel auto-restores (crash-tolerant).
func (s *State) StartMultihopTunnel(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	t, err := s.db.GetMultihopTunnel(name)
	if err != nil {
		return fmt.Errorf("get tunnel: %w", err)
	}

	if err := s.startMultihopDevice(t); err != nil {
		_ = s.db.SetMultihopStatus(name, "error", err.Error(), nil)
		return err
	}

	now := time.Now().Unix()
	_ = s.db.SetMultihopStatus(name, "running", "", &now)
	_ = s.db.SetMultihopEnabled(name, true)
	return nil
}

// StopMultihopTunnel tears down the WireGuard device for a tunnel.
// Does NOT disable — tunnel will still restore on next restart.
func (s *State) StopMultihopTunnel(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	t, err := s.db.GetMultihopTunnel(name)
	if err != nil {
		return fmt.Errorf("get tunnel: %w", err)
	}

	s.stopMultihopDevice(t)
	_ = s.db.SetMultihopStatus(name, "stopped", "", nil)
	return nil
}

// DisableMultihopTunnel stops and disables — will NOT restore on restart.
func (s *State) DisableMultihopTunnel(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	t, err := s.db.GetMultihopTunnel(name)
	if err != nil {
		return fmt.Errorf("get tunnel: %w", err)
	}

	s.stopMultihopDevice(t)
	_ = s.db.SetMultihopStatus(name, "stopped", "", nil)
	_ = s.db.SetMultihopEnabled(name, false)
	return nil
}

// DeleteMultihopTunnel stops and removes the tunnel entirely.
func (s *State) DeleteMultihopTunnel(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.status == StatusUninitialized {
		return fmt.Errorf("not initialized")
	}

	t, _ := s.db.GetMultihopTunnel(name)
	if t != nil {
		s.stopMultihopDevice(t)
	}
	return s.db.DeleteMultihopTunnel(name)
}

// ListMultihopTunnels returns all tunnels as JSON.
func (s *State) ListMultihopTunnels() (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	tunnels, err := s.db.ListMultihopTunnels()
	if err != nil {
		return "", err
	}
	return db.MultihopTunnelListToJSON(tunnels), nil
}

// GetMultihopTunnel returns a single tunnel as JSON.
func (s *State) GetMultihopTunnel(name string) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.status == StatusUninitialized {
		return "", fmt.Errorf("not initialized")
	}

	t, err := s.db.GetMultihopTunnel(name)
	if err != nil {
		return "", err
	}
	return t.ToJSON(), nil
}

// ============================================================================
// Internal helpers
// ============================================================================

// addPeerToDevice configures a peer on the WireGuard device via IPC.
func (s *State) addPeerToDevice(c db.ClientRecord) {
	config := fmt.Sprintf(
		"public_key=%s\npreshared_key=%s\nallowed_ip=%s\npersistent_keepalive_interval=%d\n",
		c.PublicKey, c.PresharedKey, c.AllowedIP, c.Keepalive,
	)
	if c.AllowedIPv6 != "" {
		config += fmt.Sprintf("allowed_ip=%s\n", c.AllowedIPv6)
	}
	_ = s.dev.IpcSet(config)
}

// restoreMultihopTunnels restores all enabled multihop tunnels.
// Called during Start() for crash recovery.
func (s *State) restoreMultihopTunnels() {
	tunnels, err := s.db.EnabledMultihopTunnels()
	if err != nil || len(tunnels) == 0 {
		return
	}

	for _, t := range tunnels {
		if err := s.startMultihopDevice(&t); err != nil {
			_ = s.db.SetMultihopStatus(t.Name, "error", err.Error(), nil)
			if s.logger != nil {
				s.logger.Errorf("multihop restore %s: %v", t.Name, err)
			}
			continue
		}
		now := time.Now().Unix()
		_ = s.db.SetMultihopStatus(t.Name, "running", "", &now)
	}
}

// startMultihopDevice creates a TUN device, configures WireGuard,
// and adds the remote peer for a multihop tunnel.
func (s *State) startMultihopDevice(t *db.MultihopTunnel) error {
	tunDev, err := tun.CreateTUN(t.InterfaceName, device.DefaultMTU)
	if err != nil {
		return fmt.Errorf("tun %s: %w", t.InterfaceName, err)
	}

	logger := newCallbackLogger(device.LogLevelError, "("+t.InterfaceName+") ")
	dev := device.NewDevice(tunDev, conn.NewDefaultBind(), logger)
	if dev == nil {
		_ = tunDev.Close()
		return fmt.Errorf("device create %s", t.InterfaceName)
	}

	// Configure device: private key, listen port, fwmark
	ipcConfig := fmt.Sprintf("private_key=%s\n", t.PrivateKey)
	if t.ListenPort > 0 {
		ipcConfig += fmt.Sprintf("listen_port=%d\n", t.ListenPort)
	}
	if t.FWMark != 0 {
		ipcConfig += fmt.Sprintf("fwmark=%d\n", t.FWMark)
	}
	if err := dev.IpcSet(ipcConfig); err != nil {
		dev.Close()
		return fmt.Errorf("ipc set device %s: %w", t.InterfaceName, err)
	}

	// Add remote peer
	peerConfig := fmt.Sprintf(
		"public_key=%s\nendpoint=%s\nallowed_ip=%s\npersistent_keepalive_interval=%d\n",
		t.RemotePublicKey, t.RemoteEndpoint, t.RemoteAllowedIPs, t.RemoteKeepalive,
	)
	if t.RemotePresharedKey != "" {
		peerConfig += fmt.Sprintf("preshared_key=%s\n", t.RemotePresharedKey)
	}
	if err := dev.IpcSet(peerConfig); err != nil {
		dev.Close()
		return fmt.Errorf("ipc set peer %s: %w", t.InterfaceName, err)
	}

	if err := dev.Up(); err != nil {
		dev.Close()
		return fmt.Errorf("device up %s: %w", t.InterfaceName, err)
	}

	// Store in registry for cleanup
	entry := &multihopEntry{device: dev, tun: tunDev, name: t.Name}
	multihopRegistryMu.Lock()
	multihopRegistry[t.Name] = entry
	multihopRegistryMu.Unlock()

	return nil
}

// stopMultihopDevice tears down a multihop device.
func (s *State) stopMultihopDevice(t *db.MultihopTunnel) {
	multihopRegistryMu.Lock()
	entry, ok := multihopRegistry[t.Name]
	if ok {
		delete(multihopRegistry, t.Name)
	}
	multihopRegistryMu.Unlock()

	if ok {
		entry.device.Close()
	}
}

// multihopEntry tracks live multihop devices for cleanup.
type multihopEntry struct {
	device *device.Device
	tun    tun.Device
	name   string
}

var (
	multihopRegistry   = make(map[string]*multihopEntry)
	multihopRegistryMu sync.Mutex
)
