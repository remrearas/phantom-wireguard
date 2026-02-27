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
import (
	"strings"
)

// AllowedIPs operations use IpcSet/IpcGet since the internal allowedips
// table is unexported in wireguard-go. This is the intended public API.
//
// UAPI protocol format for allowed_ip:
//   set=1\npublic_key=<hex>\nreplace_allowed_ips=true\nallowed_ip=<prefix>\n\n
//
// These helpers build UAPI strings for AllowedIPs manipulation.

//export AllowedIpsInsert
func AllowedIpsInsert(deviceHandle C.int64_t, peerPubKeyHex *C.char, prefixStr *C.char) C.int32_t {
	dev, err := getDevice(int64(deviceHandle))
	if err != C.WG_OK {
		return err
	}

	config := "public_key=" + C.GoString(peerPubKeyHex) + "\nallowed_ip=" + C.GoString(prefixStr) + "\n"

	if e := dev.IpcSet(config); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export AllowedIpsReplaceForPeer
func AllowedIpsReplaceForPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char, prefixes *C.char) C.int32_t {
	dev, err := getDevice(int64(deviceHandle))
	if err != C.WG_OK {
		return err
	}

	config := "public_key=" + C.GoString(peerPubKeyHex) + "\nreplace_allowed_ips=true\n"

	prefixList := C.GoString(prefixes)
	for _, prefix := range strings.Split(prefixList, "\n") {
		prefix = strings.TrimSpace(prefix)
		if prefix != "" {
			config += "allowed_ip=" + prefix + "\n"
		}
	}

	if e := dev.IpcSet(config); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export AllowedIpsRemoveByPeer
func AllowedIpsRemoveByPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char) C.int32_t {
	dev, err := getDevice(int64(deviceHandle))
	if err != C.WG_OK {
		return err
	}

	config := "public_key=" + C.GoString(peerPubKeyHex) + "\nreplace_allowed_ips=true\n"

	if e := dev.IpcSet(config); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

// AllowedIpsGetForPeer returns allowed IPs for a peer via IpcGet parsing.
// Returns newline-separated CIDR prefixes. Caller must free with FreeString.
//
//export AllowedIpsGetForPeer
func AllowedIpsGetForPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char) *C.char {
	dev, err := getDevice(int64(deviceHandle))
	if err != C.WG_OK {
		return nil
	}

	config, e := dev.IpcGet()
	if e != nil {
		return nil
	}

	targetKey := C.GoString(peerPubKeyHex)
	var result []string
	inTargetPeer := false

	for _, line := range strings.Split(config, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "public_key=") {
			key := strings.TrimPrefix(line, "public_key=")
			inTargetPeer = key == targetKey
		} else if inTargetPeer && strings.HasPrefix(line, "allowed_ip=") {
			prefix := strings.TrimPrefix(line, "allowed_ip=")
			result = append(result, prefix)
		}
	}

	return C.CString(strings.Join(result, "\n"))
}
