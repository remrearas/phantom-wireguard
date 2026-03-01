//! Preset rule group templates for common firewall scenarios.
//!
//! Each preset creates a named rule group and populates it with the
//! appropriate firewall + routing rules. The metadata JSON stores
//! parameters for reconstruction and audit.

use serde_json::json;

use crate::db::FirewallDB;
use crate::error::ErrorCode;

// ---------------------------------------------------------------------------
// VPN Basic
// ---------------------------------------------------------------------------

/// Create a VPN basic rule group:
/// 1. INPUT ACCEPT udp dport {wg_port}
/// 2. FORWARD ACCEPT iif {wg_iface} oif {out_iface}
/// 3. FORWARD ACCEPT iif {out_iface} oif {wg_iface} ct state established,related
/// 4. POSTROUTING MASQUERADE ip saddr {wg_subnet} oif {out_iface}
pub fn preset_vpn(
    db: &FirewallDB,
    name: &str,
    wg_iface: &str,
    wg_port: u16,
    wg_subnet: &str,
    out_iface: &str,
) -> Result<(), (ErrorCode, String)> {
    let metadata = json!({
        "preset": "vpn",
        "wg_iface": wg_iface,
        "wg_port": wg_port,
        "wg_subnet": wg_subnet,
        "out_iface": out_iface,
    })
    .to_string();

    let group = db
        .create_rule_group(name, "vpn", 100, &metadata)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    let gid = group.id;

    // INPUT ACCEPT: WG listen port
    db.insert_firewall_rule(
        gid, "input", "accept", 2, "udp", wg_port as i32, 0,
        "", "", "", "", "", "wg-listen-port", 0,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // FORWARD: wg → out
    db.insert_firewall_rule(
        gid, "forward", "accept", 2, "", 0, 0,
        "", "", wg_iface, out_iface, "", "wg-forward-out", 1,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // FORWARD: out → wg (established,related)
    db.insert_firewall_rule(
        gid, "forward", "accept", 2, "", 0, 0,
        "", "", out_iface, wg_iface, "established,related", "wg-forward-return", 2,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // POSTROUTING: masquerade
    db.insert_firewall_rule(
        gid, "postrouting", "masquerade", 2, "", 0, 0,
        wg_subnet, "", "", out_iface, "", "wg-nat", 3,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Multihop
// ---------------------------------------------------------------------------

/// Create a multihop rule group:
/// 1. Routing: ensure_table(table_id, name)
/// 2. Routing: policy from {subnet} table {name}
/// 3. Routing: default route dev {out_iface} table {name}
/// 4. FORWARD: in → out
/// 5. FORWARD: out → in (established,related)
/// 6. If fwmark: policy fwmark → table
pub fn preset_multihop(
    db: &FirewallDB,
    name: &str,
    in_iface: &str,
    out_iface: &str,
    fwmark: u32,
    table_id: u32,
    subnet: &str,
) -> Result<(), (ErrorCode, String)> {
    let metadata = json!({
        "preset": "multihop",
        "in_iface": in_iface,
        "out_iface": out_iface,
        "fwmark": fwmark,
        "table_id": table_id,
        "subnet": subnet,
    })
    .to_string();

    let group = db
        .create_rule_group(name, "multihop", 80, &metadata)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    let gid = group.id;

    // Routing: ensure table
    db.insert_routing_rule(gid, "table", "", "", name, table_id as i32, 0, "", "", 0)
        .map_err(|e| (ErrorCode::DbWrite, e))?;

    // Routing: policy from subnet → table
    db.insert_routing_rule(
        gid, "policy", subnet, "", name, table_id as i32, 100, "", "", 0,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // Routing: default route dev out_iface table name
    db.insert_routing_rule(
        gid, "route", "", "", name, table_id as i32, 0, "default", out_iface, 0,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // Routing: fwmark policy (if set)
    if fwmark > 0 {
        db.insert_routing_rule(
            gid, "policy", "", "", name, table_id as i32, 200, "", "", fwmark as i32,
        )
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    }

    // FORWARD: in → out
    db.insert_firewall_rule(
        gid, "forward", "accept", 2, "", 0, 0,
        "", "", in_iface, out_iface, "", "multihop-forward", 0,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    // FORWARD: out → in (established,related)
    db.insert_firewall_rule(
        gid, "forward", "accept", 2, "", 0, 0,
        "", "", out_iface, in_iface, "established,related", "multihop-return", 1,
    )
    .map_err(|e| (ErrorCode::DbWrite, e))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Kill-Switch
// ---------------------------------------------------------------------------

/// Create a kill-switch rule group (high priority = applied first):
///
/// OUTPUT chain:
/// 1. ACCEPT oif lo
/// 2. ACCEPT ct state established,related
/// 3. ACCEPT udp dport {wg_port}
/// 4. ACCEPT oif {wg_iface}
/// 5. ACCEPT udp dport 67:68 (DHCP)
/// 6. [optional] ACCEPT tcp dport {wstunnel_port}
/// 7. DROP (catch-all)
///
/// INPUT chain:
/// 8. ACCEPT iif lo
/// 9. ACCEPT ct state established,related
/// 10. DROP (catch-all)
pub fn preset_kill_switch(
    db: &FirewallDB,
    wg_port: u16,
    wstunnel_port: u16,
    wg_iface: &str,
) -> Result<(), (ErrorCode, String)> {
    let metadata = json!({
        "preset": "kill_switch",
        "wg_port": wg_port,
        "wstunnel_port": wstunnel_port,
        "wg_iface": wg_iface,
    })
    .to_string();

    let group = db
        .create_rule_group("kill-switch", "kill_switch", 10, &metadata)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    let gid = group.id;
    let mut pos = 0;

    // OUTPUT: accept loopback
    db.insert_firewall_rule(gid, "output", "accept", 2, "", 0, 0, "", "", "", "lo", "", "ks-lo-out", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // OUTPUT: accept established,related
    db.insert_firewall_rule(gid, "output", "accept", 2, "", 0, 0, "", "", "", "", "established,related", "ks-ct-out", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // OUTPUT: accept WG port
    db.insert_firewall_rule(gid, "output", "accept", 2, "udp", wg_port as i32, 0, "", "", "", "", "", "ks-wg-out", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // OUTPUT: accept via WG interface
    db.insert_firewall_rule(gid, "output", "accept", 2, "", 0, 0, "", "", "", wg_iface, "", "ks-wg-iface", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // OUTPUT: accept DHCP (67-68) — use dport=67, separate rule for 68
    db.insert_firewall_rule(gid, "output", "accept", 2, "udp", 67, 0, "", "", "", "", "", "ks-dhcp-67", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    db.insert_firewall_rule(gid, "output", "accept", 2, "udp", 68, 0, "", "", "", "", "", "ks-dhcp-68", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // OUTPUT: accept wstunnel port (if configured)
    if wstunnel_port > 0 {
        db.insert_firewall_rule(gid, "output", "accept", 2, "tcp", wstunnel_port as i32, 0, "", "", "", "", "", "ks-wst-out", pos)
            .map_err(|e| (ErrorCode::DbWrite, e))?;
        pos += 1;
    }

    // OUTPUT: drop catch-all
    db.insert_firewall_rule(gid, "output", "drop", 2, "", 0, 0, "", "", "", "", "", "ks-drop-out", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // INPUT: accept loopback
    db.insert_firewall_rule(gid, "input", "accept", 2, "", 0, 0, "", "", "lo", "", "", "ks-lo-in", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // INPUT: accept established,related
    db.insert_firewall_rule(gid, "input", "accept", 2, "", 0, 0, "", "", "", "", "established,related", "ks-ct-in", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    pos += 1;

    // INPUT: drop catch-all
    db.insert_firewall_rule(gid, "input", "drop", 2, "", 0, 0, "", "", "", "", "", "ks-drop-in", pos)
        .map_err(|e| (ErrorCode::DbWrite, e))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// DNS Leak Protection
// ---------------------------------------------------------------------------

/// Block DNS (port 53) except via WG interface and localhost:
/// 1. OUTPUT ACCEPT oif {wg_iface} udp dport 53
/// 2. OUTPUT ACCEPT oif {wg_iface} tcp dport 53
/// 3. OUTPUT ACCEPT oif lo udp dport 53
/// 4. OUTPUT DROP udp dport 53
/// 5. OUTPUT DROP tcp dport 53
pub fn preset_dns_protection(
    db: &FirewallDB,
    wg_iface: &str,
) -> Result<(), (ErrorCode, String)> {
    let metadata = json!({
        "preset": "dns_protection",
        "wg_iface": wg_iface,
    })
    .to_string();

    let group = db
        .create_rule_group("dns-protection", "dns_protection", 20, &metadata)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    let gid = group.id;

    // Allow DNS via WG
    db.insert_firewall_rule(gid, "output", "accept", 2, "udp", 53, 0, "", "", "", wg_iface, "", "dns-wg-udp", 0)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    db.insert_firewall_rule(gid, "output", "accept", 2, "tcp", 53, 0, "", "", "", wg_iface, "", "dns-wg-tcp", 1)
        .map_err(|e| (ErrorCode::DbWrite, e))?;

    // Allow DNS via localhost (local resolver)
    db.insert_firewall_rule(gid, "output", "accept", 2, "udp", 53, 0, "", "", "", "lo", "", "dns-lo-udp", 2)
        .map_err(|e| (ErrorCode::DbWrite, e))?;

    // Block DNS everywhere else
    db.insert_firewall_rule(gid, "output", "drop", 2, "udp", 53, 0, "", "", "", "", "", "dns-block-udp", 3)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    db.insert_firewall_rule(gid, "output", "drop", 2, "tcp", 53, 0, "", "", "", "", "", "dns-block-tcp", 4)
        .map_err(|e| (ErrorCode::DbWrite, e))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// IPv6 Block
// ---------------------------------------------------------------------------

/// Block all IPv6 traffic on input, output, and forward chains.
pub fn preset_ipv6_block(db: &FirewallDB) -> Result<(), (ErrorCode, String)> {
    let metadata = json!({"preset": "ipv6_block"}).to_string();

    let group = db
        .create_rule_group("ipv6-block", "ipv6_block", 5, &metadata)
        .map_err(|e| (ErrorCode::DbWrite, e))?;
    let gid = group.id;

    // family=10 (AF_INET6) + drop on all chains
    for (i, chain) in ["input", "output", "forward"].iter().enumerate() {
        db.insert_firewall_rule(gid, chain, "drop", 10, "", 0, 0, "", "", "", "", "", &format!("ipv6-{chain}"), i as i32)
            .map_err(|e| (ErrorCode::DbWrite, e))?;
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::FirewallDB;

    fn test_db() -> FirewallDB {
        FirewallDB::open(":memory:").expect("in-memory DB")
    }

    #[test]
    fn test_preset_vpn() {
        let db = test_db();
        preset_vpn(&db, "vpn-basic", "wg0", 51820, "10.8.0.0/24", "eth0").unwrap();

        let group = db.get_rule_group("vpn-basic").unwrap();
        assert_eq!(group.group_type, "vpn");
        assert_eq!(group.priority, 100);

        let rules = db.firewall_rules_for_group(group.id).unwrap();
        assert_eq!(rules.len(), 4);
        assert_eq!(rules[0].chain, "input");
        assert_eq!(rules[0].dport, 51820);
        assert_eq!(rules[1].chain, "forward");
        assert_eq!(rules[2].state_match, "established,related");
        assert_eq!(rules[3].rule_type, "masquerade");
    }

    #[test]
    fn test_preset_multihop() {
        let db = test_db();
        preset_multihop(&db, "hop1", "wg0", "wg-hop1", 100, 200, "10.8.0.0/24").unwrap();

        let group = db.get_rule_group("hop1").unwrap();
        assert_eq!(group.group_type, "multihop");

        let fw_rules = db.firewall_rules_for_group(group.id).unwrap();
        assert_eq!(fw_rules.len(), 2); // forward + return

        let rt_rules = db.routing_rules_for_group(group.id).unwrap();
        assert_eq!(rt_rules.len(), 4); // table + policy + route + fwmark policy
    }

    #[test]
    fn test_preset_multihop_no_fwmark() {
        let db = test_db();
        preset_multihop(&db, "hop-nofwm", "wg0", "wg-hop1", 0, 200, "10.8.0.0/24").unwrap();

        let group = db.get_rule_group("hop-nofwm").unwrap();
        let rt_rules = db.routing_rules_for_group(group.id).unwrap();
        assert_eq!(rt_rules.len(), 3); // no fwmark policy
    }

    #[test]
    fn test_preset_kill_switch() {
        let db = test_db();
        preset_kill_switch(&db, 51820, 443, "wg0").unwrap();

        let group = db.get_rule_group("kill-switch").unwrap();
        assert_eq!(group.group_type, "kill_switch");
        assert_eq!(group.priority, 10); // high priority

        let rules = db.firewall_rules_for_group(group.id).unwrap();
        // lo + ct + wg-port + wg-iface + dhcp67 + dhcp68 + wstunnel + drop-out + lo-in + ct-in + drop-in = 11
        assert_eq!(rules.len(), 11);

        // First rule is OUTPUT accept lo
        assert_eq!(rules[0].chain, "output");
        assert_eq!(rules[0].out_iface, "lo");

        // Last rule is INPUT drop
        let last = rules.last().unwrap();
        assert_eq!(last.chain, "input");
        assert_eq!(last.rule_type, "drop");
    }

    #[test]
    fn test_preset_kill_switch_no_wstunnel() {
        let db = test_db();
        preset_kill_switch(&db, 51820, 0, "wg0").unwrap();

        let group = db.get_rule_group("kill-switch").unwrap();
        let rules = db.firewall_rules_for_group(group.id).unwrap();
        // Without wstunnel: 10 rules (one less)
        assert_eq!(rules.len(), 10);
    }

    #[test]
    fn test_preset_dns_protection() {
        let db = test_db();
        preset_dns_protection(&db, "wg0").unwrap();

        let group = db.get_rule_group("dns-protection").unwrap();
        assert_eq!(group.group_type, "dns_protection");

        let rules = db.firewall_rules_for_group(group.id).unwrap();
        assert_eq!(rules.len(), 5);

        // All output chain
        for r in &rules {
            assert_eq!(r.chain, "output");
        }

        // First two are accept via wg0, last two are drop
        assert_eq!(rules[0].rule_type, "accept");
        assert_eq!(rules[0].out_iface, "wg0");
        assert_eq!(rules[3].rule_type, "drop");
        assert_eq!(rules[4].rule_type, "drop");
    }

    #[test]
    fn test_preset_ipv6_block() {
        let db = test_db();
        preset_ipv6_block(&db).unwrap();

        let group = db.get_rule_group("ipv6-block").unwrap();
        assert_eq!(group.group_type, "ipv6_block");
        assert_eq!(group.priority, 5); // highest priority

        let rules = db.firewall_rules_for_group(group.id).unwrap();
        assert_eq!(rules.len(), 3); // input + output + forward

        for r in &rules {
            assert_eq!(r.family, 10); // AF_INET6
            assert_eq!(r.rule_type, "drop");
        }
    }

    #[test]
    fn test_preset_metadata_stored() {
        let db = test_db();
        preset_vpn(&db, "meta-test", "wg0", 51820, "10.8.0.0/24", "eth0").unwrap();

        let group = db.get_rule_group("meta-test").unwrap();
        let meta: serde_json::Value = serde_json::from_str(&group.metadata).unwrap();
        assert_eq!(meta["preset"], "vpn");
        assert_eq!(meta["wg_port"], 51820);
        assert_eq!(meta["wg_iface"], "wg0");
    }
}
