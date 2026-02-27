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
	"golang.zx2c4.com/wireguard/device"
)

// ---------- Peer Lifecycle ----------

//export PeerStart
func PeerStart(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.Start()
	return C.WG_OK
}

//export PeerStop
func PeerStop(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.Stop()
	return C.WG_OK
}

//export PeerString
func PeerString(handle C.int64_t) *C.char {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return nil
	}
	return C.CString(peer.String())
}

//export PeerFree
func PeerFree(handle C.int64_t) {
	peerRegistry.Remove(int64(handle))
}

// ---------- Handshake Operations ----------

//export PeerSendHandshakeInitiation
func PeerSendHandshakeInitiation(handle C.int64_t, isRetry C.bool) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := peer.SendHandshakeInitiation(bool(isRetry)); e != nil {
		return C.WG_ERR_HANDSHAKE
	}
	return C.WG_OK
}

//export PeerSendHandshakeResponse
func PeerSendHandshakeResponse(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := peer.SendHandshakeResponse(); e != nil {
		return C.WG_ERR_HANDSHAKE
	}
	return C.WG_OK
}

//export PeerBeginSymmetricSession
func PeerBeginSymmetricSession(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := peer.BeginSymmetricSession(); e != nil {
		return C.WG_ERR_SESSION
	}
	return C.WG_OK
}

// ---------- Keepalive ----------

//export PeerSendKeepalive
func PeerSendKeepalive(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.SendKeepalive()
	return C.WG_OK
}

//export PeerSendStagedPackets
func PeerSendStagedPackets(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.SendStagedPackets()
	return C.WG_OK
}

// ---------- Keypair Management ----------

//export PeerExpireCurrentKeypairs
func PeerExpireCurrentKeypairs(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.ExpireCurrentKeypairs()
	return C.WG_OK
}

// ---------- Flush & Cleanup ----------

//export PeerFlushStagedPackets
func PeerFlushStagedPackets(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.FlushStagedPackets()
	return C.WG_OK
}

//export PeerZeroAndFlushAll
func PeerZeroAndFlushAll(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.ZeroAndFlushAll()
	return C.WG_OK
}

// ---------- Internal Notes ----------
// Keypairs.Current(), Handshake.Clear() are unexported in latest wireguard-go.
// Access these through IpcGet() which reports handshake/keypair state.
// RoutineSequentialReceiver/Sender are started by Peer.Start().
// SendBuffers, StagePackets, SetEndpointFromPacket, ReceivedWithKeypair,
// NewTimer are internal operations called by device goroutines.

// ---------- Helper ----------

func getPeer(handle int64) (*device.Peer, C.int32_t) {
	obj, ok := peerRegistry.Get(handle)
	if !ok {
		return nil, C.WG_ERR_NOT_FOUND
	}
	return obj.(*device.Peer), C.WG_OK
}