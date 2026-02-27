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
	"unsafe"

	"golang.zx2c4.com/wireguard/device"
)

//export SetLogCallback
func SetLogCallback(callback C.WgLogCallback, context unsafe.Pointer) { //nolint:revive
	// Placeholder: callback registration is handled at the Python layer.
	// Logs are written to stderr via device.NewLogger's Verbosef/Errorf.
	_ = callback
	_ = context
}

//export NewLogger
func NewLogger(level C.int, prepend *C.char) C.int64_t {
	goLevel := int(level)
	goPrepend := C.GoString(prepend)
	logger := device.NewLogger(goLevel, goPrepend)
	return C.int64_t(loggerRegistry.Add(logger))
}

//export LoggerFree
func LoggerFree(handle C.int64_t) {
	loggerRegistry.Remove(int64(handle))
}

//export DiscardLogf
func DiscardLogf() {
	// No-op: device.DiscardLogf discards all log output.
}

func getLogger(handle int64) *device.Logger {
	obj, ok := loggerRegistry.Get(handle)
	if !ok {
		return device.NewLogger(device.LogLevelSilent, "")
	}
	return obj.(*device.Logger)
}