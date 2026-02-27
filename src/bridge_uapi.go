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
	"fmt"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"sync"
	"syscall"

	"golang.zx2c4.com/wireguard/conn"
	"golang.zx2c4.com/wireguard/device"
	"golang.zx2c4.com/wireguard/ipc"
	"golang.zx2c4.com/wireguard/tun"
)

const defaultSocketDir = "/var/run/wireguard"

// Run mirrors wireguard-go main.go foreground mode exactly:
// CreateTUN → NewDevice → UAPIOpen → UAPIListen → accept loop → wait for signal.
// Blocks until SIGTERM/SIGINT. Caller backgrounds with & in shell.
//
//export Run
func Run(ifname *C.char, logLevel C.int) C.int32_t {
	interfaceName := C.GoString(ifname)

	logger := device.NewLogger(int(logLevel), fmt.Sprintf("(%s) ", interfaceName))

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

// --- Individual UAPI functions (for programmatic non-daemon usage) ---

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
	dev, err := getDevice(int64(deviceHandle))
	if err != C.WG_OK {
		return err
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

	ul := &uapiListener{
		listener: listener,
		stop:     make(chan struct{}),
	}

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
	socketName := C.GoString(ifname)
	return C.CString(filepath.Join(defaultSocketDir, socketName+".sock"))
}