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

// Error code constants mirrored from C header for Go usage.
const (
	errOK             = C.WG_OK
	errDBOpen         = C.WG_ERR_DB_OPEN
	errDBQuery        = C.WG_ERR_DB_QUERY
	errDBWrite        = C.WG_ERR_DB_WRITE
	errIPExhausted    = C.WG_ERR_IP_EXHAUSTED
	errNotInitialized = C.WG_ERR_NOT_INITIALIZED
	errStatsRunning   = C.WG_ERR_STATS_RUNNING
	errInternal       = C.WG_ERR_INTERNAL
)

// Ensure all error codes are referenced (used in future export functions).
var _ = [...]C.int32_t{errDBQuery, errIPExhausted}
