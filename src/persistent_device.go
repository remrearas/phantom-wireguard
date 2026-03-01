// ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
// ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
// ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
// ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
// ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
// ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
//
// Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
// Licensed under AGPL-3.0 - see LICENSE file for details
// Third-party licenses - see THIRD_PARTY_LICENSES file for details
// WireGuard® is a registered trademark of Jason A. Donenfeld.
//
// persistent_device.go — WireGuard device with IPC state persistence.
// Every IpcSet automatically persists the full device state to SQLite.
// On creation, if a previous state exists in DB, it is restored.

package main

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "github.com/mattn/go-sqlite3"
	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun"
)

// persistentDevice wraps a WireGuard device with automatic IPC state persistence.
type persistentDevice struct {
	dev *device.Device
	tun tun.Device
	db  *sql.DB
}

// newPersistentDevice creates a TUN device, WireGuard device, opens the state DB,
// and restores previous IPC state if available. DB must already exist.
func newPersistentDevice(ifname string, mtu int, dbPath string) (*persistentDevice, error) {
	// Open state DB
	db, err := sql.Open("sqlite3", dbPath+"?_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return nil, fmt.Errorf("open state db: %w", err)
	}
	if err := db.Ping(); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping state db: %w", err)
	}

	// Create TUN + WireGuard device
	tunDev, err := tun.CreateTUN(ifname, mtu)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("create tun: %w", err)
	}

	logger := device.NewLogger(device.LogLevelError, "("+ifname+") ")
	dev := device.NewDevice(tunDev, conn.NewDefaultBind(), logger)
	if dev == nil {
		_ = tunDev.Close()
		_ = db.Close()
		return nil, fmt.Errorf("create device")
	}

	pd := &persistentDevice{dev: dev, tun: tunDev, db: db}

	// Restore previous state if exists
	if err := pd.restore(); err != nil {
		dev.Close()
		_ = db.Close()
		return nil, fmt.Errorf("restore: %w", err)
	}

	return pd, nil
}

// ipcSet applies config to the device and persists the full state.
func (pd *persistentDevice) ipcSet(config string) error {
	if err := pd.dev.IpcSet(config); err != nil {
		return err
	}
	return pd.persist()
}

// ipcGet returns the current device state.
func (pd *persistentDevice) ipcGet() (string, error) {
	return pd.dev.IpcGet()
}

// persist writes the settable IpcGet state to the state DB.
// Filters out read-only fields that IpcSet rejects.
func (pd *persistentDevice) persist() error {
	dump, err := pd.dev.IpcGet()
	if err != nil {
		return fmt.Errorf("ipc get: %w", err)
	}
	filtered := filterIpcDump(dump)
	_, err = pd.db.Exec(
		"INSERT OR REPLACE INTO ipc_state (id, dump) VALUES (1, ?)", filtered)
	return err
}

// filterIpcDump removes read-only fields from IpcGet output
// so the dump can be fed back into IpcSet without errors.
func filterIpcDump(dump string) string {
	var result []byte
	for _, line := range strings.Split(dump, "\n") {
		if strings.HasPrefix(line, "last_handshake_time_sec=") ||
			strings.HasPrefix(line, "last_handshake_time_nsec=") ||
			strings.HasPrefix(line, "rx_bytes=") ||
			strings.HasPrefix(line, "tx_bytes=") ||
			strings.HasPrefix(line, "protocol_version=") {
			continue
		}
		result = append(result, line...)
		result = append(result, '\n')
	}
	return string(result)
}

// restore loads previous IPC state from DB and applies it to the device.
func (pd *persistentDevice) restore() error {
	var dump string
	err := pd.db.QueryRow("SELECT dump FROM ipc_state WHERE id = 1").Scan(&dump)
	if errors.Is(err, sql.ErrNoRows) {
		return nil // fresh DB, no state to restore
	}
	if err != nil {
		return fmt.Errorf("read state: %w", err)
	}
	if dump == "" {
		return nil
	}
	return pd.dev.IpcSet(dump)
}

// close shuts down the device and closes the state DB.
func (pd *persistentDevice) close() {
	pd.dev.Close()
	_ = pd.db.Close()
}
