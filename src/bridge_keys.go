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
	"crypto/rand"
	"encoding/hex"
	"unsafe"

	"golang.org/x/crypto/curve25519"
	"golang.zx2c4.com/wireguard/device"
)

// ---------- Key Generation ----------
// Replaces: wg genkey, wg pubkey, wg genpsk subprocess calls

//export GeneratePrivateKey
func GeneratePrivateKey() *C.char {
	var key [32]byte
	if _, err := rand.Read(key[:]); err != nil {
		return nil
	}
	// Curve25519 clamping
	key[0] &= 248
	key[31] &= 127
	key[31] |= 64
	return C.CString(hex.EncodeToString(key[:]))
}

//export DerivePublicKey
func DerivePublicKey(privateKeyHex *C.char) *C.char {
	privHex := C.GoString(privateKeyHex)
	privBytes, err := hex.DecodeString(privHex)
	if err != nil || len(privBytes) != 32 {
		return nil
	}
	var privKey [32]byte
	copy(privKey[:], privBytes)

	pubBytes, err := curve25519.X25519(privKey[:], curve25519.Basepoint)
	if err != nil {
		return nil
	}
	return C.CString(hex.EncodeToString(pubBytes))
}

//export GeneratePresharedKey
func GeneratePresharedKey() *C.char {
	var key [32]byte
	if _, err := rand.Read(key[:]); err != nil {
		return nil
	}
	return C.CString(hex.EncodeToString(key[:]))
}

// ---------- NoisePrivateKey Operations ----------

//export PrivateKeyFromHex
func PrivateKeyFromHex(hexStr *C.char, out unsafe.Pointer) C.int32_t {
	var key device.NoisePrivateKey
	if err := key.FromHex(C.GoString(hexStr)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}
	C.memcpy(out, unsafe.Pointer(&key[0]), 32)
	return C.WG_OK
}

//export PrivateKeyFromMaybeZeroHex
func PrivateKeyFromMaybeZeroHex(hexStr *C.char, out unsafe.Pointer) C.int32_t {
	var key device.NoisePrivateKey
	if err := key.FromMaybeZeroHex(C.GoString(hexStr)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}
	C.memcpy(out, unsafe.Pointer(&key[0]), 32)
	return C.WG_OK
}

//export PrivateKeyIsZero
func PrivateKeyIsZero(keyHex *C.char) C.bool {
	var key device.NoisePrivateKey
	if err := key.FromMaybeZeroHex(C.GoString(keyHex)); err != nil {
		return C.bool(true)
	}
	return C.bool(key.IsZero())
}

//export PrivateKeyEquals
func PrivateKeyEquals(keyAHex *C.char, keyBHex *C.char) C.bool {
	var a, b device.NoisePrivateKey
	if err := a.FromHex(C.GoString(keyAHex)); err != nil {
		return C.bool(false)
	}
	if err := b.FromHex(C.GoString(keyBHex)); err != nil {
		return C.bool(false)
	}
	return C.bool(a.Equals(b))
}

// ---------- NoisePublicKey Operations ----------

//export PublicKeyFromHex
func PublicKeyFromHex(hexStr *C.char, out unsafe.Pointer) C.int32_t {
	var key device.NoisePublicKey
	if err := key.FromHex(C.GoString(hexStr)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}
	C.memcpy(out, unsafe.Pointer(&key[0]), 32)
	return C.WG_OK
}

//export PublicKeyIsZero
func PublicKeyIsZero(keyHex *C.char) C.bool {
	var key device.NoisePublicKey
	if err := key.FromHex(C.GoString(keyHex)); err != nil {
		return C.bool(true)
	}
	return C.bool(key.IsZero())
}

//export PublicKeyEquals
func PublicKeyEquals(keyAHex *C.char, keyBHex *C.char) C.bool {
	var a, b device.NoisePublicKey
	if err := a.FromHex(C.GoString(keyAHex)); err != nil {
		return C.bool(false)
	}
	if err := b.FromHex(C.GoString(keyBHex)); err != nil {
		return C.bool(false)
	}
	return C.bool(a.Equals(b))
}

// ---------- NoisePresharedKey Operations ----------

//export PresharedKeyFromHex
func PresharedKeyFromHex(hexStr *C.char, out unsafe.Pointer) C.int32_t {
	var key device.NoisePresharedKey
	if err := key.FromHex(C.GoString(hexStr)); err != nil {
		return C.WG_ERR_KEY_PARSE
	}
	C.memcpy(out, unsafe.Pointer(&key[0]), 32)
	return C.WG_OK
}