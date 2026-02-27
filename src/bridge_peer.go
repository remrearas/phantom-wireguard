package main

/*
#include "phantom_wg.h"
*/
import "C"
import (
	"golang.zx2c4.com/wireguard/device"
)

// ---------- Peer Lifecycle ----------

//export wgPeerStart
func wgPeerStart(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.Start()
	return C.WG_OK
}

//export wgPeerStop
func wgPeerStop(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.Stop()
	return C.WG_OK
}

//export wgPeerString
func wgPeerString(handle C.int64_t) *C.char {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return nil
	}
	return C.CString(peer.String())
}

//export wgPeerFree
func wgPeerFree(handle C.int64_t) {
	peerRegistry.Remove(int64(handle))
}

// ---------- Handshake Operations ----------

//export wgPeerSendHandshakeInitiation
func wgPeerSendHandshakeInitiation(handle C.int64_t, isRetry C.bool) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := peer.SendHandshakeInitiation(bool(isRetry)); e != nil {
		return C.WG_ERR_HANDSHAKE
	}
	return C.WG_OK
}

//export wgPeerSendHandshakeResponse
func wgPeerSendHandshakeResponse(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := peer.SendHandshakeResponse(); e != nil {
		return C.WG_ERR_HANDSHAKE
	}
	return C.WG_OK
}

//export wgPeerBeginSymmetricSession
func wgPeerBeginSymmetricSession(handle C.int64_t) C.int32_t {
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

//export wgPeerSendKeepalive
func wgPeerSendKeepalive(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.SendKeepalive()
	return C.WG_OK
}

//export wgPeerSendStagedPackets
func wgPeerSendStagedPackets(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.SendStagedPackets()
	return C.WG_OK
}

// ---------- Keypair Management ----------

//export wgPeerExpireCurrentKeypairs
func wgPeerExpireCurrentKeypairs(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.ExpireCurrentKeypairs()
	return C.WG_OK
}

// ---------- Flush & Cleanup ----------

//export wgPeerFlushStagedPackets
func wgPeerFlushStagedPackets(handle C.int64_t) C.int32_t {
	peer, err := getPeer(int64(handle))
	if err != C.WG_OK {
		return err
	}
	peer.FlushStagedPackets()
	return C.WG_OK
}

//export wgPeerZeroAndFlushAll
func wgPeerZeroAndFlushAll(handle C.int64_t) C.int32_t {
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