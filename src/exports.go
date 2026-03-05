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

/*
#include "compose_bridge.h"
#include <stdlib.h>
*/
import "C"

import (
	"fmt"
	"os"
	"unsafe"
)

// bridgeRegistry holds composeBridge instances keyed by handle.
var bridgeRegistry = NewRegistry()

// --- FFI exports ---

//export NewComposeBridge
func NewComposeBridge(configPath, projectName *C.char) C.int64_t {
	b, err := newComposeBridge(C.GoString(configPath), C.GoString(projectName))
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s NewComposeBridge error: %v\n", logPrefix, err)
		return C.int64_t(C.CB_ERR_DOCKER_INIT)
	}
	handle := bridgeRegistry.Store(b)
	return C.int64_t(handle)
}

func getBridge(handle C.int64_t) *composeBridge {
	v, ok := bridgeRegistry.Load(int64(handle))
	if !ok {
		return nil
	}
	return v.(*composeBridge)
}

//export GetProjectName
func GetProjectName(bridgeHandle C.int64_t) *C.char {
	b := getBridge(bridgeHandle)
	if b == nil {
		return nil
	}
	return C.CString(b.projectName)
}

//export ProjectUp
func ProjectUp(bridgeHandle C.int64_t) C.int32_t {
	b := getBridge(bridgeHandle)
	if b == nil {
		return C.int32_t(C.CB_ERR_NOT_FOUND)
	}

	if err := b.projectUp(); err != nil {
		b.setError(err)
		return C.int32_t(C.CB_ERR_PROJECT_UP)
	}
	return C.int32_t(C.CB_OK)
}

//export ProjectDown
func ProjectDown(bridgeHandle C.int64_t) C.int32_t {
	b := getBridge(bridgeHandle)
	if b == nil {
		return C.int32_t(C.CB_ERR_NOT_FOUND)
	}

	if err := b.projectDown(); err != nil {
		b.setError(err)
		return C.int32_t(C.CB_ERR_PROJECT_DOWN)
	}
	return C.int32_t(C.CB_OK)
}

//export ProjectPs
func ProjectPs(bridgeHandle C.int64_t) *C.char {
	b := getBridge(bridgeHandle)
	if b == nil {
		return nil
	}

	result, err := b.projectPs()
	if err != nil {
		b.setError(err)
		return nil
	}
	return C.CString(result)
}

//export ServiceExec
func ServiceExec(bridgeHandle C.int64_t, service, command, envJSON *C.char) *C.char {
	b := getBridge(bridgeHandle)
	if b == nil {
		return nil
	}

	result, err := b.serviceExec(
		C.GoString(service),
		C.GoString(command),
		C.GoString(envJSON),
	)
	if err != nil {
		b.setError(err)
		return nil
	}
	return C.CString(result)
}

//export ServiceLogs
func ServiceLogs(bridgeHandle C.int64_t, service *C.char, follow C.int32_t) *C.char {
	b := getBridge(bridgeHandle)
	if b == nil {
		return nil
	}

	result, err := b.serviceLogs(
		C.GoString(service),
		follow != 0,
	)
	if err != nil {
		b.setError(err)
		return nil
	}
	return C.CString(result)
}

//export GetLastError
func GetLastError(bridgeHandle C.int64_t) *C.char {
	b := getBridge(bridgeHandle)
	if b == nil {
		return C.CString("bridge not found")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	return C.CString(b.lastErr)
}

//export CloseBridge
func CloseBridge(bridgeHandle C.int64_t) C.int32_t {
	b := getBridge(bridgeHandle)
	if b == nil {
		return C.int32_t(C.CB_ERR_NOT_FOUND)
	}
	bridgeRegistry.Delete(int64(bridgeHandle))
	return C.int32_t(C.CB_OK)
}

//export FreeString
func FreeString(s *C.char) {
	if s != nil {
		C.free(unsafe.Pointer(s))
	}
}

//export BridgeVersion
func BridgeVersion() *C.char {
	return C.CString(BridgeVersionStr)
}
