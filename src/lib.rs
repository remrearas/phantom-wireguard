//! firewall-bridge-linux v2 — Stateful firewall and routing bridge.
//!
//! SQLite-backed state management with rule groups, presets, and crash recovery.
//! All operations go through nftables (libnftables) and netlink — zero subprocess calls.

mod db;
mod error;
mod nft;
mod presets;
mod route;
mod state;
mod verify;

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::ptr;
use std::sync::Mutex;

use error::ErrorCode;
use state::FirewallState;

const VERSION: &str = env!("CARGO_PKG_VERSION");

// ---------------------------------------------------------------------------
// Global singleton — all FFI calls go through this Mutex
// ---------------------------------------------------------------------------

static STATE: Mutex<FirewallState> = Mutex::new(FirewallState::new());

// ---------------------------------------------------------------------------
// Log callback — native Rust→Python bridge (mirrors wireguard-go-bridge)
// ---------------------------------------------------------------------------

/// Callback type: fn(level: i32, message: *const c_char, context: *mut c_void)
/// level: 0=error, 1=warning, 2=info, 3=debug
type LogCallbackFn = extern "C" fn(c_int, *const c_char, *mut c_void);

struct LogCallbackHolder {
    cb: LogCallbackFn,
    ctx: *mut c_void,
}

// Safety: the callback + context are set once from the main thread and only
// read under the mutex. The Python-managed context pointer is stable.
unsafe impl Send for LogCallbackHolder {}

static LOG_CALLBACK: Mutex<Option<LogCallbackHolder>> = Mutex::new(None);

fn emit_log(level: i32, msg: &str) {
    if let Ok(guard) = LOG_CALLBACK.lock() {
        if let Some(ref holder) = *guard {
            if let Ok(c_msg) = CString::new(msg) {
                (holder.cb)(level, c_msg.as_ptr(), holder.ctx);
            }
        }
    }
}

/// Log levels
pub const LOG_ERROR: i32 = 0;
pub const LOG_WARN: i32 = 1;
pub const LOG_INFO: i32 = 2;
pub const LOG_DEBUG: i32 = 3;

fn with_state<F, R>(f: F) -> R
where
    F: FnOnce(&mut FirewallState) -> R,
{
    let mut guard = STATE.lock().unwrap_or_else(|e| e.into_inner());
    f(&mut guard)
}

// ---------------------------------------------------------------------------
// C string helpers
// ---------------------------------------------------------------------------

/// Convert C string pointer to &str. Returns empty string if NULL.
unsafe fn cstr_to_str<'a>(ptr: *const c_char) -> &'a str {
    if ptr.is_null() {
        ""
    } else {
        CStr::from_ptr(ptr).to_str().unwrap_or("")
    }
}

/// Allocate a CString on heap and return raw pointer. Caller must free via free_string.
fn to_heap_cstring(s: &str) -> *mut c_char {
    CString::new(s).map(|c| c.into_raw()).unwrap_or(ptr::null_mut())
}

/// Return error code and set last_error message.
fn err_result(state: &mut FirewallState, code: ErrorCode, msg: &str) -> i32 {
    state.set_last_error(msg);
    code as i32
}

// ---------------------------------------------------------------------------
// v2 Lifecycle FFI
// ---------------------------------------------------------------------------

/// Initialize firewall bridge with SQLite database.
/// Auto-closes previous state if re-initialized (singleton safe).
#[no_mangle]
pub extern "C" fn firewall_bridge_init(db_path: *const c_char) -> i32 {
    let path = unsafe { cstr_to_str(db_path) };
    if path.is_empty() {
        return with_state(|s| err_result(s, ErrorCode::InvalidParam, "db_path is required"));
    }

    with_state(|s| match s.init(path) {
        Ok(()) => ErrorCode::Ok as i32,
        Err((code, msg)) => err_result(s, code, &msg),
    })
}

/// Get current status as JSON. Caller must free returned string.
#[no_mangle]
pub extern "C" fn firewall_bridge_get_status() -> *mut c_char {
    with_state(|s| to_heap_cstring(&s.get_status_json()))
}

/// Start: apply all enabled rule groups from DB to kernel.
#[no_mangle]
pub extern "C" fn firewall_bridge_start() -> i32 {
    with_state(|s| match s.start() {
        Ok(()) => ErrorCode::Ok as i32,
        Err((code, msg)) => err_result(s, code, &msg),
    })
}

/// Stop: flush all applied rules from kernel.
#[no_mangle]
pub extern "C" fn firewall_bridge_stop() -> i32 {
    with_state(|s| match s.stop() {
        Ok(()) => ErrorCode::Ok as i32,
        Err((code, msg)) => err_result(s, code, &msg),
    })
}

/// Close: stop if started, release all resources.
#[no_mangle]
pub extern "C" fn firewall_bridge_close() -> i32 {
    with_state(|s| match s.close() {
        Ok(()) => ErrorCode::Ok as i32,
        Err((code, msg)) => err_result(s, code, &msg),
    })
}

// ---------------------------------------------------------------------------
// v2 Rule Group FFI
// ---------------------------------------------------------------------------

/// Create a rule group. Returns JSON or NULL on error. Caller must free.
#[no_mangle]
pub extern "C" fn fw_create_rule_group(
    name: *const c_char,
    group_type: *const c_char,
    priority: i32,
) -> *mut c_char {
    let name_str = unsafe { cstr_to_str(name) };
    let type_str = unsafe { cstr_to_str(group_type) };
    if name_str.is_empty() {
        return ptr::null_mut();
    }

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        match db.create_rule_group(name_str, type_str, priority, "{}") {
            Ok(group) => to_heap_cstring(&serde_json::to_string(&group).unwrap_or_default()),
            Err(msg) => { s.set_last_error(&msg); ptr::null_mut() }
        }
    })
}

/// Delete a rule group and all its rules. If started, removes from kernel first.
#[no_mangle]
pub extern "C" fn fw_delete_rule_group(name: *const c_char) -> i32 {
    let name_str = unsafe { cstr_to_str(name) };
    if name_str.is_empty() {
        return ErrorCode::InvalidParam as i32;
    }

    with_state(|s| {
        // If started, disable group first (remove from kernel)
        if s.is_started() {
            let _ = disable_group_internal(s, name_str);
        }
        let db = match s.db() {
            Ok(db) => db,
            Err((code, msg)) => return err_result(s, code, &msg),
        };
        match db.delete_rule_group(name_str) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => err_result(s, ErrorCode::GroupNotFound, &msg),
        }
    })
}

/// Enable a rule group. If bridge is started, applies rules to kernel immediately.
#[no_mangle]
pub extern "C" fn fw_enable_rule_group(name: *const c_char) -> i32 {
    let name_str = unsafe { cstr_to_str(name) };
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((code, msg)) => return err_result(s, code, &msg),
        };
        if let Err(msg) = db.set_group_enabled(name_str, true) {
            return err_result(s, ErrorCode::GroupNotFound, &msg);
        }
        // If started, apply rules now
        if s.is_started() {
            if let Err(msg) = apply_group_rules(s, name_str) {
                return err_result(s, ErrorCode::NftablesFailed, &msg);
            }
        }
        ErrorCode::Ok as i32
    })
}

/// Disable a rule group. If bridge is started, removes rules from kernel.
#[no_mangle]
pub extern "C" fn fw_disable_rule_group(name: *const c_char) -> i32 {
    let name_str = unsafe { cstr_to_str(name) };
    with_state(|s| {
        if s.is_started() {
            let _ = disable_group_internal(s, name_str);
        }
        let db = match s.db() {
            Ok(db) => db,
            Err((code, msg)) => return err_result(s, code, &msg),
        };
        match db.set_group_enabled(name_str, false) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => err_result(s, ErrorCode::GroupNotFound, &msg),
        }
    })
}

/// List all rule groups as JSON. Caller must free.
#[no_mangle]
pub extern "C" fn fw_list_rule_groups() -> *mut c_char {
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ptr::null_mut(),
        };
        match db.list_rule_groups() {
            Ok(groups) => to_heap_cstring(&serde_json::to_string(&groups).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Get a single rule group by name as JSON. Caller must free.
#[no_mangle]
pub extern "C" fn fw_get_rule_group(name: *const c_char) -> *mut c_char {
    let name_str = unsafe { cstr_to_str(name) };
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ptr::null_mut(),
        };
        match db.get_rule_group(name_str) {
            Ok(group) => to_heap_cstring(&serde_json::to_string(&group).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

// ---------------------------------------------------------------------------
// Internal helpers for rule application
// ---------------------------------------------------------------------------

fn apply_group_rules(state: &FirewallState, group_name: &str) -> Result<(), String> {
    let db = state.db().map_err(|(_, m)| m)?;
    let nft_ctx = state.nft().map_err(|(_, m)| m)?;
    let group = db.get_rule_group(group_name)?;

    let rules = db.firewall_rules_for_group(group.id)?;
    for rule in &rules {
        match nft::apply_rule(nft_ctx, rule) {
            Ok(handle) => { let _ = db.update_fw_rule_applied(rule.id, true, handle as i64); }
            Err(e) => return Err(format!("Rule {}: {}", rule.id, e)),
        }
    }

    let rt_rules = db.routing_rules_for_group(group.id)?;
    for rule in &rt_rules {
        match route::apply_routing_rule(rule) {
            Ok(()) => { let _ = db.update_rt_rule_applied(rule.id, true); }
            Err(e) => return Err(format!("Routing rule {}: {}", rule.id, e)),
        }
    }
    Ok(())
}

fn disable_group_internal(state: &FirewallState, group_name: &str) -> Result<(), String> {
    let db = state.db().map_err(|(_, m)| m)?;
    let nft_ctx = state.nft().map_err(|(_, m)| m)?;
    let group = db.get_rule_group(group_name)?;

    // Remove firewall rules by handle
    let rules = db.firewall_rules_for_group(group.id)?;
    for rule in &rules {
        if rule.applied && rule.nft_handle > 0 {
            let _ = nft::remove_rule_by_handle(nft_ctx, &rule.chain, rule.nft_handle as u64);
        }
        let _ = db.update_fw_rule_applied(rule.id, false, 0);
    }

    // Remove routing rules
    let rt_rules = db.routing_rules_for_group(group.id)?;
    for rule in &rt_rules {
        if rule.applied {
            let _ = route::remove_routing_rule(rule);
        }
        let _ = db.update_rt_rule_applied(rule.id, false);
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// v2 Firewall Rule FFI
// ---------------------------------------------------------------------------

/// Add a firewall rule to a group. Returns rule_id (>0) or negative error.
/// If bridge is started and group is enabled, applies immediately.
#[no_mangle]
pub extern "C" fn fw_add_rule(
    group_name: *const c_char,
    chain: *const c_char,
    rule_type: *const c_char,
    family: u8,
    proto: *const c_char,
    dport: u16,
    source: *const c_char,
    destination: *const c_char,
    in_iface: *const c_char,
    out_iface: *const c_char,
    state_match: *const c_char,
) -> i64 {
    let gn = unsafe { cstr_to_str(group_name) };
    let ch = unsafe { cstr_to_str(chain) };
    let rt = unsafe { cstr_to_str(rule_type) };
    let pr = unsafe { cstr_to_str(proto) };
    let sr = unsafe { cstr_to_str(source) };
    let ds = unsafe { cstr_to_str(destination) };
    let ii = unsafe { cstr_to_str(in_iface) };
    let oi = unsafe { cstr_to_str(out_iface) };
    let sm = unsafe { cstr_to_str(state_match) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ErrorCode::NotInitialized as i64,
        };
        let group = match db.get_rule_group(gn) {
            Ok(g) => g,
            Err(_) => return ErrorCode::GroupNotFound as i64,
        };

        let position = db.firewall_rules_for_group(group.id)
            .map(|r| r.len() as i32)
            .unwrap_or(0);

        match db.insert_firewall_rule(
            group.id, ch, rt, family as i32, pr, dport as i32, 0,
            sr, ds, ii, oi, sm, "", position,
        ) {
            Ok(rule_id) => {
                // If started + group enabled, apply immediately
                if s.is_started() && group.enabled {
                    if let Ok(rule) = db.firewall_rules_for_group(group.id) {
                        if let Some(rule) = rule.iter().find(|r| r.id == rule_id) {
                            if let Ok(nft_ctx) = s.nft() {
                                if let Ok(handle) = nft::apply_rule(nft_ctx, rule) {
                                    let _ = db.update_fw_rule_applied(rule_id, true, handle as i64);
                                }
                            }
                        }
                    }
                }
                rule_id
            }
            Err(msg) => { s.set_last_error(&msg); ErrorCode::DbWrite as i64 }
        }
    })
}

/// Remove a firewall rule by ID.
#[no_mangle]
pub extern "C" fn fw_remove_rule(rule_id: i64) -> i32 {
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((code, msg)) => return err_result(s, code, &msg),
        };
        // If applied, remove from kernel first
        if let Ok(rules) = db.all_firewall_rules() {
            if let Some(rule) = rules.iter().find(|r| r.id == rule_id) {
                if rule.applied && rule.nft_handle > 0 {
                    if let Ok(nft_ctx) = s.nft() {
                        let _ = nft::remove_rule_by_handle(nft_ctx, &rule.chain, rule.nft_handle as u64);
                    }
                }
            }
        }
        match db.delete_firewall_rule(rule_id) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => err_result(s, ErrorCode::RuleNotFound, &msg),
        }
    })
}

/// List firewall rules as JSON. If group_name is NULL, list all. Caller must free.
#[no_mangle]
pub extern "C" fn fw_list_rules(group_name: *const c_char) -> *mut c_char {
    let gn = unsafe { cstr_to_str(group_name) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ptr::null_mut(),
        };
        let rules = if gn.is_empty() {
            db.all_firewall_rules()
        } else {
            match db.get_rule_group(gn) {
                Ok(group) => db.firewall_rules_for_group(group.id),
                Err(_) => return ptr::null_mut(),
            }
        };
        match rules {
            Ok(r) => to_heap_cstring(&serde_json::to_string(&r).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

// ---------------------------------------------------------------------------
// v2 Routing Rule FFI
// ---------------------------------------------------------------------------

/// Add a routing rule to a group. Returns rule_id or negative error.
#[no_mangle]
pub extern "C" fn rt_add_rule(
    group_name: *const c_char,
    rule_type: *const c_char,
    from_network: *const c_char,
    to_network: *const c_char,
    table_name: *const c_char,
    table_id: u32,
    priority: u32,
    destination: *const c_char,
    device: *const c_char,
    fwmark: u32,
) -> i64 {
    let gn = unsafe { cstr_to_str(group_name) };
    let rt = unsafe { cstr_to_str(rule_type) };
    let frm = unsafe { cstr_to_str(from_network) };
    let to = unsafe { cstr_to_str(to_network) };
    let tn = unsafe { cstr_to_str(table_name) };
    let dst = unsafe { cstr_to_str(destination) };
    let dev = unsafe { cstr_to_str(device) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ErrorCode::NotInitialized as i64,
        };
        let group = match db.get_rule_group(gn) {
            Ok(g) => g,
            Err(_) => return ErrorCode::GroupNotFound as i64,
        };
        match db.insert_routing_rule(
            group.id, rt, frm, to, tn, table_id as i32,
            priority as i32, dst, dev, fwmark as i32,
        ) {
            Ok(rule_id) => {
                if s.is_started() && group.enabled {
                    if let Ok(rule) = db.routing_rules_for_group(group.id) {
                        if let Some(rule) = rule.iter().find(|r| r.id == rule_id) {
                            if route::apply_routing_rule(rule).is_ok() {
                                let _ = db.update_rt_rule_applied(rule_id, true);
                            }
                        }
                    }
                }
                rule_id
            }
            Err(msg) => { s.set_last_error(&msg); ErrorCode::DbWrite as i64 }
        }
    })
}

/// Remove a routing rule by ID.
#[no_mangle]
pub extern "C" fn rt_remove_rule(rule_id: i64) -> i32 {
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((code, msg)) => return err_result(s, code, &msg),
        };
        if let Ok(rules) = db.applied_routing_rules() {
            if let Some(rule) = rules.iter().find(|r| r.id == rule_id) {
                if rule.applied {
                    let _ = route::remove_routing_rule(rule);
                }
            }
        }
        match db.delete_routing_rule(rule_id) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => err_result(s, ErrorCode::RuleNotFound, &msg),
        }
    })
}

/// List routing rules as JSON. Caller must free.
#[no_mangle]
pub extern "C" fn rt_list_rules(group_name: *const c_char) -> *mut c_char {
    let gn = unsafe { cstr_to_str(group_name) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err(_) => return ptr::null_mut(),
        };
        let rules = if gn.is_empty() {
            db.applied_routing_rules() // fallback: all applied
        } else {
            match db.get_rule_group(gn) {
                Ok(group) => db.routing_rules_for_group(group.id),
                Err(_) => return ptr::null_mut(),
            }
        };
        match rules {
            Ok(r) => to_heap_cstring(&serde_json::to_string(&r).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

// ---------------------------------------------------------------------------
// Utility FFI (v1 compat + v2 additions)
// ---------------------------------------------------------------------------

/// Set log callback for native Rust→Python log routing.
/// Pass NULL to disable logging.
#[no_mangle]
pub extern "C" fn firewall_bridge_set_log_callback(
    callback: Option<LogCallbackFn>,
    context: *mut c_void,
) {
    if let Ok(mut guard) = LOG_CALLBACK.lock() {
        match callback {
            Some(cb) => {
                *guard = Some(LogCallbackHolder { cb, ctx: context });
                // Can't emit_log here because we hold the lock
            }
            None => {
                *guard = None;
            }
        }
    }
}

/// Return version string (static, does not need to be freed).
#[no_mangle]
pub extern "C" fn firewall_bridge_get_version() -> *const c_char {
    use std::sync::OnceLock;
    static VERSION_CSTR: OnceLock<CString> = OnceLock::new();
    VERSION_CSTR
        .get_or_init(|| CString::new(VERSION).unwrap_or_default())
        .as_ptr()
}

/// Return the last error message (static buffer, does not need to be freed).
#[no_mangle]
pub extern "C" fn firewall_bridge_get_last_error() -> *const c_char {
    // Note: returns pointer into a static CString that persists until next call
    use std::sync::OnceLock;
    static LAST_ERR: Mutex<Option<CString>> = Mutex::new(None);

    with_state(|s| {
        let msg = s.last_error();
        if let Ok(mut guard) = LAST_ERR.lock() {
            *guard = CString::new(msg).ok();
            guard.as_ref().map(|c| c.as_ptr()).unwrap_or(ptr::null())
        } else {
            ptr::null()
        }
    })
}

/// Free a heap-allocated string returned by v2 JSON functions.
#[no_mangle]
pub extern "C" fn firewall_bridge_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe { drop(CString::from_raw(ptr)); }
    }
}

/// Flush route cache.
#[no_mangle]
pub extern "C" fn rt_flush_cache() -> i32 {
    match route::flush_cache() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => with_state(|s| err_result(s, ErrorCode::IoError, &msg)),
    }
}

/// Enable IPv4 forwarding.
#[no_mangle]
pub extern "C" fn rt_enable_ip_forward() -> i32 {
    match route::enable_ip_forward() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => with_state(|s| err_result(s, ErrorCode::IoError, &msg)),
    }
}

// ---------------------------------------------------------------------------
// v2 Preset FFI
// ---------------------------------------------------------------------------

/// Apply VPN basic preset. Returns rule group JSON or NULL. Caller must free.
#[no_mangle]
pub extern "C" fn fw_apply_preset_vpn(
    name: *const c_char,
    wg_iface: *const c_char,
    wg_port: u16,
    wg_subnet: *const c_char,
    out_iface: *const c_char,
) -> *mut c_char {
    let n = unsafe { cstr_to_str(name) };
    let wi = unsafe { cstr_to_str(wg_iface) };
    let ws = unsafe { cstr_to_str(wg_subnet) };
    let oi = unsafe { cstr_to_str(out_iface) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        if let Err((_, msg)) = presets::preset_vpn(db, n, wi, wg_port, ws, oi) {
            s.set_last_error(&msg);
            return ptr::null_mut();
        }
        // If started, apply immediately
        if s.is_started() {
            let _ = apply_group_rules(s, n);
        }
        match db.get_rule_group(n) {
            Ok(g) => to_heap_cstring(&serde_json::to_string(&g).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Apply multihop preset. Returns rule group JSON or NULL. Caller must free.
#[no_mangle]
pub extern "C" fn fw_apply_preset_multihop(
    name: *const c_char,
    in_iface: *const c_char,
    out_iface: *const c_char,
    fwmark: u32,
    table_id: u32,
    subnet: *const c_char,
) -> *mut c_char {
    let n = unsafe { cstr_to_str(name) };
    let ii = unsafe { cstr_to_str(in_iface) };
    let oi = unsafe { cstr_to_str(out_iface) };
    let sub = unsafe { cstr_to_str(subnet) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        if let Err((_, msg)) = presets::preset_multihop(db, n, ii, oi, fwmark, table_id, sub) {
            s.set_last_error(&msg);
            return ptr::null_mut();
        }
        if s.is_started() {
            let _ = apply_group_rules(s, n);
        }
        match db.get_rule_group(n) {
            Ok(g) => to_heap_cstring(&serde_json::to_string(&g).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Apply kill-switch preset. Returns rule group JSON or NULL. Caller must free.
#[no_mangle]
pub extern "C" fn fw_apply_preset_kill_switch(
    wg_port: u16,
    wstunnel_port: u16,
    wg_iface: *const c_char,
) -> *mut c_char {
    let wi = unsafe { cstr_to_str(wg_iface) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        if let Err((_, msg)) = presets::preset_kill_switch(db, wg_port, wstunnel_port, wi) {
            s.set_last_error(&msg);
            return ptr::null_mut();
        }
        if s.is_started() {
            let _ = apply_group_rules(s, "kill-switch");
        }
        match db.get_rule_group("kill-switch") {
            Ok(g) => to_heap_cstring(&serde_json::to_string(&g).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Apply DNS leak protection preset. Returns rule group JSON or NULL. Caller must free.
#[no_mangle]
pub extern "C" fn fw_apply_preset_dns_protection(wg_iface: *const c_char) -> *mut c_char {
    let wi = unsafe { cstr_to_str(wg_iface) };

    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        if let Err((_, msg)) = presets::preset_dns_protection(db, wi) {
            s.set_last_error(&msg);
            return ptr::null_mut();
        }
        if s.is_started() {
            let _ = apply_group_rules(s, "dns-protection");
        }
        match db.get_rule_group("dns-protection") {
            Ok(g) => to_heap_cstring(&serde_json::to_string(&g).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Apply IPv6 block preset. Returns rule group JSON or NULL. Caller must free.
#[no_mangle]
pub extern "C" fn fw_apply_preset_ipv6_block() -> *mut c_char {
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        if let Err((_, msg)) = presets::preset_ipv6_block(db) {
            s.set_last_error(&msg);
            return ptr::null_mut();
        }
        if s.is_started() {
            let _ = apply_group_rules(s, "ipv6-block");
        }
        match db.get_rule_group("ipv6-block") {
            Ok(g) => to_heap_cstring(&serde_json::to_string(&g).unwrap_or_default()),
            Err(_) => ptr::null_mut(),
        }
    })
}

/// Remove a preset by name: disable + delete.
#[no_mangle]
pub extern "C" fn fw_remove_preset(name: *const c_char) -> i32 {
    let n = unsafe { cstr_to_str(name) };
    // Reuse existing delete which handles kernel removal
    fw_delete_rule_group(name)
}

// ---------------------------------------------------------------------------
// v2 Verify FFI
// ---------------------------------------------------------------------------

/// Get actual kernel state (nft list table). Caller must free.
#[no_mangle]
pub extern "C" fn fw_get_kernel_state() -> *mut c_char {
    with_state(|s| {
        let nft_ctx = match s.nft() {
            Ok(n) => n,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        match verify::get_kernel_state(nft_ctx) {
            Ok(json) => to_heap_cstring(&json),
            Err(msg) => { s.set_last_error(&msg); ptr::null_mut() }
        }
    })
}

/// Verify DB rules against kernel state. Returns JSON drift report. Caller must free.
#[no_mangle]
pub extern "C" fn fw_verify_rules() -> *mut c_char {
    with_state(|s| {
        let db = match s.db() {
            Ok(db) => db,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        let nft_ctx = match s.nft() {
            Ok(n) => n,
            Err((_, msg)) => { s.set_last_error(&msg); return ptr::null_mut(); }
        };
        match verify::verify_rules(db, nft_ctx) {
            Ok(result) => to_heap_cstring(&serde_json::to_string(&result).unwrap_or_default()),
            Err(msg) => { s.set_last_error(&msg); ptr::null_mut() }
        }
    })
}

// ---------------------------------------------------------------------------
// v1 compat — kept for backward compatibility but route through v2 state
// ---------------------------------------------------------------------------

/// v1 init (no DB). For v2, use firewall_bridge_init(db_path) instead.
/// This creates a temporary in-memory DB for backward compat.
#[no_mangle]
pub extern "C" fn firewall_bridge_init_legacy() -> i32 {
    firewall_bridge_init(
        CString::new(":memory:").unwrap().as_ptr()
    )
}

/// v1 cleanup. Alias for firewall_bridge_close.
#[no_mangle]
pub extern "C" fn firewall_bridge_cleanup() {
    let _ = with_state(|s| s.close());
}

/// Flush all rules in the phantom table.
#[no_mangle]
pub extern "C" fn fw_flush_table() -> i32 {
    with_state(|s| {
        match s.nft() {
            Ok(nft_ctx) => match nft::flush_table(nft_ctx) {
                Ok(()) => ErrorCode::Ok as i32,
                Err(msg) => err_result(s, ErrorCode::NftablesFailed, &msg),
            },
            Err((code, msg)) => err_result(s, code, &msg),
        }
    })
}
