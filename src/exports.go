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
// exports.go — FFI exports: PersistentDevice + Key generation + utility.
// This is the entire public API surface. No high-level logic.

package main

/*
#include "wireguard_go_bridge.h"
*/
import "C"
import (
	"unsafe"

	"wireguard-go-bridge/core"
)

// ============================================================================
// PersistentDevice — WireGuard device with automatic IPC state persistence
// ============================================================================

//export NewPersistentDevice
func NewPersistentDevice(ifname *C.char, mtu C.int, dbPath *C.char) C.int64_t {
	pd, err := newPersistentDevice(C.GoString(ifname), int(mtu), C.GoString(dbPath))
	if err != nil {
		return C.int64_t(C.WG_ERR_DEVICE_CREATE)
	}
	return C.int64_t(deviceRegistry.Add(pd))
}

//export DeviceIpcSet
func DeviceIpcSet(handle C.int64_t, config *C.char) C.int32_t {
	pd, errC := getPersistentDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if err := pd.ipcSet(C.GoString(config)); err != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export DeviceIpcGet
func DeviceIpcGet(handle C.int64_t) *C.char {
	pd, errC := getPersistentDevice(int64(handle))
	if errC != C.WG_OK {
		return nil
	}
	dump, err := pd.ipcGet()
	if err != nil {
		return nil
	}
	return C.CString(dump)
}

//export DeviceUp
func DeviceUp(handle C.int64_t) C.int32_t {
	pd, errC := getPersistentDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if err := pd.dev.Up(); err != nil {
		return C.WG_ERR_DEVICE_UP
	}
	return C.WG_OK
}

//export DeviceDown
func DeviceDown(handle C.int64_t) C.int32_t {
	pd, errC := getPersistentDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if err := pd.dev.Down(); err != nil {
		return C.WG_ERR_DEVICE_DOWN
	}
	return C.WG_OK
}

//export DeviceClose
func DeviceClose(handle C.int64_t) C.int32_t {
	obj, ok := deviceRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	pd := obj.(*persistentDevice)
	pd.close()
	deviceRegistry.Remove(int64(handle))
	return C.WG_OK
}

// ============================================================================
// Key Generation
// ============================================================================

//export GeneratePrivateKey
func GeneratePrivateKey() *C.char {
	key, err := core.GeneratePrivateKey()
	if err != nil {
		return nil
	}
	return C.CString(key)
}

//export DerivePublicKey
func DerivePublicKey(privateKeyHex *C.char) *C.char {
	pub, err := core.DerivePublicKey(C.GoString(privateKeyHex))
	if err != nil {
		return nil
	}
	return C.CString(pub)
}

//export GeneratePresharedKey
func GeneratePresharedKey() *C.char {
	key, err := core.GeneratePresharedKey()
	if err != nil {
		return nil
	}
	return C.CString(key)
}

//export HexToBase64
func HexToBase64(hexStr *C.char) *C.char {
	b64, err := core.HexToBase64(C.GoString(hexStr))
	if err != nil {
		return nil
	}
	return C.CString(b64)
}

// ============================================================================
// Utility
// ============================================================================

//export BridgeVersion
func BridgeVersion() *C.char {
	return C.CString(BridgeVersionStr)
}

//export FreeString
func FreeString(s *C.char) {
	C.free(unsafe.Pointer(s))
}

// ============================================================================
// Internal
// ============================================================================

func getPersistentDevice(handle int64) (*persistentDevice, C.int32_t) {
	obj, ok := deviceRegistry.Get(handle)
	if !ok {
		return nil, C.WG_ERR_NOT_FOUND
	}
	return obj.(*persistentDevice), C.WG_OK
}
