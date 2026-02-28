/*
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 *
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 * Licensed under AGPL-3.0 - see LICENSE file for details
 * Third-party licenses - see THIRD_PARTY_LICENSES file for details
 * WireGuard® is a registered trademark of Jason A. Donenfeld.
 *
 * wireguard_go_bridge.h — v2.0.0 public API
 */

#ifndef WIREGUARD_GO_BRIDGE_H
#define WIREGUARD_GO_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

/* Error codes */
#define WG_OK                     0
#define WG_ERR_INVALID_PARAM     -1
#define WG_ERR_TUN_CREATE        -2
#define WG_ERR_DEVICE_CREATE     -3
#define WG_ERR_IPC_SET           -4
#define WG_ERR_NOT_FOUND         -5
#define WG_ERR_ALREADY_EXISTS    -6
#define WG_ERR_DEVICE_UP         -7
#define WG_ERR_DEVICE_DOWN       -8
#define WG_ERR_BIND              -9
#define WG_ERR_KEY_PARSE        -10
#define WG_ERR_PEER_CREATE      -11
#define WG_ERR_SESSION          -12
#define WG_ERR_HANDSHAKE        -13
#define WG_ERR_COOKIE           -14
/* v2 error codes */
#define WG_ERR_DB_OPEN          -20
#define WG_ERR_DB_QUERY         -21
#define WG_ERR_DB_WRITE         -22
#define WG_ERR_IP_EXHAUSTED     -23
#define WG_ERR_NOT_INITIALIZED  -24
#define WG_ERR_STATS_RUNNING    -25
#define WG_ERR_INTERNAL         -99

/* Log levels */
#define WG_LOG_SILENT    0
#define WG_LOG_ERROR     1
#define WG_LOG_VERBOSE   2

/* Log callback (placeholder) */
typedef void (*WgLogCallback)(int32_t level, const char *message, void *context);

#endif /* WIREGUARD_GO_BRIDGE_H */
