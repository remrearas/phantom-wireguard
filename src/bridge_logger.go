package main

/*
#include "phantom_wg.h"
*/
import "C"
import (
	"unsafe"

	"golang.zx2c4.com/wireguard/device"
)

//export wgSetLogCallback
func wgSetLogCallback(callback C.WgLogCallback, context unsafe.Pointer) {
	// Callback is stored on the C/Python side.
	// This export exists so the FFI consumer can register a callback.
	// The actual log routing happens through device.NewLogger — logs
	// are written to the logger's Verbosef/Errorf which go to stderr.
	// For custom routing, the Python side captures stderr or uses
	// the callback mechanism at the Python layer.
}

//export wgNewLogger
func wgNewLogger(level C.int, prepend *C.char) C.int64_t {
	goLevel := int(level)
	goPrepend := C.GoString(prepend)
	logger := device.NewLogger(goLevel, goPrepend)
	return C.int64_t(loggerRegistry.Add(logger))
}

//export wgLoggerFree
func wgLoggerFree(handle C.int64_t) {
	loggerRegistry.Remove(int64(handle))
}

//export wgDiscardLogf
func wgDiscardLogf() {
	// No-op: device.DiscardLogf discards all log output.
}

func getLogger(handle int64) *device.Logger {
	obj, ok := loggerRegistry.Get(handle)
	if !ok {
		return device.NewLogger(device.LogLevelSilent, "")
	}
	return obj.(*device.Logger)
}