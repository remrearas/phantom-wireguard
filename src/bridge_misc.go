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

/*
#include "wireguard_go_bridge.h"
*/
import "C"

// ---------- IndexTable ----------
// IndexTable is managed internally by Device. Its Init(), Delete(),
// Lookup(), NewIndexForHandshake(), and SwapIndexForKeypair() methods
// are called by the device's handshake processing goroutines.
// Direct FFI access is not needed — IpcSet/IpcGet handles all peer indexing.

// ---------- Keypairs ----------
// Keypairs and Keypair are internal crypto session state.
// Keypairs.Current() is exposed via PeerHasCurrentKeypair.
// DeleteKeypair is called internally during key rotation.

// ---------- WaitPool ----------
// WaitPool is an internal memory pool (sync.Pool with max capacity).
// NewWaitPool, Get, and Put are used by device goroutines for
// zero-allocation packet processing. Exposed via DevicePopulatePools.

// ---------- Queue Types ----------
// QueueInboundElement, QueueInboundElementsContainer,
// QueueOutboundElement, QueueOutboundElementsContainer,
// QueueHandshakeElement are internal packet queue types.
// They flow through encryption/decryption goroutines automatically.

// ---------- Message Types ----------
// MessageInitiation, MessageResponse, MessageTransport, MessageCookieReply
// are WireGuard protocol message structs. They are handled by device
// goroutines. MessageCookieReply is exposed via Cookie bridge operations.

// ---------- NoiseNonce ----------
// NoiseNonce (uint64) is the packet counter for replay protection.
// Managed internally by the device during encryption/decryption.

// ---------- IPCError ----------

//export IpcErrorCode
func IpcErrorCode(errCode C.int64_t) C.int64_t {
	// IPCError wraps an error with an error code.
	// When IpcSet fails, DeviceIpcSetOperation returns the error code.
	// This function documents the pattern — the error code is already
	// returned directly from DeviceIpcSetOperation.
	return errCode
}

// ---------- Version & Info ----------

//export BridgeVersion
func BridgeVersion() *C.char {
	return C.CString("1.0.0")
}

//export WireguardGoVersion
func WireguardGoVersion() *C.char {
	return C.CString("0.0.20230223")
}

// ---------- Handle Count (diagnostics) ----------

//export ActiveDeviceCount
func ActiveDeviceCount() C.int {
	return C.int(deviceRegistry.Count())
}

//export ActivePeerCount
func ActivePeerCount() C.int {
	return C.int(peerRegistry.Count())
}