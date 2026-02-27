package main

/*
#include "phantom_wg.h"
*/
import "C"
import (
	"errors"
	"unsafe"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/tun"
)

// deviceEntry stores a device along with its associated TUN for cleanup
type deviceEntry struct {
	device *device.Device
	tun    tun.Device
}

// ---------- Device Lifecycle ----------

//export wgDeviceCreate
func wgDeviceCreate(ifname *C.char, mtu C.int, loggerHandle C.int64_t) C.int64_t {
	name := C.GoString(ifname)
	goMtu := int(mtu)

	tunDev, err := tun.CreateTUN(name, goMtu)
	if err != nil {
		return C.int64_t(C.WG_ERR_TUN_CREATE)
	}

	logger := getLogger(int64(loggerHandle))
	bind := conn.NewDefaultBind()

	dev := device.NewDevice(tunDev, bind, logger)
	if dev == nil {
		_ = tunDev.Close()
		return C.int64_t(C.WG_ERR_DEVICE_CREATE)
	}

	entry := &deviceEntry{device: dev, tun: tunDev}
	return C.int64_t(deviceRegistry.Add(entry))
}

//export wgDeviceClose
func wgDeviceClose(handle C.int64_t) C.int32_t {
	obj, ok := deviceRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	entry := obj.(*deviceEntry)
	entry.device.Close()
	deviceRegistry.Remove(int64(handle))
	return C.WG_OK
}

//export wgDeviceUp
func wgDeviceUp(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := dev.Up(); e != nil {
		return C.WG_ERR_DEVICE_UP
	}
	return C.WG_OK
}

//export wgDeviceDown
func wgDeviceDown(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := dev.Down(); e != nil {
		return C.WG_ERR_DEVICE_DOWN
	}
	return C.WG_OK
}

// ---------- IPC (UAPI Protocol) ----------

//export wgDeviceIpcSet
func wgDeviceIpcSet(handle C.int64_t, config *C.char) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	goConfig := C.GoString(config)
	if e := dev.IpcSet(goConfig); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export wgDeviceIpcGet
func wgDeviceIpcGet(handle C.int64_t) *C.char {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return nil
	}
	config, e := dev.IpcGet()
	if e != nil {
		return nil
	}
	return C.CString(config)
}

//export wgDeviceIpcSetOperation
func wgDeviceIpcSetOperation(handle C.int64_t, config *C.char) C.int64_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return C.int64_t(err)
	}
	goConfig := C.GoString(config)
	if e := dev.IpcSet(goConfig); e != nil {
		var ipcErr *device.IPCError
		if errors.As(e, &ipcErr) {
			return C.int64_t(ipcErr.ErrorCode())
		}
		return C.int64_t(C.WG_ERR_IPC_SET)
	}
	return C.int64_t(C.WG_OK)
}

// ---------- Bind Operations ----------

//export wgDeviceBindClose
func wgDeviceBindClose(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := dev.BindClose(); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export wgDeviceBindUpdate
func wgDeviceBindUpdate(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := dev.BindUpdate(); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export wgDeviceBindSetMark
func wgDeviceBindSetMark(handle C.int64_t, mark C.uint32_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	if e := dev.BindSetMark(uint32(mark)); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export wgDeviceBind
func wgDeviceBind(handle C.int64_t) C.int64_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return 0
	}
	_ = dev.Bind()
	// Bind returns conn.Bind interface — not meaningful to expose directly.
	// Use bind_close/bind_update/bind_set_mark for control.
	return 1
}

// ---------- Device State & Info ----------

//export wgDeviceBatchSize
func wgDeviceBatchSize(handle C.int64_t) C.int {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return 0
	}
	return C.int(dev.BatchSize())
}

//export wgDeviceIsUnderLoad
func wgDeviceIsUnderLoad(handle C.int64_t) C.bool {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return C.bool(false)
	}
	return C.bool(dev.IsUnderLoad())
}

//export wgDeviceWait
func wgDeviceWait(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	<-dev.Wait()
	return C.WG_OK
}

// ---------- Key Management on Device ----------

//export wgDeviceSetPrivateKey
func wgDeviceSetPrivateKey(handle C.int64_t, hexKey *C.char) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	var key device.NoisePrivateKey
	if e := key.FromHex(C.GoString(hexKey)); e != nil {
		return C.WG_ERR_KEY_PARSE
	}
	if e := dev.SetPrivateKey(key); e != nil {
		return C.WG_ERR_INTERNAL
	}
	return C.WG_OK
}

// ---------- Peer Management via Device ----------

//export wgDeviceNewPeer
func wgDeviceNewPeer(handle C.int64_t, pubKeyHex *C.char) C.int64_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return C.int64_t(err)
	}
	var pk device.NoisePublicKey
	if e := pk.FromHex(C.GoString(pubKeyHex)); e != nil {
		return C.int64_t(C.WG_ERR_KEY_PARSE)
	}
	peer, e := dev.NewPeer(pk)
	if e != nil {
		return C.int64_t(C.WG_ERR_PEER_CREATE)
	}
	return C.int64_t(peerRegistry.Add(peer))
}

//export wgDeviceLookupPeer
func wgDeviceLookupPeer(handle C.int64_t, pubKeyHex *C.char) C.int64_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return 0
	}
	var pk device.NoisePublicKey
	if e := pk.FromHex(C.GoString(pubKeyHex)); e != nil {
		return 0
	}
	peer := dev.LookupPeer(pk)
	if peer == nil {
		return 0
	}
	return C.int64_t(peerRegistry.Add(peer))
}

//export wgDeviceRemovePeer
func wgDeviceRemovePeer(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	var pk device.NoisePublicKey
	if e := pk.FromHex(C.GoString(pubKeyHex)); e != nil {
		return C.WG_ERR_KEY_PARSE
	}
	dev.RemovePeer(pk)
	return C.WG_OK
}

//export wgDeviceRemoveAllPeers
func wgDeviceRemoveAllPeers(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	dev.RemoveAllPeers()
	return C.WG_OK
}

// ---------- Device Miscellaneous ----------

//export wgDevicePopulatePools
func wgDevicePopulatePools(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	dev.PopulatePools()
	return C.WG_OK
}

//export wgDeviceDisableRoaming
func wgDeviceDisableRoaming(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	dev.DisableSomeRoamingForBrokenMobileSemantics()
	return C.WG_OK
}

//export wgDeviceSendKeepalivesToPeers
func wgDeviceSendKeepalivesToPeers(handle C.int64_t) C.int32_t {
	dev, err := getDevice(int64(handle))
	if err != C.WG_OK {
		return err
	}
	dev.SendKeepalivesToPeersWithCurrentKeypair()
	return C.WG_OK
}

// ---------- Message Handling (Handshake Protocol) ----------
// ConsumeMessageInitiation, ConsumeMessageResponse, CreateMessageInitiation,
// CreateMessageResponse, SendHandshakeCookie are internal protocol operations.
// They are invoked automatically by device goroutines (RoutineHandshake, etc.)
// and not exposed directly — the device handles them upon Up().

// ---------- Routine Workers ----------
// RoutineDecryption, RoutineEncryption, RoutineHandshake, RoutineReadFromTUN,
// RoutineReceiveIncoming, RoutineTUNEventReader are goroutines started
// automatically by device.Up(). They should not be called from FFI.

// ---------- Queue & Pool Operations ----------
// GetInboundElement, PutInboundElement, GetOutboundElement, PutOutboundElement,
// GetInboundElementsContainer, PutInboundElementsContainer,
// GetOutboundElementsContainer, PutOutboundElementsContainer,
// GetMessageBuffer, PutMessageBuffer, NewOutboundElement, DeleteKeypair
// are internal memory pool operations managed by the device.
// PopulatePools() is exposed above for pre-warming.

// ---------- Helpers ----------

func getDevice(handle int64) (*device.Device, C.int32_t) {
	obj, ok := deviceRegistry.Get(handle)
	if !ok {
		return nil, C.WG_ERR_NOT_FOUND
	}
	return obj.(*deviceEntry).device, C.WG_OK
}

//export wgFreeString
func wgFreeString(s *C.char) {
	C.free(unsafe.Pointer(s))
}