/**
 * firewall_bridge_linux.h — Native firewall and routing bridge.
 *
 * All functions return 0 on success, negative on error.
 * Use firewall_bridge_get_last_error() for error details.
 */

#ifndef FIREWALL_BRIDGE_LINUX_H
#define FIREWALL_BRIDGE_LINUX_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Error codes */
#define FW_OK                    0
#define FW_ERR_ALREADY_INIT     -1
#define FW_ERR_NOT_INIT         -2
#define FW_ERR_NFT_FAILED       -3
#define FW_ERR_NETLINK_FAILED   -4
#define FW_ERR_INVALID_PARAM    -5
#define FW_ERR_IO_ERROR         -6
#define FW_ERR_PERMISSION       -7

/* Address families */
#define FW_AF_INET   2
#define FW_AF_INET6  10

/* --- Lifecycle --- */

int32_t     firewall_bridge_init(void);
void        firewall_bridge_cleanup(void);
const char* firewall_bridge_get_version(void);
const char* firewall_bridge_get_last_error(void);

/* --- Firewall: INPUT rules --- */

int32_t fw_add_input_accept(uint8_t family, const char* proto,
                            uint16_t dport, const char* source);

int32_t fw_add_input_drop(uint8_t family, const char* proto,
                          uint16_t dport, const char* source);

int32_t fw_del_input(uint8_t family, const char* proto,
                     uint16_t dport, const char* source,
                     const char* action);

/* --- Firewall: FORWARD rules --- */

int32_t fw_add_forward(const char* in_iface, const char* out_iface,
                       const char* state_match);

int32_t fw_del_forward(const char* in_iface, const char* out_iface,
                       const char* state_match);

/* --- Firewall: NAT rules --- */

int32_t fw_add_nat_masquerade(const char* source_network,
                              const char* out_iface);

int32_t fw_del_nat_masquerade(const char* source_network,
                              const char* out_iface);

/* --- Firewall: Query & Control --- */

const char* fw_list_rules(void);
int32_t     fw_flush_table(void);

/* --- Routing: Policy rules --- */

int32_t rt_add_policy(const char* from_network, const char* to_network,
                      const char* table_name, uint32_t priority);

int32_t rt_del_policy(const char* from_network, const char* to_network,
                      const char* table_name, uint32_t priority);

/* --- Routing: Routes --- */

int32_t rt_add_route(const char* destination, const char* device,
                     const char* table_name);

int32_t rt_del_route(const char* destination, const char* device,
                     const char* table_name);

/* --- Routing: Table management --- */

int32_t rt_ensure_table(uint32_t table_id, const char* table_name);
int32_t rt_flush_cache(void);
int32_t rt_enable_ip_forward(void);

#ifdef __cplusplus
}
#endif

#endif /* FIREWALL_BRIDGE_LINUX_H */