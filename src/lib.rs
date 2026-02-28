//! firewall-bridge-linux — Native firewall and routing bridge.
//!
//! Provides C ABI functions for:
//! - nftables firewall rules (INPUT, FORWARD, NAT)
//! - Routing policy rules and route table management
//!
//! All operations go through netlink — zero subprocess calls.

mod error;
mod nft;
mod route;

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use error::ErrorCode;
use nft::NftContext;

const VERSION: &str = env!("CARGO_PKG_VERSION");

// ---------------------------------------------------------------------------
// Global state
// ---------------------------------------------------------------------------

static INITIALIZED: AtomicBool = AtomicBool::new(false);
static NFT_CTX: Mutex<Option<NftContext>> = Mutex::new(None);
static LAST_ERROR: Mutex<Option<CString>> = Mutex::new(None);

fn set_last_error(msg: &str) {
    if let Ok(mut guard) = LAST_ERROR.lock() {
        *guard = CString::new(msg).ok();
    }
}

fn with_nft<F>(f: F) -> i32
where
    F: FnOnce(&NftContext) -> Result<(), String>,
{
    if !INITIALIZED.load(Ordering::SeqCst) {
        set_last_error("Not initialized — call firewall_bridge_init() first");
        return ErrorCode::NotInitialized as i32;
    }

    let guard = match NFT_CTX.lock() {
        Ok(g) => g,
        Err(e) => {
            set_last_error(&format!("Lock poisoned: {}", e));
            return ErrorCode::NftablesFailed as i32;
        }
    };

    match guard.as_ref() {
        Some(ctx) => match f(ctx) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => {
                set_last_error(&msg);
                ErrorCode::NftablesFailed as i32
            }
        },
        None => {
            set_last_error("nftables context not available");
            ErrorCode::NotInitialized as i32
        }
    }
}

/// Convert C string pointer to &str. Returns empty string if NULL.
unsafe fn cstr_to_str<'a>(ptr: *const c_char) -> &'a str {
    if ptr.is_null() {
        ""
    } else {
        CStr::from_ptr(ptr).to_str().unwrap_or("")
    }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

/// Initialize the firewall bridge. Creates nftables context and ensures
/// the phantom table + base chains exist.
#[no_mangle]
pub extern "C" fn firewall_bridge_init() -> i32 {
    if INITIALIZED.load(Ordering::SeqCst) {
        set_last_error("Already initialized");
        return ErrorCode::AlreadyInitialized as i32;
    }

    // Create nftables context
    let ctx = match NftContext::new() {
        Ok(c) => c,
        Err(e) => {
            set_last_error(&format!("Failed to create nftables context: {}", e));
            return ErrorCode::NftablesFailed as i32;
        }
    };

    // Ensure phantom table and chains exist
    if let Err(msg) = nft::ensure_table(&ctx) {
        set_last_error(&format!("Failed to create phantom table: {}", msg));
        return ErrorCode::NftablesFailed as i32;
    }

    // Store context
    if let Ok(mut guard) = NFT_CTX.lock() {
        *guard = Some(ctx);
    }

    INITIALIZED.store(true, Ordering::SeqCst);
    ErrorCode::Ok as i32
}

/// Cleanup and release all resources.
#[no_mangle]
pub extern "C" fn firewall_bridge_cleanup() {
    if let Ok(mut guard) = NFT_CTX.lock() {
        *guard = None;
    }
    INITIALIZED.store(false, Ordering::SeqCst);
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

/// Return the last error message, or NULL if no error.
#[no_mangle]
pub extern "C" fn firewall_bridge_get_last_error() -> *const c_char {
    match LAST_ERROR.lock() {
        Ok(guard) => guard.as_ref()
            .map(|s| s.as_ptr())
            .unwrap_or(ptr::null()),
        Err(_) => ptr::null(),
    }
}

// ---------------------------------------------------------------------------
// Firewall — INPUT rules
// ---------------------------------------------------------------------------

/// Add an INPUT ACCEPT rule.
/// family: AF_INET (2) or AF_INET6 (10)
/// proto: "tcp" or "udp"
/// dport: destination port (0 = any)
/// source: source address/network or NULL for any
#[no_mangle]
pub extern "C" fn fw_add_input_accept(
    family: u8,
    proto: *const c_char,
    dport: u16,
    source: *const c_char,
) -> i32 {
    let proto_str = unsafe { cstr_to_str(proto) };
    let source_str = unsafe { cstr_to_str(source) };

    with_nft(|ctx| nft::add_input_accept(ctx, family, proto_str, dport, source_str))
}

/// Add an INPUT DROP rule.
#[no_mangle]
pub extern "C" fn fw_add_input_drop(
    family: u8,
    proto: *const c_char,
    dport: u16,
    source: *const c_char,
) -> i32 {
    let proto_str = unsafe { cstr_to_str(proto) };
    let source_str = unsafe { cstr_to_str(source) };

    with_nft(|ctx| nft::add_input_drop(ctx, family, proto_str, dport, source_str))
}

/// Delete an INPUT rule by match criteria.
/// action: "accept" or "drop"
#[no_mangle]
pub extern "C" fn fw_del_input(
    family: u8,
    proto: *const c_char,
    dport: u16,
    source: *const c_char,
    action: *const c_char,
) -> i32 {
    let proto_str = unsafe { cstr_to_str(proto) };
    let source_str = unsafe { cstr_to_str(source) };
    let action_str = unsafe { cstr_to_str(action) };

    with_nft(|ctx| nft::del_input_rule(ctx, family, proto_str, dport, source_str, action_str))
}

// ---------------------------------------------------------------------------
// Firewall — FORWARD rules
// ---------------------------------------------------------------------------

/// Add a FORWARD ACCEPT rule.
/// in_iface: input interface name (or NULL for any)
/// out_iface: output interface name (or NULL for any)
/// state_match: conntrack state match, e.g. "established,related" (or NULL for none)
#[no_mangle]
pub extern "C" fn fw_add_forward(
    in_iface: *const c_char,
    out_iface: *const c_char,
    state_match: *const c_char,
) -> i32 {
    let in_str = unsafe { cstr_to_str(in_iface) };
    let out_str = unsafe { cstr_to_str(out_iface) };
    let state_str = unsafe { cstr_to_str(state_match) };

    with_nft(|ctx| nft::add_forward(ctx, in_str, out_str, state_str))
}

/// Delete a FORWARD rule.
#[no_mangle]
pub extern "C" fn fw_del_forward(
    in_iface: *const c_char,
    out_iface: *const c_char,
    state_match: *const c_char,
) -> i32 {
    let in_str = unsafe { cstr_to_str(in_iface) };
    let out_str = unsafe { cstr_to_str(out_iface) };
    let state_str = unsafe { cstr_to_str(state_match) };

    with_nft(|ctx| nft::del_forward(ctx, in_str, out_str, state_str))
}

// ---------------------------------------------------------------------------
// Firewall — NAT rules
// ---------------------------------------------------------------------------

/// Add a NAT MASQUERADE rule in POSTROUTING chain.
#[no_mangle]
pub extern "C" fn fw_add_nat_masquerade(
    source_network: *const c_char,
    out_iface: *const c_char,
) -> i32 {
    let src = unsafe { cstr_to_str(source_network) };
    let oif = unsafe { cstr_to_str(out_iface) };

    if src.is_empty() {
        set_last_error("source_network is required");
        return ErrorCode::InvalidParam as i32;
    }

    with_nft(|ctx| nft::add_nat_masquerade(ctx, src, oif))
}

/// Delete a NAT MASQUERADE rule.
#[no_mangle]
pub extern "C" fn fw_del_nat_masquerade(
    source_network: *const c_char,
    out_iface: *const c_char,
) -> i32 {
    let src = unsafe { cstr_to_str(source_network) };
    let oif = unsafe { cstr_to_str(out_iface) };

    with_nft(|ctx| nft::del_nat_masquerade(ctx, src, oif))
}

// ---------------------------------------------------------------------------
// Firewall — Query & Control
// ---------------------------------------------------------------------------

/// List all rules in the phantom table as JSON.
/// Returns a pointer to a JSON string. The string is valid until the
/// next call to fw_list_rules or firewall_bridge_cleanup.
#[no_mangle]
pub extern "C" fn fw_list_rules() -> *const c_char {
    static LIST_RESULT: Mutex<Option<CString>> = Mutex::new(None);

    if !INITIALIZED.load(Ordering::SeqCst) {
        return ptr::null();
    }

    let guard = match NFT_CTX.lock() {
        Ok(g) => g,
        Err(_) => return ptr::null(),
    };

    let result = match guard.as_ref() {
        Some(ctx) => nft::list_rules(ctx),
        None => return ptr::null(),
    };

    match result {
        Ok(json) => {
            if let Ok(mut lr) = LIST_RESULT.lock() {
                *lr = CString::new(json).ok();
                return lr.as_ref()
                    .map(|s| s.as_ptr())
                    .unwrap_or(ptr::null());
            }
            ptr::null()
        }
        Err(msg) => {
            set_last_error(&msg);
            ptr::null()
        }
    }
}

/// Flush all rules in the phantom table (keeps table and chains).
#[no_mangle]
pub extern "C" fn fw_flush_table() -> i32 {
    with_nft(|ctx| nft::flush_table(ctx))
}

// ---------------------------------------------------------------------------
// Routing — Policy rules
// ---------------------------------------------------------------------------

/// Add a policy rule: ip rule add from <from> [to <to>] table <table> priority <prio>
/// to_network can be NULL or empty for no destination match.
#[no_mangle]
pub extern "C" fn rt_add_policy(
    from_network: *const c_char,
    to_network: *const c_char,
    table_name: *const c_char,
    priority: u32,
) -> i32 {
    let from = unsafe { cstr_to_str(from_network) };
    let to = unsafe { cstr_to_str(to_network) };
    let table = unsafe { cstr_to_str(table_name) };

    if from.is_empty() || table.is_empty() {
        set_last_error("from_network and table_name are required");
        return ErrorCode::InvalidParam as i32;
    }

    match route::policy_add(from, to, table, priority) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::NetlinkFailed as i32
        }
    }
}

/// Delete a policy rule.
#[no_mangle]
pub extern "C" fn rt_del_policy(
    from_network: *const c_char,
    to_network: *const c_char,
    table_name: *const c_char,
    priority: u32,
) -> i32 {
    let from = unsafe { cstr_to_str(from_network) };
    let to = unsafe { cstr_to_str(to_network) };
    let table = unsafe { cstr_to_str(table_name) };

    if from.is_empty() || table.is_empty() {
        set_last_error("from_network and table_name are required");
        return ErrorCode::InvalidParam as i32;
    }

    match route::policy_delete(from, to, table, priority) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::NetlinkFailed as i32
        }
    }
}

// ---------------------------------------------------------------------------
// Routing — Routes
// ---------------------------------------------------------------------------

/// Add a route: ip route add <destination> dev <device> table <table>
/// Use "default" as destination for default route.
#[no_mangle]
pub extern "C" fn rt_add_route(
    destination: *const c_char,
    device: *const c_char,
    table_name: *const c_char,
) -> i32 {
    let dest = unsafe { cstr_to_str(destination) };
    let dev = unsafe { cstr_to_str(device) };
    let table = unsafe { cstr_to_str(table_name) };

    if dest.is_empty() || dev.is_empty() || table.is_empty() {
        set_last_error("destination, device, and table_name are required");
        return ErrorCode::InvalidParam as i32;
    }

    match route::route_add(dest, dev, table) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::NetlinkFailed as i32
        }
    }
}

/// Delete a route.
#[no_mangle]
pub extern "C" fn rt_del_route(
    destination: *const c_char,
    device: *const c_char,
    table_name: *const c_char,
) -> i32 {
    let dest = unsafe { cstr_to_str(destination) };
    let dev = unsafe { cstr_to_str(device) };
    let table = unsafe { cstr_to_str(table_name) };

    if dest.is_empty() || dev.is_empty() || table.is_empty() {
        set_last_error("destination, device, and table_name are required");
        return ErrorCode::InvalidParam as i32;
    }

    match route::route_delete(dest, dev, table) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::NetlinkFailed as i32
        }
    }
}

// ---------------------------------------------------------------------------
// Routing — Table management
// ---------------------------------------------------------------------------

/// Ensure a routing table entry exists in /etc/iproute2/rt_tables.
#[no_mangle]
pub extern "C" fn rt_ensure_table(
    table_id: u32,
    table_name: *const c_char,
) -> i32 {
    let name = unsafe { cstr_to_str(table_name) };

    if name.is_empty() {
        set_last_error("table_name is required");
        return ErrorCode::InvalidParam as i32;
    }

    match route::ensure_table(table_id, name) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::IoError as i32
        }
    }
}

/// Flush route cache.
#[no_mangle]
pub extern "C" fn rt_flush_cache() -> i32 {
    match route::flush_cache() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::IoError as i32
        }
    }
}

/// Enable IPv4 forwarding (/proc/sys/net/ipv4/ip_forward).
#[no_mangle]
pub extern "C" fn rt_enable_ip_forward() -> i32 {
    match route::enable_ip_forward() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => {
            set_last_error(&msg);
            ErrorCode::IoError as i32
        }
    }
}