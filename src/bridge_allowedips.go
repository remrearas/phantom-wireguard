package main

/*
#include "phantom_wg.h"
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

//export wgAllowedIpsInsert
func wgAllowedIpsInsert(deviceHandle C.int64_t, peerPubKeyHex *C.char, prefixStr *C.char) C.int32_t {
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

//export wgAllowedIpsReplaceForPeer
func wgAllowedIpsReplaceForPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char, prefixes *C.char) C.int32_t {
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

//export wgAllowedIpsRemoveByPeer
func wgAllowedIpsRemoveByPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char) C.int32_t {
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

// wgAllowedIpsGetForPeer returns allowed IPs for a peer via IpcGet parsing.
// Returns newline-separated CIDR prefixes. Caller must free with wgFreeString.
//
//export wgAllowedIpsGetForPeer
func wgAllowedIpsGetForPeer(deviceHandle C.int64_t, peerPubKeyHex *C.char) *C.char {
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
