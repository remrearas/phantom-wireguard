package main

/*
#include "phantom_wg.h"
*/
import "C"
import (
	"unsafe"

	"golang.zx2c4.com/wireguard/device"
)

// ---------- CookieChecker ----------

//export wgCookieCheckerCreate
func wgCookieCheckerCreate() C.int64_t {
	checker := new(device.CookieChecker)
	return C.int64_t(cookieCheckerRegistry.Add(checker))
}

//export wgCookieCheckerInit
func wgCookieCheckerInit(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
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

//export wgCookieCheckerCheckMac1
func wgCookieCheckerCheckMac1(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.bool {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.bool(false)
	}
	checker := obj.(*device.CookieChecker)
	msgSlice := C.GoBytes(msg, msgLen)
	return C.bool(checker.CheckMAC1(msgSlice))
}

//export wgCookieCheckerCheckMac2
func wgCookieCheckerCheckMac2(handle C.int64_t, msg unsafe.Pointer, msgLen C.int, src unsafe.Pointer, srcLen C.int) C.bool {
	obj, ok := cookieCheckerRegistry.Get(int64(handle))
	if !ok {
		return C.bool(false)
	}
	checker := obj.(*device.CookieChecker)
	msgSlice := C.GoBytes(msg, msgLen)
	srcSlice := C.GoBytes(src, srcLen)
	return C.bool(checker.CheckMAC2(msgSlice, srcSlice))
}

//export wgCookieCheckerCreateReply
func wgCookieCheckerCreateReply(
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

//export wgCookieCheckerFree
func wgCookieCheckerFree(handle C.int64_t) {
	cookieCheckerRegistry.Remove(int64(handle))
}

// ---------- CookieGenerator ----------

//export wgCookieGeneratorCreate
func wgCookieGeneratorCreate() C.int64_t {
	gen := new(device.CookieGenerator)
	return C.int64_t(cookieGenRegistry.Add(gen))
}

//export wgCookieGeneratorInit
func wgCookieGeneratorInit(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
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

//export wgCookieGeneratorAddMacs
func wgCookieGeneratorAddMacs(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.int32_t {
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

//export wgCookieGeneratorConsumeReply
func wgCookieGeneratorConsumeReply(handle C.int64_t, msg unsafe.Pointer, msgLen C.int) C.bool {
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

//export wgCookieGeneratorFree
func wgCookieGeneratorFree(handle C.int64_t) {
	cookieGenRegistry.Remove(int64(handle))
}