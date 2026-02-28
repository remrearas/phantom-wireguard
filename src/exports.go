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
//
// exports.go — ALL //export FFI functions (thin wrappers)
// CGo constraint: //export must be in package main.

package main

/*
#include "wireguard_go_bridge.h"

// C wrapper to invoke the log callback function pointer from Go.
static inline void invoke_log_callback(WgLogCallback cb, int32_t level, const char *msg, void *ctx) {
    if (cb) cb(level, msg, ctx);
}
*/
import "C"
import (
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"syscall"
	"unsafe"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/ipc"
	"golang.zx2c4.com/wireguard/tun"

	"wireguard-go-bridge/bridge"
	"wireguard-go-bridge/core"
)

// bridgeState is the global singleton for bridge-db high-level API.
var bridgeState = bridge.New()

// ============================================================================
// Log Callback
// ============================================================================

//export BridgeSetLogCallback
func BridgeSetLogCallback(callback C.WgLogCallback, context unsafe.Pointer) {
	if callback == nil {
		bridge.SetLogCallback(nil, nil)
		return
	}
	cb := callback
	bridge.SetLogCallback(func(level int32, msg *byte, ctx unsafe.Pointer) {
		C.invoke_log_callback(cb, C.int32_t(level), (*C.char)(unsafe.Pointer(msg)), ctx)
	}, context)
}

// ============================================================================
// Bridge-DB High-Level API
// ============================================================================

//export BridgeInit
func BridgeInit(dbPath *C.char, ifname *C.char, listenPort C.int, logLevel C.int) C.int32_t {
	if err := bridgeState.Init(C.GoString(dbPath), C.GoString(ifname), int(listenPort), int(logLevel)); err != nil {
		return errDBOpen
	}
	return errOK
}

//export BridgeGetStatus
func BridgeGetStatus() *C.char {
	return C.CString(bridgeState.GetStatus())
}

//export BridgeSetup
func BridgeSetup(endpoint *C.char, network *C.char, dnsPrimary *C.char, dnsSecondary *C.char, mtu C.int, fwmark C.int) C.int32_t {
	if err := bridgeState.Setup(C.GoString(endpoint), C.GoString(network), C.GoString(dnsPrimary), C.GoString(dnsSecondary), int(mtu), int(fwmark)); err != nil {
		return errDBWrite
	}
	return errOK
}

//export BridgeClose
func BridgeClose() C.int32_t {
	if err := bridgeState.Close(); err != nil {
		return errNotInitialized
	}
	return errOK
}

//export BridgeStart
func BridgeStart() C.int32_t {
	if err := bridgeState.Start(); err != nil {
		return C.WG_ERR_DEVICE_UP
	}
	return errOK
}

//export BridgeStop
func BridgeStop() C.int32_t {
	if err := bridgeState.Stop(); err != nil {
		return C.WG_ERR_DEVICE_DOWN
	}
	return errOK
}

//export BridgeAddClient
func BridgeAddClient(allowedIp *C.char) *C.char {
	result, err := bridgeState.AddClient(C.GoString(allowedIp))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeRemoveClient
func BridgeRemoveClient(pubKeyHex *C.char) C.int32_t {
	if err := bridgeState.RemoveClient(C.GoString(pubKeyHex)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeEnableClient
func BridgeEnableClient(pubKeyHex *C.char) C.int32_t {
	if err := bridgeState.EnableClient(C.GoString(pubKeyHex)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeDisableClient
func BridgeDisableClient(pubKeyHex *C.char) C.int32_t {
	if err := bridgeState.DisableClient(C.GoString(pubKeyHex)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeGetClient
func BridgeGetClient(pubKeyHex *C.char) *C.char {
	result, err := bridgeState.GetClient(C.GoString(pubKeyHex))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeListClients
func BridgeListClients(page C.int, limit C.int) *C.char {
	result, err := bridgeState.ListClients(int(page), int(limit))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeExportClientConfig
func BridgeExportClientConfig(pubKeyHex *C.char, serverEndpoint *C.char, dns *C.char) *C.char {
	result, err := bridgeState.ExportClientConfig(C.GoString(pubKeyHex), C.GoString(serverEndpoint), C.GoString(dns))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeStartStatsSync
func BridgeStartStatsSync(intervalSec C.int) C.int32_t {
	if err := bridgeState.StartStatsSync(int(intervalSec)); err != nil {
		return errStatsRunning
	}
	return errOK
}

//export BridgeStopStatsSync
func BridgeStopStatsSync() C.int32_t {
	_ = bridgeState.StopStatsSync()
	return errOK
}

//export BridgeGetDeviceInfo
func BridgeGetDeviceInfo() *C.char {
	result, err := bridgeState.GetDeviceInfo()
	if err != nil {
		return nil
	}
	return C.CString(result)
}

// ============================================================================
// Server Config API
// ============================================================================

//export BridgeGetServerConfig
func BridgeGetServerConfig() *C.char {
	result, err := bridgeState.GetServerConfig()
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeSetServerConfig
func BridgeSetServerConfig(configJSON *C.char) C.int32_t {
	if err := bridgeState.SetServerConfig(C.GoString(configJSON)); err != nil {
		return errDBWrite
	}
	return errOK
}

// ============================================================================
// Multihop Tunnel API
// ============================================================================

//export BridgeCreateMultihopTunnel
func BridgeCreateMultihopTunnel(name *C.char, ifaceName *C.char, remoteEndpoint *C.char, remotePubKey *C.char, fwmark C.int) *C.char {
	result, err := bridgeState.CreateMultihopTunnel(C.GoString(name), C.GoString(ifaceName), C.GoString(remoteEndpoint), C.GoString(remotePubKey), int(fwmark))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeStartMultihopTunnel
func BridgeStartMultihopTunnel(name *C.char) C.int32_t {
	if err := bridgeState.StartMultihopTunnel(C.GoString(name)); err != nil {
		return errInternal
	}
	return errOK
}

//export BridgeStopMultihopTunnel
func BridgeStopMultihopTunnel(name *C.char) C.int32_t {
	if err := bridgeState.StopMultihopTunnel(C.GoString(name)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeDisableMultihopTunnel
func BridgeDisableMultihopTunnel(name *C.char) C.int32_t {
	if err := bridgeState.DisableMultihopTunnel(C.GoString(name)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeDeleteMultihopTunnel
func BridgeDeleteMultihopTunnel(name *C.char) C.int32_t {
	if err := bridgeState.DeleteMultihopTunnel(C.GoString(name)); err != nil {
		return C.WG_ERR_NOT_FOUND
	}
	return errOK
}

//export BridgeListMultihopTunnels
func BridgeListMultihopTunnels() *C.char {
	result, err := bridgeState.ListMultihopTunnels()
	if err != nil {
		return nil
	}
	return C.CString(result)
}

//export BridgeGetMultihopTunnel
func BridgeGetMultihopTunnel(name *C.char) *C.char {
	result, err := bridgeState.GetMultihopTunnel(C.GoString(name))
	if err != nil {
		return nil
	}
	return C.CString(result)
}

// ============================================================================
// Low-Level Device API (retained for multihop/advanced use)
// ============================================================================

// deviceEntry stores a device along with its associated TUN for cleanup.
type deviceEntry struct {
	device *device.Device
	tun    tun.Device
}

//export NewDevice
func NewDevice(ifname *C.char, mtu C.int, loggerHandle C.int64_t) C.int64_t {
	name := C.GoString(ifname)
	tunDev, err := tun.CreateTUN(name, int(mtu))
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

//export DeviceClose
func DeviceClose(handle C.int64_t) C.int32_t {
	obj, ok := deviceRegistry.Get(int64(handle))
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	entry := obj.(*deviceEntry)
	entry.device.Close()
	deviceRegistry.Remove(int64(handle))
	return C.WG_OK
}

//export DeviceUp
func DeviceUp(handle C.int64_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.Up(); e != nil {
		return C.WG_ERR_DEVICE_UP
	}
	return C.WG_OK
}

//export DeviceDown
func DeviceDown(handle C.int64_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.Down(); e != nil {
		return C.WG_ERR_DEVICE_DOWN
	}
	return C.WG_OK
}

//export DeviceSetPrivateKey
func DeviceSetPrivateKey(handle C.int64_t, hexKey *C.char) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
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

//export DeviceIpcSet
func DeviceIpcSet(handle C.int64_t, config *C.char) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.IpcSet(C.GoString(config)); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export DeviceIpcGet
func DeviceIpcGet(handle C.int64_t) *C.char {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return nil
	}
	config, e := dev.IpcGet()
	if e != nil {
		return nil
	}
	return C.CString(config)
}

//export DeviceNewPeer
func DeviceNewPeer(handle C.int64_t, pubKeyHex *C.char) C.int64_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return C.int64_t(errC)
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

//export DeviceLookupPeer
func DeviceLookupPeer(handle C.int64_t, pubKeyHex *C.char) C.int64_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
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

//export DeviceRemovePeer
func DeviceRemovePeer(handle C.int64_t, pubKeyHex *C.char) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	var pk device.NoisePublicKey
	if e := pk.FromHex(C.GoString(pubKeyHex)); e != nil {
		return C.WG_ERR_KEY_PARSE
	}
	dev.RemovePeer(pk)
	return C.WG_OK
}

//export DeviceRemoveAllPeers
func DeviceRemoveAllPeers(handle C.int64_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	dev.RemoveAllPeers()
	return C.WG_OK
}

//export DeviceBindClose
func DeviceBindClose(handle C.int64_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.BindClose(); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export DeviceBindUpdate
func DeviceBindUpdate(handle C.int64_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.BindUpdate(); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export DeviceBindSetMark
func DeviceBindSetMark(handle C.int64_t, mark C.uint32_t) C.int32_t {
	dev, errC := getDevice(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	if e := dev.BindSetMark(uint32(mark)); e != nil {
		return C.WG_ERR_BIND
	}
	return C.WG_OK
}

//export AllowedIpsInsert
func AllowedIpsInsert(deviceHandle C.int64_t, peerPubKeyHex *C.char, prefixStr *C.char) C.int32_t {
	dev, errC := getDevice(int64(deviceHandle))
	if errC != C.WG_OK {
		return errC
	}
	config := "public_key=" + C.GoString(peerPubKeyHex) + "\nallowed_ip=" + C.GoString(prefixStr) + "\n"
	if e := dev.IpcSet(config); e != nil {
		return C.WG_ERR_IPC_SET
	}
	return C.WG_OK
}

//export PeerStart
func PeerStart(handle C.int64_t) C.int32_t {
	peer, errC := getPeer(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	peer.Start()
	return C.WG_OK
}

//export PeerStop
func PeerStop(handle C.int64_t) C.int32_t {
	peer, errC := getPeer(int64(handle))
	if errC != C.WG_OK {
		return errC
	}
	peer.Stop()
	return C.WG_OK
}

// ============================================================================
// Key Generation
// ============================================================================

//export GeneratePrivateKey
func GeneratePrivateKey() *C.char {
	key, err := core.GeneratePrivateKey()
	if err != nil {
		return nil
	}
	return C.CString(key)
}

//export DerivePublicKey
func DerivePublicKey(privateKeyHex *C.char) *C.char {
	pub, err := core.DerivePublicKey(C.GoString(privateKeyHex))
	if err != nil {
		return nil
	}
	return C.CString(pub)
}

//export GeneratePresharedKey
func GeneratePresharedKey() *C.char {
	key, err := core.GeneratePresharedKey()
	if err != nil {
		return nil
	}
	return C.CString(key)
}

// ============================================================================
// Version & Utility
// ============================================================================

//export BridgeVersion
func BridgeVersion() *C.char {
	return C.CString("2.0.0")
}

//export WireguardGoVersion
func WireguardGoVersion() *C.char {
	return C.CString("0.0.20230223")
}

//export FreeString
func FreeString(s *C.char) {
	C.free(unsafe.Pointer(s))
}

// ============================================================================
// UAPI / Run (for tests — standalone daemon mode)
// ============================================================================

const defaultSocketDir = "/var/run/wireguard"

//export Run
func Run(ifname *C.char, logLevel C.int) C.int32_t {
	interfaceName := string(C.GoString(ifname))
	logger := device.NewLogger(int(logLevel), "("+interfaceName+") ")

	tunDev, err := tun.CreateTUN(interfaceName, device.DefaultMTU)
	if err != nil {
		logger.Errorf("Failed to create TUN device: %v", err)
		return C.WG_ERR_TUN_CREATE
	}
	if realName, nameErr := tunDev.Name(); nameErr == nil {
		interfaceName = realName
	}

	dev := device.NewDevice(tunDev, conn.NewDefaultBind(), logger)
	logger.Verbosef("Device started")

	fileUAPI, err := ipc.UAPIOpen(interfaceName)
	if err != nil {
		logger.Errorf("UAPI listen error: %v", err)
		dev.Close()
		return C.WG_ERR_INTERNAL
	}

	uapi, err := ipc.UAPIListen(interfaceName, fileUAPI)
	if err != nil {
		logger.Errorf("Failed to listen on UAPI socket: %v", err)
		dev.Close()
		return C.WG_ERR_INTERNAL
	}

	errs := make(chan error)
	go func() {
		for {
			c, acceptErr := uapi.Accept()
			if acceptErr != nil {
				errs <- acceptErr
				return
			}
			go dev.IpcHandle(c)
		}
	}()

	logger.Verbosef("UAPI listener started")

	term := make(chan os.Signal, 1)
	signal.Notify(term, syscall.SIGTERM, syscall.SIGINT)

	select {
	case <-term:
	case <-errs:
	case <-dev.Wait():
	}

	_ = uapi.Close()
	dev.Close()
	logger.Verbosef("Shutting down")
	return C.WG_OK
}

type uapiListener struct {
	listener net.Listener
	stop     chan struct{}
	wg       sync.WaitGroup
}

var (
	uapiListeners   = make(map[int64]*uapiListener)
	uapiListenersMu sync.Mutex
)

//export DeviceUAPIListen
func DeviceUAPIListen(deviceHandle C.int64_t, ifname *C.char) C.int32_t {
	dev, errC := getDevice(int64(deviceHandle))
	if errC != C.WG_OK {
		return errC
	}
	socketName := C.GoString(ifname)
	socketPath := filepath.Join(defaultSocketDir, socketName+".sock")
	if e := os.MkdirAll(defaultSocketDir, 0711); e != nil {
		return C.WG_ERR_INTERNAL
	}
	_ = os.Remove(socketPath)
	listener, e := net.Listen("unix", socketPath)
	if e != nil {
		return C.WG_ERR_INTERNAL
	}
	_ = os.Chmod(socketPath, 0600)

	ul := &uapiListener{listener: listener, stop: make(chan struct{})}
	ul.wg.Add(1)
	go func() {
		defer ul.wg.Done()
		for {
			c, acceptErr := listener.Accept()
			if acceptErr != nil {
				select {
				case <-ul.stop:
					return
				default:
					continue
				}
			}
			go dev.IpcHandle(c)
		}
	}()

	uapiListenersMu.Lock()
	uapiListeners[int64(deviceHandle)] = ul
	uapiListenersMu.Unlock()
	return C.WG_OK
}

//export DeviceUAPIClose
func DeviceUAPIClose(deviceHandle C.int64_t, ifname *C.char) C.int32_t {
	uapiListenersMu.Lock()
	ul, ok := uapiListeners[int64(deviceHandle)]
	if ok {
		delete(uapiListeners, int64(deviceHandle))
	}
	uapiListenersMu.Unlock()
	if !ok {
		return C.WG_ERR_NOT_FOUND
	}
	close(ul.stop)
	_ = ul.listener.Close()
	ul.wg.Wait()
	socketName := C.GoString(ifname)
	socketPath := filepath.Join(defaultSocketDir, socketName+".sock")
	_ = os.Remove(socketPath)
	return C.WG_OK
}

//export DeviceUAPISocketPath
func DeviceUAPISocketPath(ifname *C.char) *C.char {
	return C.CString(filepath.Join(defaultSocketDir, C.GoString(ifname)+".sock"))
}

// ============================================================================
// Internal helpers
// ============================================================================

func getDevice(handle int64) (*device.Device, C.int32_t) {
	obj, ok := deviceRegistry.Get(handle)
	if !ok {
		return nil, C.WG_ERR_NOT_FOUND
	}
	return obj.(*deviceEntry).device, C.WG_OK
}

func getPeer(handle int64) (*device.Peer, C.int32_t) {
	obj, ok := peerRegistry.Get(handle)
	if !ok {
		return nil, C.WG_ERR_NOT_FOUND
	}
	return obj.(*device.Peer), C.WG_OK
}

func getLogger(handle int64) *device.Logger {
	obj, ok := loggerRegistry.Get(handle)
	if !ok {
		return device.NewLogger(device.LogLevelSilent, "")
	}
	return obj.(*device.Logger)
}
