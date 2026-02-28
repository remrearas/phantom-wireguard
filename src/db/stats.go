package db

import (
	"strconv"
	"strings"
	"sync"
	"time"
)

// StatsSyncer periodically reads WireGuard runtime state via IpcGet
// and writes it to bridge-db.
type StatsSyncer struct {
	db       *BridgeDB
	ipcGetFn func() (string, error) // injected: calls device.IpcGet()
	interval time.Duration
	stop     chan struct{}
	wg       sync.WaitGroup
}

// NewStatsSyncer creates a stats syncer.
// ipcGetFn should return the UAPI IpcGet output string.
func NewStatsSyncer(db *BridgeDB, ipcGetFn func() (string, error), intervalSec int) *StatsSyncer {
	return &StatsSyncer{
		db:       db,
		ipcGetFn: ipcGetFn,
		interval: time.Duration(intervalSec) * time.Second,
		stop:     make(chan struct{}),
	}
}

// Start begins the background sync goroutine.
func (s *StatsSyncer) Start() {
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		ticker := time.NewTicker(s.interval)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				s.syncOnce()
			case <-s.stop:
				return
			}
		}
	}()
}

// Stop halts the background sync goroutine and waits for it to finish.
func (s *StatsSyncer) Stop() {
	close(s.stop)
	s.wg.Wait()
}

// peerStats holds parsed per-peer stats from IpcGet output.
type peerStats struct {
	publicKey     string
	endpoint      string
	lastHandshake *int64
	rxBytes       int64
	txBytes       int64
}

func (s *StatsSyncer) syncOnce() {
	output, err := s.ipcGetFn()
	if err != nil {
		return
	}

	peers := parseIpcGetPeers(output)
	for _, p := range peers {
		_ = s.db.UpdateStats(p.publicKey, p.endpoint, p.lastHandshake, p.rxBytes, p.txBytes)
	}
}

// parseIpcGetPeers parses the UAPI IpcGet output into per-peer stats.
// Format:
//
//	public_key=<hex>
//	endpoint=<ip>:<port>
//	last_handshake_time_sec=<unix>
//	rx_bytes=<int>
//	tx_bytes=<int>
func parseIpcGetPeers(output string) []peerStats {
	var result []peerStats
	var current *peerStats

	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key, val := parts[0], parts[1]

		switch key {
		case "public_key":
			if current != nil {
				result = append(result, *current)
			}
			current = &peerStats{publicKey: val}
		case "endpoint":
			if current != nil {
				current.endpoint = val
			}
		case "last_handshake_time_sec":
			if current != nil {
				if v, err := strconv.ParseInt(val, 10, 64); err == nil && v > 0 {
					current.lastHandshake = &v
				}
			}
		case "rx_bytes":
			if current != nil {
				current.rxBytes, _ = strconv.ParseInt(val, 10, 64)
			}
		case "tx_bytes":
			if current != nil {
				current.txBytes, _ = strconv.ParseInt(val, 10, 64)
			}
		}
	}
	if current != nil {
		result = append(result, *current)
	}
	return result
}
