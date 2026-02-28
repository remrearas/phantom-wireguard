// Package multihop defines hop chain configuration and routing models
// for multi-hop WireGuard tunnels.
//
// In a multihop setup:
//   - Entry node: client connects to first WireGuard server
//   - Relay node(s): forward traffic between WireGuard interfaces
//   - Exit node: traffic exits to the internet
//
// Each hop has its own WireGuard device with a unique fwmark.
// Policy routing (managed by firewall_bridge) uses these marks
// to direct traffic through the correct chain.
//
// This package provides the data model — actual device creation
// is handled by bridge.State, routing by firewall_bridge via daemon-db.
package multihop

// Hop represents a single node in a multihop chain.
type Hop struct {
	Name       string `json:"name"`        // 'hop-entry', 'hop-relay-1', 'hop-exit'
	Role       string `json:"role"`        // 'entry', 'relay', 'exit'
	Interface  string `json:"interface"`   // 'wg-hop0', 'wg-hop1'
	ListenPort int    `json:"listen_port"`
	FWMark     int    `json:"fwmark"`      // SO_MARK for policy routing
	Endpoint   string `json:"endpoint"`    // remote endpoint for this hop
	PublicKey  string `json:"public_key"`  // remote peer public key
}

// Chain represents a complete multihop tunnel path.
type Chain struct {
	Name string `json:"name"` // 'multihop-us-exit'
	Hops []Hop  `json:"hops"`
}

// Entry returns the first hop (client-facing interface).
func (c *Chain) Entry() *Hop {
	if len(c.Hops) == 0 {
		return nil
	}
	return &c.Hops[0]
}

// Exit returns the last hop (internet-facing interface).
func (c *Chain) Exit() *Hop {
	if len(c.Hops) == 0 {
		return nil
	}
	return &c.Hops[len(c.Hops)-1]
}

// FWMarks returns all fwmarks in the chain for policy routing setup.
func (c *Chain) FWMarks() []int {
	marks := make([]int, 0, len(c.Hops))
	for _, h := range c.Hops {
		if h.FWMark != 0 {
			marks = append(marks, h.FWMark)
		}
	}
	return marks
}
