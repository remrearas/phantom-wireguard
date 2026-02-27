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

	"golang.org/x/crypto/blake2s"
	"golang.zx2c4.com/wireguard/device"
)

// ---------- HMAC Functions ----------

//export HMAC1
func HMAC1(
	key unsafe.Pointer, keyLen C.int,
	in0 unsafe.Pointer, in0Len C.int,
	out unsafe.Pointer,
) {
	keySlice := C.GoBytes(key, keyLen)
	in0Slice := C.GoBytes(in0, in0Len)

	var sum [blake2s.Size]byte
	device.HMAC1(&sum, keySlice, in0Slice)
	C.memcpy(out, unsafe.Pointer(&sum[0]), C.size_t(blake2s.Size))
}

//export HMAC2
func HMAC2(
	key unsafe.Pointer, keyLen C.int,
	in0 unsafe.Pointer, in0Len C.int,
	in1 unsafe.Pointer, in1Len C.int,
	out unsafe.Pointer,
) {
	keySlice := C.GoBytes(key, keyLen)
	in0Slice := C.GoBytes(in0, in0Len)
	in1Slice := C.GoBytes(in1, in1Len)

	var sum [blake2s.Size]byte
	device.HMAC2(&sum, keySlice, in0Slice, in1Slice)
	C.memcpy(out, unsafe.Pointer(&sum[0]), C.size_t(blake2s.Size))
}

// ---------- KDF Functions ----------

//export KDF1
func KDF1(
	key unsafe.Pointer, keyLen C.int,
	input unsafe.Pointer, inputLen C.int,
	t0 unsafe.Pointer,
) {
	keySlice := C.GoBytes(key, keyLen)
	inputSlice := C.GoBytes(input, inputLen)

	var out0 [blake2s.Size]byte
	device.KDF1(&out0, keySlice, inputSlice)
	C.memcpy(t0, unsafe.Pointer(&out0[0]), C.size_t(blake2s.Size))
}

//export KDF2
func KDF2(
	key unsafe.Pointer, keyLen C.int,
	input unsafe.Pointer, inputLen C.int,
	t0 unsafe.Pointer,
	t1 unsafe.Pointer,
) {
	keySlice := C.GoBytes(key, keyLen)
	inputSlice := C.GoBytes(input, inputLen)

	var out0, out1 [blake2s.Size]byte
	device.KDF2(&out0, &out1, keySlice, inputSlice)
	C.memcpy(t0, unsafe.Pointer(&out0[0]), C.size_t(blake2s.Size))
	C.memcpy(t1, unsafe.Pointer(&out1[0]), C.size_t(blake2s.Size))
}

//export KDF3
func KDF3(
	key unsafe.Pointer, keyLen C.int,
	input unsafe.Pointer, inputLen C.int,
	t0 unsafe.Pointer,
	t1 unsafe.Pointer,
	t2 unsafe.Pointer,
) {
	keySlice := C.GoBytes(key, keyLen)
	inputSlice := C.GoBytes(input, inputLen)

	var out0, out1, out2 [blake2s.Size]byte
	device.KDF3(&out0, &out1, &out2, keySlice, inputSlice)
	C.memcpy(t0, unsafe.Pointer(&out0[0]), C.size_t(blake2s.Size))
	C.memcpy(t1, unsafe.Pointer(&out1[0]), C.size_t(blake2s.Size))
	C.memcpy(t2, unsafe.Pointer(&out2[0]), C.size_t(blake2s.Size))
}

// ---------- Constants ----------

//export Blake2sSize
func Blake2sSize() C.int {
	return C.int(blake2s.Size)
}
