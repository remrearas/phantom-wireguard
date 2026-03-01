/**
 * firewall_bridge_linux.h — Stateful firewall and routing bridge (v2).
 *
 * SQLite-backed state management with rule groups, presets, and crash recovery.
 * Functions returning *char (JSON) must be freed with firewall_bridge_free_string().
 * Functions returning const char* are static and must NOT be freed.
 * All other functions return 0 on success, negative on error.
 */

#ifndef FIREWALL_BRIDGE_LINUX_H
#define FIREWALL_BRIDGE_LINUX_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Error codes ---- */

/* v1 codes */
#define FW_OK                    0
#define FW_ERR_ALREADY_INIT     -1
#define FW_ERR_NOT_INIT         -2
#define FW_ERR_NFT_FAILED       -3
#define FW_ERR_NETLINK_FAILED   -4
#define FW_ERR_INVALID_PARAM    -5
#define FW_ERR_IO_ERROR         -6
#define FW_ERR_PERMISSION       -7

/* v2 codes */
#define FW_ERR_DB_OPEN          -10
#define FW_ERR_DB_QUERY         -11
#define FW_ERR_DB_WRITE         -12
#define FW_ERR_GROUP_NOT_FOUND  -13
#define FW_ERR_RULE_NOT_FOUND   -14
#define FW_ERR_INVALID_STATE    -15
#define FW_ERR_ALREADY_STARTED  -16
#define FW_ERR_NOT_STARTED      -17
#define FW_ERR_PRESET_FAILED    -18
#define FW_ERR_VERIFY_FAILED    -19

/* Address families */
#define FW_AF_INET   2
#define FW_AF_INET6  10

/* Log levels */
#define FW_LOG_ERROR   0
#define FW_LOG_WARN    1
#define FW_LOG_INFO    2
#define FW_LOG_DEBUG   3

/* Log callback type */
typedef void (*fw_log_callback_t)(int32_t level, const char* message, void* context);

/* ---- Lifecycle ---- */

int32_t     firewall_bridge_init(const char* db_path);
char*       firewall_bridge_get_status(void);   /* caller frees */
int32_t     firewall_bridge_start(void);
int32_t     firewall_bridge_stop(void);
int32_t     firewall_bridge_close(void);

/* ---- Rule Groups ---- */

char*       fw_create_rule_group(const char* name, const char* group_type, int32_t priority);  /* caller frees */
int32_t     fw_delete_rule_group(const char* name);
int32_t     fw_enable_rule_group(const char* name);
int32_t     fw_disable_rule_group(const char* name);
char*       fw_list_rule_groups(void);           /* caller frees */
char*       fw_get_rule_group(const char* name); /* caller frees */

/* ---- Firewall Rules ---- */

int64_t     fw_add_rule(const char* group_name, const char* chain, const char* rule_type,
                        uint8_t family, const char* proto, uint16_t dport,
                        const char* source, const char* destination,
                        const char* in_iface, const char* out_iface,
                        const char* state_match);
int32_t     fw_remove_rule(int64_t rule_id);
char*       fw_list_rules(const char* group_name); /* NULL=all, caller frees */

/* ---- Routing Rules ---- */

int64_t     rt_add_rule(const char* group_name, const char* rule_type,
                        const char* from_network, const char* to_network,
                        const char* table_name, uint32_t table_id, uint32_t priority,
                        const char* destination, const char* device, uint32_t fwmark);
int32_t     rt_remove_rule(int64_t rule_id);
char*       rt_list_rules(const char* group_name); /* NULL=all, caller frees */

/* ---- Presets (ghost mode) ---- */

char*       fw_apply_preset_vpn(const char* name, const char* wg_iface, uint16_t wg_port,
                                const char* wg_subnet, const char* out_iface);
char*       fw_apply_preset_multihop(const char* name, const char* in_iface, const char* out_iface,
                                     uint32_t fwmark, uint32_t table_id, const char* subnet);
char*       fw_apply_preset_kill_switch(uint16_t wg_port, uint16_t wstunnel_port, const char* wg_iface);
char*       fw_apply_preset_dns_protection(const char* wg_iface);
char*       fw_apply_preset_ipv6_block(void);
int32_t     fw_remove_preset(const char* name);

/* ---- Verify ---- */

char*       fw_get_kernel_state(void);  /* caller frees */
char*       fw_verify_rules(void);      /* caller frees */

/* ---- Utility ---- */

const char* firewall_bridge_get_version(void);      /* static, do NOT free */
const char* firewall_bridge_get_last_error(void);    /* static, do NOT free */
void        firewall_bridge_free_string(char* ptr);
void        firewall_bridge_set_log_callback(fw_log_callback_t callback, void* context);
int32_t     rt_flush_cache(void);
int32_t     rt_enable_ip_forward(void);
int32_t     fw_flush_table(void);

/* ---- v1 compatibility ---- */

int32_t     firewall_bridge_init_legacy(void);
void        firewall_bridge_cleanup(void);

#ifdef __cplusplus
}
#endif

#endif /* FIREWALL_BRIDGE_LINUX_H */