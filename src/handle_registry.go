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

package main

import (
	"sync"
)

// HandleRegistry provides thread-safe storage for Go objects
// referenced by integer handles across the FFI boundary.
// Pattern mirrors wstunnel's OpaquePointer approach but supports
// multi-instance (one handle per device/peer/object).
type HandleRegistry struct {
	mu      sync.RWMutex
	objects map[int64]interface{}
	seq     int64
}

func NewHandleRegistry() *HandleRegistry {
	return &HandleRegistry{
		objects: make(map[int64]interface{}),
	}
}

func (r *HandleRegistry) Add(obj interface{}) int64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.seq++
	r.objects[r.seq] = obj
	return r.seq
}

func (r *HandleRegistry) Get(handle int64) (interface{}, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	obj, ok := r.objects[handle]
	return obj, ok
}

func (r *HandleRegistry) Remove(handle int64) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.objects[handle]; ok {
		delete(r.objects, handle)
		return true
	}
	return false
}

func (r *HandleRegistry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.objects)
}

// Global registries — one per type for type safety
var (
	deviceRegistry        = NewHandleRegistry()
	peerRegistry          = NewHandleRegistry()
	loggerRegistry        = NewHandleRegistry()
	cookieCheckerRegistry = NewHandleRegistry()
	cookieGenRegistry     = NewHandleRegistry()
)