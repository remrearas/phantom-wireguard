// wireguard-go-bridge
//
// Native bridge for wireguard-go → Python via c-shared FFI.
// Compiles to libphantom_wg.so for Linux production environments.
//
// All exported functions use handle-based access for Go objects
// that cannot cross the FFI boundary directly.
//
// Copyright (c) 2025 Rıza Emre ARAS
// Licensed under AGPL-3.0

package main

import "C"

func main() {}