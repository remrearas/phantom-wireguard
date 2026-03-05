/*
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 *
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 * Licensed under AGPL-3.0 - see LICENSE file for details
 */

package main

import "sync"

// Registry is a thread-safe map from int64 handles to arbitrary values.
type Registry struct {
	mu      sync.RWMutex
	entries map[int64]interface{}
	nextID  int64
}

// NewRegistry creates a new empty registry.
func NewRegistry() *Registry {
	return &Registry{
		entries: make(map[int64]interface{}),
		nextID:  1,
	}
}

// Store inserts a value and returns the assigned handle.
func (r *Registry) Store(v interface{}) int64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	id := r.nextID
	r.nextID++
	r.entries[id] = v
	return id
}

// Load retrieves the value for a handle, or nil if not found.
func (r *Registry) Load(id int64) (interface{}, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	v, ok := r.entries[id]
	return v, ok
}

// Delete removes a handle from the registry.
func (r *Registry) Delete(id int64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.entries, id)
}
