//! firewall-bridge-linux v2.1 — Kernel operations backend.
//!
//! Pure nftables + netlink operations. No database, no state machine.
//! State management, persistence, presets → Python side.
//! This is the kernel backend, like iptables-restore is to ufw.

mod error;
mod nft;
mod route;

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;
use std::sync::Mutex;

use error::ErrorCode;
use nft::NftContext;

const VERSION: &str = env!("CARGO_PKG_VERSION");

// ---------------------------------------------------------------------------
// Global nft context — serialized via Mutex
// ---------------------------------------------------------------------------

static NFT_CTX: Mutex<Option<NftContext>> = Mutex::new(None);
static LAST_ERROR: Mutex<Option<CString>> = Mutex::new(None);

fn with_nft<F, R>(f: F) -> R
where
    F: FnOnce(&NftContext) -> R,
{
    let guard = NFT_CTX.lock().unwrap_or_else(|e| e.into_inner());
    let ctx = guard.as_ref().expect("nft context not initialized");
    f(ctx)
}

fn set_last_error(msg: &str) {
    if let Ok(mut guard) = LAST_ERROR.lock() {
        *guard = CString::new(msg).ok();
    }
}

fn to_heap_cstring(s: &str) -> *mut c_char {
    CString::new(s).map(|c| c.into_raw()).unwrap_or(ptr::null_mut())
}

unsafe fn cstr_to_str<'a>(ptr: *const c_char) -> &'a str {
    if ptr.is_null() { "" }
    else { CStr::from_ptr(ptr).to_str().unwrap_or("") }
}

// ---------------------------------------------------------------------------
// nftables FFI
// ---------------------------------------------------------------------------

/// Initialize nft context and ensure phantom table + chains exist.
/// Must be called before any other nft_* function.
#[no_mangle]
pub extern "C" fn nft_init() -> i32 {
    let ctx = match NftContext::new() {
        Ok(c) => c,
        Err(msg) => {
            set_last_error(msg);
            return ErrorCode::NftablesFailed as i32;
        }
    };

    if let Err(msg) = nft::ensure_table(&ctx) {
        set_last_error(&msg);
        return ErrorCode::NftablesFailed as i32;
    }

    let mut guard = NFT_CTX.lock().unwrap_or_else(|e| e.into_inner());
    *guard = Some(ctx);
    ErrorCode::Ok as i32
}

/// Close nft context and release resources.
#[no_mangle]
pub extern "C" fn nft_close() {
    let mut guard = NFT_CTX.lock().unwrap_or_else(|e| e.into_inner());
    *guard = None;
}

/// Add a firewall rule to the phantom table. Returns nft handle (>0) or negative error.
#[no_mangle]
pub extern "C" fn nft_add_rule(
    chain: *const c_char,
    action: *const c_char,
    family: i32,
    proto: *const c_char,
    dport: i32,
    source: *const c_char,
    destination: *const c_char,
    in_iface: *const c_char,
    out_iface: *const c_char,
    state_match: *const c_char,
    comment: *const c_char,
) -> i64 {
    let ch = unsafe { cstr_to_str(chain) };
    let act = unsafe { cstr_to_str(action) };
    let pr = unsafe { cstr_to_str(proto) };
    let sr = unsafe { cstr_to_str(source) };
    let ds = unsafe { cstr_to_str(destination) };
    let ii = unsafe { cstr_to_str(in_iface) };
    let oi = unsafe { cstr_to_str(out_iface) };
    let sm = unsafe { cstr_to_str(state_match) };
    let cm = unsafe { cstr_to_str(comment) };

    with_nft(|ctx| {
        match nft::add_rule(ctx, ch, act, family, pr, dport, sr, ds, ii, oi, sm, cm) {
            Ok(handle) => handle as i64,
            Err(msg) => { set_last_error(&msg); ErrorCode::NftablesFailed as i64 }
        }
    })
}

/// Remove a firewall rule by chain + nft handle.
#[no_mangle]
pub extern "C" fn nft_remove_rule(chain: *const c_char, handle: u64) -> i32 {
    let ch = unsafe { cstr_to_str(chain) };
    with_nft(|ctx| {
        match nft::remove_rule(ctx, ch, handle) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => { set_last_error(&msg); ErrorCode::NftablesFailed as i32 }
        }
    })
}

/// Flush all rules in the phantom table (keeps chains).
#[no_mangle]
pub extern "C" fn nft_flush_table() -> i32 {
    with_nft(|ctx| {
        match nft::flush_table(ctx) {
            Ok(()) => ErrorCode::Ok as i32,
            Err(msg) => { set_last_error(&msg); ErrorCode::NftablesFailed as i32 }
        }
    })
}

/// List phantom table as JSON. Caller must free with firewall_bridge_free_string.
#[no_mangle]
pub extern "C" fn nft_list_table() -> *mut c_char {
    with_nft(|ctx| {
        match nft::list_table(ctx) {
            Ok(json) => to_heap_cstring(&json),
            Err(msg) => { set_last_error(&msg); ptr::null_mut() }
        }
    })
}

// ---------------------------------------------------------------------------
// Routing FFI
// ---------------------------------------------------------------------------

/// Ensure routing table entry in /etc/iproute2/rt_tables.
#[no_mangle]
pub extern "C" fn rt_table_ensure(table_id: u32, table_name: *const c_char) -> i32 {
    let name = unsafe { cstr_to_str(table_name) };
    match route::ensure_table(table_id, name) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::NetlinkFailed as i32 }
    }
}

/// Add a policy rule (ip rule add from ... table ... priority ...).
#[no_mangle]
pub extern "C" fn rt_policy_add(
    from_network: *const c_char,
    to_network: *const c_char,
    table_name: *const c_char,
    priority: u32,
) -> i32 {
    let frm = unsafe { cstr_to_str(from_network) };
    let to = unsafe { cstr_to_str(to_network) };
    let tn = unsafe { cstr_to_str(table_name) };

    match route::policy_add(frm, to, tn, priority) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::NetlinkFailed as i32 }
    }
}

/// Delete a policy rule.
#[no_mangle]
pub extern "C" fn rt_policy_delete(
    from_network: *const c_char,
    to_network: *const c_char,
    table_name: *const c_char,
    priority: u32,
) -> i32 {
    let frm = unsafe { cstr_to_str(from_network) };
    let to = unsafe { cstr_to_str(to_network) };
    let tn = unsafe { cstr_to_str(table_name) };

    match route::policy_delete(frm, to, tn, priority) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::NetlinkFailed as i32 }
    }
}

/// Add a route (ip route add ... dev ... table ...).
#[no_mangle]
pub extern "C" fn rt_route_add(
    destination: *const c_char,
    device: *const c_char,
    table_name: *const c_char,
) -> i32 {
    let dst = unsafe { cstr_to_str(destination) };
    let dev = unsafe { cstr_to_str(device) };
    let tn = unsafe { cstr_to_str(table_name) };

    match route::route_add(dst, dev, tn) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::NetlinkFailed as i32 }
    }
}

/// Delete a route.
#[no_mangle]
pub extern "C" fn rt_route_delete(
    destination: *const c_char,
    device: *const c_char,
    table_name: *const c_char,
) -> i32 {
    let dst = unsafe { cstr_to_str(destination) };
    let dev = unsafe { cstr_to_str(device) };
    let tn = unsafe { cstr_to_str(table_name) };

    match route::route_delete(dst, dev, tn) {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::NetlinkFailed as i32 }
    }
}

/// Enable IPv4 forwarding.
#[no_mangle]
pub extern "C" fn rt_enable_ip_forward() -> i32 {
    match route::enable_ip_forward() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::IoError as i32 }
    }
}

/// Flush route cache.
#[no_mangle]
pub extern "C" fn rt_flush_cache() -> i32 {
    match route::flush_cache() {
        Ok(()) => ErrorCode::Ok as i32,
        Err(msg) => { set_last_error(&msg); ErrorCode::IoError as i32 }
    }
}

// ---------------------------------------------------------------------------
// Utility FFI
// ---------------------------------------------------------------------------

/// Return version string (static, do NOT free).
#[no_mangle]
pub extern "C" fn firewall_bridge_get_version() -> *const c_char {
    use std::sync::OnceLock;
    static VERSION_CSTR: OnceLock<CString> = OnceLock::new();
    VERSION_CSTR
        .get_or_init(|| CString::new(VERSION).unwrap_or_default())
        .as_ptr()
}

/// Return last error message (static, do NOT free).
#[no_mangle]
pub extern "C" fn firewall_bridge_get_last_error() -> *const c_char {
    if let Ok(guard) = LAST_ERROR.lock() {
        guard.as_ref().map(|c| c.as_ptr()).unwrap_or(ptr::null())
    } else {
        ptr::null()
    }
}

/// Free a heap-allocated string returned by nft_list_table.
#[no_mangle]
pub extern "C" fn firewall_bridge_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe { drop(CString::from_raw(ptr)); }
    }
}
