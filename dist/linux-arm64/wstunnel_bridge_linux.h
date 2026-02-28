#ifndef WSTUNNEL_BRIDGE_LINUX_H
#define WSTUNNEL_BRIDGE_LINUX_H

#include <stdint.h>
#include <stdbool.h>

/*
 * wstunnel-bridge-linux: C FFI wrapper for wstunnel (Linux)
 *
 * Wraps wstunnel identically to wstunnel-cli: constructs the same Client/Server
 * config and calls run_client()/run_server() internally.
 *
 * Client usage:
 *   1. (Optional) wstunnel_set_log_callback()
 *   2. wstunnel_init_logging()
 *   3. config = wstunnel_config_new()
 *   4. wstunnel_config_set_remote_url(config, ...)
 *   5. wstunnel_config_add_tunnel_udp/tcp/socks5(config, ...)
 *   6. wstunnel_client_start(config)
 *   7. wstunnel_config_free(config)
 *   ...
 *   8. wstunnel_client_stop()
 *
 * Server usage:
 *   1. (Optional) wstunnel_set_log_callback()
 *   2. wstunnel_init_logging()
 *   3. config = wstunnel_server_config_new()
 *   4. wstunnel_server_config_set_bind_url(config, ...)
 *   5. wstunnel_server_config_set_tls_certificate/key(config, ...)
 *   6. wstunnel_server_start(config)
 *   7. wstunnel_server_config_free(config)
 *   ...
 *   8. wstunnel_server_stop()
 */

/* ═══════════════════════════════════════════════════════════════
 * Return codes
 * ═══════════════════════════════════════════════════════════════ */
#define WS_OK                    0
#define WS_ERR_ALREADY_RUNNING  -1
#define WS_ERR_INVALID_PARAM    -2
#define WS_ERR_RUNTIME          -3
#define WS_ERR_START_FAILED     -4
#define WS_ERR_NOT_RUNNING      -5
#define WS_ERR_CONFIG_NULL      -6

/* ═══════════════════════════════════════════════════════════════
 * Log levels
 * ═══════════════════════════════════════════════════════════════ */
#define WS_LOG_ERROR  0
#define WS_LOG_WARN   1
#define WS_LOG_INFO   2
#define WS_LOG_DEBUG  3
#define WS_LOG_TRACE  4

/* ═══════════════════════════════════════════════════════════════
 * Opaque config handles
 * ═══════════════════════════════════════════════════════════════ */
typedef struct WstunnelConfig WstunnelConfig;
typedef struct WstunnelServerConfig WstunnelServerConfig;

/* ═══════════════════════════════════════════════════════════════
 * Log callback
 * ═══════════════════════════════════════════════════════════════ */

typedef void (*WstunnelLogCallback)(int32_t level, const char *message, void *context);

void wstunnel_set_log_callback(WstunnelLogCallback callback, void *context);
void wstunnel_init_logging(int32_t log_level);

/* ═══════════════════════════════════════════════════════════════
 * Client Config Builder
 * ═══════════════════════════════════════════════════════════════ */

WstunnelConfig *wstunnel_config_new(void);
void wstunnel_config_free(WstunnelConfig *config);

/* Remote server URL (required) — e.g. "wss://example.com:443" */
int32_t wstunnel_config_set_remote_url(WstunnelConfig *config, const char *url);

/* HTTP upgrade path prefix (default: "v1", used as secret in Ghost Mode) */
int32_t wstunnel_config_set_http_upgrade_path_prefix(WstunnelConfig *config, const char *prefix);

/* HTTP upgrade credentials for Basic auth — format: "USER:PASS" */
int32_t wstunnel_config_set_http_upgrade_credentials(WstunnelConfig *config, const char *credentials);

/* TLS certificate verification (default: false) */
int32_t wstunnel_config_set_tls_verify(WstunnelConfig *config, bool verify);

/* Override TLS SNI domain name */
int32_t wstunnel_config_set_tls_sni_override(WstunnelConfig *config, const char *domain);

/* Disable sending SNI during TLS handshake */
int32_t wstunnel_config_set_tls_sni_disable(WstunnelConfig *config, bool disable);

/* WebSocket ping frequency in seconds (default: 30, 0 to disable) */
int32_t wstunnel_config_set_websocket_ping_frequency(WstunnelConfig *config, uint32_t secs);

/* WebSocket frame masking (default: false) */
int32_t wstunnel_config_set_websocket_mask_frame(WstunnelConfig *config, bool mask);

/* Minimum idle connections in pool (default: 0) */
int32_t wstunnel_config_set_connection_min_idle(WstunnelConfig *config, uint32_t count);

/* Maximum connection retry backoff in seconds (default: 300 = 5 min) */
int32_t wstunnel_config_set_connection_retry_max_backoff(WstunnelConfig *config, uint64_t secs);

/* HTTP proxy for connecting to server — "HOST:PORT" or "http://HOST:PORT" */
int32_t wstunnel_config_set_http_proxy(WstunnelConfig *config, const char *proxy);

/* Add custom HTTP header to upgrade request */
int32_t wstunnel_config_add_http_header(WstunnelConfig *config, const char *name, const char *value);

/* Tokio worker threads (default: 2) */
int32_t wstunnel_config_set_worker_threads(WstunnelConfig *config, uint32_t threads);

/* ─── Tunnel Rules (equivalent to CLI -L flag) ─────────────── */

/* UDP tunnel: -L udp://local_host:local_port:remote_host:remote_port */
int32_t wstunnel_config_add_tunnel_udp(
    WstunnelConfig *config,
    const char     *local_host,
    uint16_t        local_port,
    const char     *remote_host,
    uint16_t        remote_port,
    uint64_t        timeout_secs
);

/* TCP tunnel: -L tcp://local_host:local_port:remote_host:remote_port */
int32_t wstunnel_config_add_tunnel_tcp(
    WstunnelConfig *config,
    const char     *local_host,
    uint16_t        local_port,
    const char     *remote_host,
    uint16_t        remote_port
);

/* SOCKS5 proxy: -L socks5://local_host:local_port */
int32_t wstunnel_config_add_tunnel_socks5(
    WstunnelConfig *config,
    const char     *local_host,
    uint16_t        local_port,
    uint64_t        timeout_secs
);

/* ═══════════════════════════════════════════════════════════════
 * Client Control
 * ═══════════════════════════════════════════════════════════════ */

int32_t wstunnel_client_start(WstunnelConfig *config);
int32_t wstunnel_client_stop(void);
int32_t wstunnel_client_is_running(void);
const char *wstunnel_client_get_last_error(void);
const char *wstunnel_get_version(void);

/* ═══════════════════════════════════════════════════════════════
 * Server Config Builder
 * ═══════════════════════════════════════════════════════════════ */

WstunnelServerConfig *wstunnel_server_config_new(void);
void wstunnel_server_config_free(WstunnelServerConfig *config);

/* Bind URL (required) — e.g. "wss://0.0.0.0:8443" or "ws://0.0.0.0:8080" */
int32_t wstunnel_server_config_set_bind_url(WstunnelServerConfig *config, const char *url);

/* TLS certificate PEM file path (optional, wss:// uses self-signed if not set) */
int32_t wstunnel_server_config_set_tls_certificate(WstunnelServerConfig *config, const char *path);

/* TLS private key PEM file path */
int32_t wstunnel_server_config_set_tls_private_key(WstunnelServerConfig *config, const char *path);

/* TLS client CA certificates PEM file path for mutual TLS */
int32_t wstunnel_server_config_set_tls_client_ca_certs(WstunnelServerConfig *config, const char *path);

/* Restrict tunnels to specific destinations — "host:port" (repeatable) */
int32_t wstunnel_server_config_add_restrict_to(WstunnelServerConfig *config, const char *target);

/* Restrict HTTP upgrade path prefix (repeatable) */
int32_t wstunnel_server_config_add_restrict_path_prefix(WstunnelServerConfig *config, const char *prefix);

/* WebSocket ping frequency in seconds (default: 30, 0 to disable) */
int32_t wstunnel_server_config_set_websocket_ping_frequency(WstunnelServerConfig *config, uint32_t secs);

/* WebSocket frame masking (default: false) */
int32_t wstunnel_server_config_set_websocket_mask_frame(WstunnelServerConfig *config, bool mask);

/* Tokio worker threads (default: 2) */
int32_t wstunnel_server_config_set_worker_threads(WstunnelServerConfig *config, uint32_t threads);

/* ═══════════════════════════════════════════════════════════════
 * Server Control
 * ═══════════════════════════════════════════════════════════════ */

int32_t wstunnel_server_start(WstunnelServerConfig *config);
int32_t wstunnel_server_stop(void);
int32_t wstunnel_server_is_running(void);
const char *wstunnel_server_get_last_error(void);

#endif /* WSTUNNEL_BRIDGE_LINUX_H */