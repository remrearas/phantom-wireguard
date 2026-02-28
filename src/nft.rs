//! nftables operations via libnftables C library.
//!
//! All firewall rules live in the `inet phantom` table.
//! This avoids conflicts with UFW, iptables, or any other rulesets.

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

use crate::error::ErrorCode;

// ---------------------------------------------------------------------------
// libnftables FFI bindings
// ---------------------------------------------------------------------------

#[allow(non_camel_case_types)]
enum nft_ctx {}

const NFT_CTX_DEFAULT: u32 = 0;
#[allow(dead_code)]
const NFT_CTX_OUTPUT_JSON: u32 = 1 << 4;
const NFT_CTX_OUTPUT_HANDLE: u32 = 1 << 3;

extern "C" {
    fn nft_ctx_new(flags: u32) -> *mut nft_ctx;
    fn nft_ctx_free(ctx: *mut nft_ctx);
    fn nft_ctx_buffer_output(ctx: *mut nft_ctx) -> i32;
    fn nft_ctx_buffer_error(ctx: *mut nft_ctx) -> i32;
    fn nft_ctx_get_output_buffer(ctx: *const nft_ctx) -> *const c_char;
    fn nft_ctx_get_error_buffer(ctx: *const nft_ctx) -> *const c_char;
    fn nft_run_cmd_from_buffer(ctx: *mut nft_ctx, buf: *const c_char) -> i32;
    fn nft_ctx_output_set_flags(ctx: *mut nft_ctx, flags: u32);
}

// ---------------------------------------------------------------------------
// NftContext — safe wrapper
// ---------------------------------------------------------------------------

pub struct NftContext {
    ctx: *mut nft_ctx,
}

// The nft_ctx is not thread-safe; we serialize access in lib.rs via Mutex.
unsafe impl Send for NftContext {}

impl NftContext {
    /// Create a new nftables context.
    pub fn new() -> Result<Self, ErrorCode> {
        let ctx = unsafe { nft_ctx_new(NFT_CTX_DEFAULT) };
        if ctx.is_null() {
            return Err(ErrorCode::NftablesFailed);
        }

        // Buffer output and error for programmatic access
        unsafe {
            nft_ctx_buffer_output(ctx);
            nft_ctx_buffer_error(ctx);
        }

        Ok(Self { ctx })
    }

    /// Execute an nft command string. Returns Ok(output) or Err with error message.
    pub fn run(&self, cmd: &str) -> Result<String, String> {
        let c_cmd = CString::new(cmd).map_err(|e| e.to_string())?;
        let rc = unsafe { nft_run_cmd_from_buffer(self.ctx, c_cmd.as_ptr()) };

        let output = self.get_output();
        let error = self.get_error();

        if rc != 0 {
            let msg = if error.is_empty() {
                format!("nft command failed (rc={}): {}", rc, cmd)
            } else {
                error
            };
            Err(msg)
        } else {
            Ok(output)
        }
    }

    /// Execute and return JSON output.
    pub fn run_json(&self, cmd: &str) -> Result<String, String> {
        unsafe {
            nft_ctx_output_set_flags(self.ctx, NFT_CTX_OUTPUT_JSON | NFT_CTX_OUTPUT_HANDLE);
        }
        let result = self.run(cmd);
        unsafe {
            nft_ctx_output_set_flags(self.ctx, NFT_CTX_OUTPUT_HANDLE);
        }
        result
    }

    fn get_output(&self) -> String {
        unsafe {
            let ptr = nft_ctx_get_output_buffer(self.ctx);
            if ptr.is_null() {
                String::new()
            } else {
                CStr::from_ptr(ptr).to_string_lossy().into_owned()
            }
        }
    }

    fn get_error(&self) -> String {
        unsafe {
            let ptr = nft_ctx_get_error_buffer(self.ctx);
            if ptr.is_null() {
                String::new()
            } else {
                CStr::from_ptr(ptr).to_string_lossy().into_owned()
            }
        }
    }
}

impl Drop for NftContext {
    fn drop(&mut self) {
        if !self.ctx.is_null() {
            unsafe { nft_ctx_free(self.ctx) };
            self.ctx = ptr::null_mut();
        }
    }
}

// ---------------------------------------------------------------------------
// Table name constant
// ---------------------------------------------------------------------------

const TABLE: &str = "inet phantom";

// ---------------------------------------------------------------------------
// High-level firewall operations
// ---------------------------------------------------------------------------

/// Ensure the phantom table and base chains exist.
pub fn ensure_table(nft: &NftContext) -> Result<(), String> {
    // Create table (idempotent with "add")
    nft.run(&format!("add table {TABLE}")).map(|_| ())?;

    // Base chains — "add" is idempotent; won't fail if they already exist
    nft.run(&format!(
        "add chain {TABLE} input {{ type filter hook input priority 0; policy accept; }}"
    )).map(|_| ())?;
    nft.run(&format!(
        "add chain {TABLE} forward {{ type filter hook forward priority 0; policy accept; }}"
    )).map(|_| ())?;
    nft.run(&format!(
        "add chain {TABLE} postrouting {{ type nat hook postrouting priority 100; policy accept; }}"
    )).map(|_| ())?;

    Ok(())
}

/// Build an nft match expression for source address.
/// Returns empty string if source is NULL or empty.
fn source_match(family: u8, source: &str) -> String {
    if source.is_empty() {
        return String::new();
    }
    let fam = if family == libc::AF_INET6 as u8 {
        "ip6"
    } else {
        "ip"
    };
    format!("{fam} saddr {source} ")
}

/// Build protocol + dport match expression.
fn proto_dport_match(proto: &str, dport: u16) -> String {
    if dport == 0 {
        return String::new();
    }
    format!("{proto} dport {dport} ")
}

// --- INPUT rules ---

pub fn add_input_accept(nft: &NftContext, family: u8, proto: &str, dport: u16, source: &str) -> Result<(), String> {
    let src = source_match(family, source);
    let pd = proto_dport_match(proto, dport);
    nft.run(&format!("add rule {TABLE} input {src}{pd}accept")).map(|_| ())
}

pub fn add_input_drop(nft: &NftContext, family: u8, proto: &str, dport: u16, source: &str) -> Result<(), String> {
    let src = source_match(family, source);
    let pd = proto_dport_match(proto, dport);
    nft.run(&format!("add rule {TABLE} input {src}{pd}drop")).map(|_| ())
}

pub fn del_input_rule(nft: &NftContext, family: u8, proto: &str, dport: u16, source: &str, action: &str) -> Result<(), String> {
    // To delete a specific rule, we need its handle.
    // Strategy: list rules as JSON, find matching rule handle, delete by handle.
    let rules_json = nft.run_json(&format!("list chain {TABLE} input"))?;
    if let Some(handle) = find_rule_handle(&rules_json, family, proto, dport, source, action, "input") {
        nft.run(&format!("delete rule {TABLE} input handle {handle}")).map(|_| ())
    } else {
        Err(format!("Rule not found: {} {} dport {} source {} {}",
            if family == libc::AF_INET6 as u8 { "ipv6" } else { "ipv4" },
            proto, dport, source, action))
    }
}

// --- FORWARD rules ---

pub fn add_forward(nft: &NftContext, in_iface: &str, out_iface: &str, state_match: &str) -> Result<(), String> {
    let iif = if in_iface.is_empty() { String::new() } else { format!("iifname \"{in_iface}\" ") };
    let oif = if out_iface.is_empty() { String::new() } else { format!("oifname \"{out_iface}\" ") };
    let ct = if state_match.is_empty() {
        String::new()
    } else {
        // Map iptables state names to nft conntrack: "RELATED,ESTABLISHED" -> "established,related"
        let nft_state = state_match.to_lowercase().replace("established", "established").replace("related", "related");
        format!("ct state {nft_state} ")
    };
    nft.run(&format!("add rule {TABLE} forward {iif}{oif}{ct}accept")).map(|_| ())
}

pub fn del_forward(nft: &NftContext, in_iface: &str, out_iface: &str, state_match: &str) -> Result<(), String> {
    let rules_json = nft.run_json(&format!("list chain {TABLE} forward"))?;
    if let Some(handle) = find_forward_handle(&rules_json, in_iface, out_iface, state_match) {
        nft.run(&format!("delete rule {TABLE} forward handle {handle}")).map(|_| ())
    } else {
        Err(format!("Forward rule not found: {} -> {} state={}", in_iface, out_iface, state_match))
    }
}

// --- NAT rules ---

pub fn add_nat_masquerade(nft: &NftContext, source_network: &str, out_iface: &str) -> Result<(), String> {
    let oif = if out_iface.is_empty() { String::new() } else { format!("oifname \"{out_iface}\" ") };
    nft.run(&format!("add rule {TABLE} postrouting ip saddr {source_network} {oif}masquerade")).map(|_| ())
}

pub fn del_nat_masquerade(nft: &NftContext, source_network: &str, out_iface: &str) -> Result<(), String> {
    let rules_json = nft.run_json(&format!("list chain {TABLE} postrouting"))?;
    if let Some(handle) = find_nat_handle(&rules_json, source_network, out_iface) {
        nft.run(&format!("delete rule {TABLE} postrouting handle {handle}")).map(|_| ())
    } else {
        Err(format!("NAT rule not found: {} via {}", source_network, out_iface))
    }
}

// --- Query & Control ---

pub fn list_rules(nft: &NftContext) -> Result<String, String> {
    nft.run_json(&format!("list table {TABLE}"))
}

pub fn flush_table(nft: &NftContext) -> Result<(), String> {
    nft.run(&format!("flush table {TABLE}")).map(|_| ())
}

// ---------------------------------------------------------------------------
// Rule handle lookup helpers (JSON parsing)
// ---------------------------------------------------------------------------

fn find_rule_handle(json: &str, family: u8, proto: &str, dport: u16, source: &str, action: &str, _chain: &str) -> Option<u64> {
    // Parse the JSON output from nft and find the matching rule's handle.
    let parsed: serde_json::Value = serde_json::from_str(json).ok()?;
    let nftables = parsed.get("nftables")?.as_array()?;

    for item in nftables {
        let rule = item.get("rule")?;
        let handle = rule.get("handle")?.as_u64()?;
        let expr = rule.get("expr")?.as_array()?;

        let mut matches_proto = proto.is_empty();
        let mut matches_dport = dport == 0;
        let mut matches_source = source.is_empty();
        let mut matches_action = false;

        let _fam = if family == libc::AF_INET6 as u8 { "ip6" } else { "ip" };

        for e in expr {
            // Check for protocol + dport match
            if let Some(m) = e.get("match") {
                if let Some(right) = m.get("right") {
                    if let Some(val) = right.as_u64() {
                        if val == dport as u64 {
                            matches_dport = true;
                        }
                    }
                    if let Some(val) = right.as_str() {
                        if val == source || val.contains(source) {
                            matches_source = true;
                        }
                    }
                }
                if let Some(left) = m.get("left") {
                    if let Some(payload) = left.get("payload") {
                        if payload.get("protocol").and_then(|p| p.as_str()) == Some(proto) {
                            matches_proto = true;
                        }
                    }
                    if let Some(meta) = left.get("meta") {
                        if meta.get("key").and_then(|k| k.as_str()) == Some("l4proto") {
                            matches_proto = true;
                        }
                    }
                }
            }
            // Check for action
            if e.get(action).is_some() {
                matches_action = true;
            }
        }

        if matches_proto && matches_dport && matches_source && matches_action {
            return Some(handle);
        }
    }

    // Fallback: iterate again without strict matching (best-effort)
    None
}

fn find_forward_handle(json: &str, in_iface: &str, out_iface: &str, state_match: &str) -> Option<u64> {
    let parsed: serde_json::Value = serde_json::from_str(json).ok()?;
    let nftables = parsed.get("nftables")?.as_array()?;

    for item in nftables {
        if let Some(rule) = item.get("rule") {
            let handle = rule.get("handle")?.as_u64()?;
            let rule_str = serde_json::to_string(rule).unwrap_or_default();

            let matches_iif = in_iface.is_empty() || rule_str.contains(in_iface);
            let matches_oif = out_iface.is_empty() || rule_str.contains(out_iface);
            let matches_state = state_match.is_empty() || rule_str.to_lowercase().contains(&state_match.to_lowercase());

            if matches_iif && matches_oif && matches_state {
                return Some(handle);
            }
        }
    }

    None
}

fn find_nat_handle(json: &str, source_network: &str, out_iface: &str) -> Option<u64> {
    let parsed: serde_json::Value = serde_json::from_str(json).ok()?;
    let nftables = parsed.get("nftables")?.as_array()?;

    for item in nftables {
        if let Some(rule) = item.get("rule") {
            let handle = rule.get("handle")?.as_u64()?;
            let rule_str = serde_json::to_string(rule).unwrap_or_default();

            let matches_src = source_network.is_empty() || rule_str.contains(source_network);
            let matches_oif = out_iface.is_empty() || rule_str.contains(out_iface);
            let has_masquerade = rule_str.contains("masquerade");

            if matches_src && matches_oif && has_masquerade {
                return Some(handle);
            }
        }
    }

    None
}