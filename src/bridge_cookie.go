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

// ---------- CookieChecker ----------

//export CookieCheckerCreate
func CookieCheckerCreate() C.int64_t {
	checker := new(device.CookieChecker)
	return C.int64_t(cookieCheckerRegistry.Add(checker))
}

//export CookieCheckerInit
func CookieCheckerInit(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	checker := obj.(*device.CookieChecker)

	var pk device.NoisePublicKey
	if err := pk.FromHex(C.GoString(pubKeyHex)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}

	checker.Init(pk)
	return C.WG_OK
}

//export CookieCheckerCheckMAC1
func CookieCheckerCheckMAC1(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.bool {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.bool(false)
	}
	checker := obj.(*device.CookieChecker)
	msgSlice := C.GoBytes(msg, msgLen)
	return C.bool(checker.CheckMAC1(msgSlice))
}

//export CookieCheckerCheckMAC2
func CookieCheckerCheckMAC2(handle C.int64_t, msg unsafe.Pointer, msgLen C.int, src unsafe.Pointer, srcLen C.int) C.bool {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.bool(false)
	}
	checker := obj.(*device.CookieChecker)
	msgSlice := C.GoBytes(msg, msgLen)
	srcSlice := C.GoBytes(src, srcLen)
	return C.bool(checker.CheckMAC2(msgSlice, srcSlice))
}

//export CookieCheckerCreateReply
func CookieCheckerCreateReply(
	handle C.int64_t,
	msg unsafe.Pointer, msgLen C.int,
	recv C.uint32_t,
	src unsafe.Pointer, srcLen C.int,
	out unsafe.Pointer, outLen *C.int,
) C.int32_t {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	checker := obj.(*device.CookieChecker)
	msgSlice := C.GoBytes(msg, msgLen)
	srcSlice := C.GoBytes(src, srcLen)

	reply, err := checker.CreateReply(msgSlice, uint32(recv), srcSlice)
	if err != nil {
		return C.WG_ERR_COOKIE
	}

	// Serialize reply to bytes
	replySize := unsafe.Sizeof(*reply)
	replyBytes := C.GoBytes(unsafe.Pointer(reply), C.int(replySize))
	C.memcpy(out, unsafe.Pointer(&replyBytes[0]), C.size_t(replySize))
	*outLen = C.int(replySize)

	return C.WG_OK
}

//export CookieCheckerFree
func CookieCheckerFree(handle C.int64_t) {
	cookieCheckerRegistry.Remove(int64(handle))
}

// ---------- CookieGenerator ----------

//export CookieGeneratorCreate
func CookieGeneratorCreate() C.int64_t {
	gen := new(device.CookieGenerator)
	return C.int64_t(cookieGenRegistry.Add(gen))
}

//export CookieGeneratorInit
func CookieGeneratorInit(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
	obj, ok := cookieGenRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	gen := obj.(*device.CookieGenerator)

	var pk device.NoisePublicKey
	if err := pk.FromHex(C.GoString(pubKeyHex)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}

	gen.Init(pk)
	return C.WG_OK
}

//export CookieGeneratorAddMacs
func CookieGeneratorAddMacs(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.int32_t {
	obj, ok := cookieGenRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	gen := obj.(*device.CookieGenerator)
	msgSlice := C.GoBytes(msg, msgLen)
	gen.AddMacs(msgSlice)

	// Write modified message back
	C.memcpy(msg, unsafe.Pointer(&msgSlice[0]), C.size_t(msgLen))
	return C.WG_OK
}

//export CookieGeneratorConsumeReply
func CookieGeneratorConsumeReply(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.bool {
	obj, ok := cookieGenRegistry.Get(int64(handle))
	if !ok {
		return C.bool(false)
	}
	gen := obj.(*device.CookieGenerator)

	// Parse as MessageCookieReply
	if int(msgLen) < int(unsafe.Sizeof(device.MessageCookieReply{})) {
		return C.bool(false)
	}
	reply := (*device.MessageCookieReply)(msg)
	return C.bool(gen.ConsumeReply(reply))
}

//export CookieGeneratorFree
func CookieGeneratorFree(handle C.int64_t) {
	cookieGenRegistry.Remove(int64(handle))
}