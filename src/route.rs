//! Routing operations via raw netlink sockets.
//!
//! Handles policy rules (ip rule add/del) and routes (ip route add/del)
//! without any subprocess calls — direct kernel communication.

use std::io;
use std::mem;
use std::net::Ipv4Addr;
use std::str::FromStr;

use crate::error::ErrorCode;

// ---------------------------------------------------------------------------
// Netlink constants (from linux/netlink.h, linux/rtnetlink.h)
// ---------------------------------------------------------------------------

const NETLINK_ROUTE: libc::c_int = 0;

// Message types
const RTM_NEWROUTE: u16 = 24;
const RTM_DELROUTE: u16 = 25;
const RTM_NEWRULE: u16 = 32;
const RTM_DELRULE: u16 = 33;

// Flags
const NLM_F_REQUEST: u16 = 0x0001;
const NLM_F_ACK: u16 = 0x0004;
const NLM_F_CREATE: u16 = 0x0400;
const NLM_F_EXCL: u16 = 0x0200;

// Route/Rule attribute types
const RTA_DST: u16 = 1;
const RTA_OIF: u16 = 4;
const RTA_TABLE: u16 = 15;
const FRA_SRC: u16 = 2;
const FRA_DST: u16 = 1;
const FRA_TABLE: u16 = 15;
const FRA_PRIORITY: u16 = 6;

// Route types
const RTN_UNICAST: u8 = 1;

// Route protocols
const RTPROT_STATIC: u8 = 4;

// Route scope
const RT_SCOPE_UNIVERSE: u8 = 0;
const RT_SCOPE_LINK: u8 = 253;

// FIB rule action
const FR_ACT_TO_TBL: u8 = 1;

// ---------------------------------------------------------------------------
// Netlink message structures
// ---------------------------------------------------------------------------

#[repr(C)]
struct NlMsgHdr {
    nlmsg_len: u32,
    nlmsg_type: u16,
    nlmsg_flags: u16,
    nlmsg_seq: u32,
    nlmsg_pid: u32,
}

#[repr(C)]
struct RtMsg {
    rtm_family: u8,
    rtm_dst_len: u8,
    rtm_src_len: u8,
    rtm_tos: u8,
    rtm_table: u8,
    rtm_protocol: u8,
    rtm_scope: u8,
    rtm_type: u8,
    rtm_flags: u32,
}

#[repr(C)]
struct FibRuleHdr {
    family: u8,
    dst_len: u8,
    src_len: u8,
    tos: u8,
    table: u8,
    res1: u8,
    res2: u8,
    action: u8,
    flags: u32,
}

#[repr(C)]
struct RtAttr {
    rta_len: u16,
    rta_type: u16,
}

// ---------------------------------------------------------------------------
// Netlink socket helper
// ---------------------------------------------------------------------------

struct NetlinkSocket {
    fd: i32,
    seq: u32,
}

impl NetlinkSocket {
    fn open() -> Result<Self, ErrorCode> {
        let fd = unsafe {
            libc::socket(
                libc::AF_NETLINK,
                libc::SOCK_RAW | libc::SOCK_CLOEXEC,
                NETLINK_ROUTE,
            )
        };
        if fd < 0 {
            return Err(if unsafe { *libc::__errno_location() } == libc::EPERM {
                ErrorCode::PermissionDenied
            } else {
                ErrorCode::NetlinkFailed
            });
        }

        // Bind to kernel
        let mut addr: libc::sockaddr_nl = unsafe { mem::zeroed() };
        addr.nl_family = libc::AF_NETLINK as u16;
        addr.nl_pid = 0; // let kernel assign

        let rc = unsafe {
            libc::bind(
                fd,
                &addr as *const libc::sockaddr_nl as *const libc::sockaddr,
                mem::size_of::<libc::sockaddr_nl>() as u32,
            )
        };
        if rc < 0 {
            unsafe { libc::close(fd) };
            return Err(ErrorCode::NetlinkFailed);
        }

        Ok(Self { fd, seq: 1 })
    }

    fn next_seq(&mut self) -> u32 {
        let s = self.seq;
        self.seq += 1;
        s
    }

    /// Send a netlink message and wait for ACK.
    fn send_and_ack(&mut self, buf: &[u8]) -> Result<(), String> {
        let sent = unsafe {
            libc::send(self.fd, buf.as_ptr() as *const libc::c_void, buf.len(), 0)
        };
        if sent < 0 {
            return Err(format!("netlink send failed: {}", io::Error::last_os_error()));
        }

        // Read ACK
        let mut recv_buf = [0u8; 4096];
        let len = unsafe {
            libc::recv(self.fd, recv_buf.as_mut_ptr() as *mut libc::c_void, recv_buf.len(), 0)
        };
        if len < 0 {
            return Err(format!("netlink recv failed: {}", io::Error::last_os_error()));
        }

        // Parse ACK — check for NLMSG_ERROR
        if len >= mem::size_of::<NlMsgHdr>() as isize {
            let hdr = unsafe { &*(recv_buf.as_ptr() as *const NlMsgHdr) };
            if hdr.nlmsg_type == libc::NLMSG_ERROR as u16 {
                // Error payload: i32 error code after nlmsghdr
                if len >= (mem::size_of::<NlMsgHdr>() + 4) as isize {
                    let err = unsafe {
                        *(recv_buf.as_ptr().add(mem::size_of::<NlMsgHdr>()) as *const i32)
                    };
                    if err != 0 {
                        return Err(format!("netlink error: {}", io::Error::from_raw_os_error(-err)));
                    }
                }
            }
        }

        Ok(())
    }
}

impl Drop for NetlinkSocket {
    fn drop(&mut self) {
        if self.fd >= 0 {
            unsafe { libc::close(self.fd) };
            self.fd = -1;
        }
    }
}

// ---------------------------------------------------------------------------
// Message builder helpers
// ---------------------------------------------------------------------------

fn align4(len: usize) -> usize {
    (len + 3) & !3
}

fn push_attr(buf: &mut Vec<u8>, rta_type: u16, data: &[u8]) {
    let rta_len = (mem::size_of::<RtAttr>() + data.len()) as u16;
    buf.extend_from_slice(&rta_len.to_ne_bytes());
    buf.extend_from_slice(&rta_type.to_ne_bytes());
    buf.extend_from_slice(data);
    // Pad to 4-byte alignment
    let padded = align4(rta_len as usize);
    for _ in 0..(padded - rta_len as usize) {
        buf.push(0);
    }
}

fn push_attr_u32(buf: &mut Vec<u8>, rta_type: u16, val: u32) {
    push_attr(buf, rta_type, &val.to_ne_bytes());
}

/// Parse "10.66.66.0/24" into (Ipv4Addr, prefix_len).
fn parse_network(network: &str) -> Result<(Ipv4Addr, u8), String> {
    let parts: Vec<&str> = network.split('/').collect();
    if parts.len() != 2 {
        return Err(format!("Invalid network format: {}", network));
    }
    let addr = Ipv4Addr::from_str(parts[0])
        .map_err(|e| format!("Invalid IP address: {}", e))?;
    let prefix: u8 = parts[1].parse()
        .map_err(|e| format!("Invalid prefix length: {}", e))?;
    Ok((addr, prefix))
}

/// Resolve interface name to ifindex.
fn if_nametoindex(name: &str) -> Result<u32, String> {
    let c_name = std::ffi::CString::new(name).map_err(|e| e.to_string())?;
    let idx = unsafe { libc::if_nametoindex(c_name.as_ptr()) };
    if idx == 0 {
        Err(format!("Interface not found: {}", name))
    } else {
        Ok(idx)
    }
}

/// Resolve named routing table to numeric ID.
/// Reads /etc/iproute2/rt_tables for name→id mapping.
fn resolve_table(table_name: &str) -> Result<u32, String> {
    // Built-in tables
    match table_name {
        "default" => return Ok(253),
        "main" => return Ok(254),
        "local" => return Ok(255),
        "unspec" => return Ok(0),
        _ => {}
    }

    // Try numeric
    if let Ok(n) = table_name.parse::<u32>() {
        return Ok(n);
    }

    // Read rt_tables file
    let content = std::fs::read_to_string("/etc/iproute2/rt_tables")
        .map_err(|e| format!("Cannot read rt_tables: {}", e))?;

    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 && parts[1] == table_name {
            return parts[0].parse::<u32>()
                .map_err(|e| format!("Invalid table ID in rt_tables: {}", e));
        }
    }

    Err(format!("Routing table not found: {}", table_name))
}

// ---------------------------------------------------------------------------
// Public routing operations
// ---------------------------------------------------------------------------

/// Add a policy rule: ip rule add from <from> [to <to>] table <table> priority <prio>
pub fn policy_add(from_network: &str, to_network: &str, table_name: &str, priority: u32) -> Result<(), String> {
    let mut sock = NetlinkSocket::open().map_err(|e| e.to_string())?;
    let seq = sock.next_seq();
    let table_id = resolve_table(table_name)?;

    let (from_addr, from_prefix) = parse_network(from_network)?;

    let mut buf = Vec::with_capacity(256);

    // Reserve space for nlmsghdr (will fill in later)
    buf.extend_from_slice(&[0u8; mem::size_of::<NlMsgHdr>()]);

    // FIB rule header
    let fib = FibRuleHdr {
        family: libc::AF_INET as u8,
        dst_len: 0,
        src_len: from_prefix,
        tos: 0,
        table: if table_id <= 255 { table_id as u8 } else { 0 },
        res1: 0,
        res2: 0,
        action: FR_ACT_TO_TBL,
        flags: 0,
    };
    let fib_bytes = unsafe {
        std::slice::from_raw_parts(&fib as *const FibRuleHdr as *const u8, mem::size_of::<FibRuleHdr>())
    };
    buf.extend_from_slice(fib_bytes);

    // Source address attribute
    push_attr(&mut buf, FRA_SRC, &from_addr.octets());

    // Destination if provided
    if !to_network.is_empty() {
        let (to_addr, to_prefix) = parse_network(to_network)?;
        push_attr(&mut buf, FRA_DST, &to_addr.octets());
        // Update dst_len in the header
        let dst_len_offset = mem::size_of::<NlMsgHdr>() + 1; // offset of dst_len in FibRuleHdr
        buf[dst_len_offset] = to_prefix;
    }

    // Table attribute (for table IDs > 255)
    if table_id > 255 {
        push_attr_u32(&mut buf, FRA_TABLE, table_id);
    }

    // Priority
    push_attr_u32(&mut buf, FRA_PRIORITY, priority);

    // Fill in nlmsghdr
    let total_len = buf.len() as u32;
    let hdr = NlMsgHdr {
        nlmsg_len: total_len,
        nlmsg_type: RTM_NEWRULE,
        nlmsg_flags: NLM_F_REQUEST | NLM_F_ACK | NLM_F_CREATE | NLM_F_EXCL,
        nlmsg_seq: seq,
        nlmsg_pid: 0,
    };
    let hdr_bytes = unsafe {
        std::slice::from_raw_parts(&hdr as *const NlMsgHdr as *const u8, mem::size_of::<NlMsgHdr>())
    };
    buf[..mem::size_of::<NlMsgHdr>()].copy_from_slice(hdr_bytes);

    sock.send_and_ack(&buf)
}

/// Delete a policy rule.
pub fn policy_delete(from_network: &str, to_network: &str, table_name: &str, priority: u32) -> Result<(), String> {
    let mut sock = NetlinkSocket::open().map_err(|e| e.to_string())?;
    let seq = sock.next_seq();
    let table_id = resolve_table(table_name)?;

    let (from_addr, from_prefix) = parse_network(from_network)?;

    let mut buf = Vec::with_capacity(256);
    buf.extend_from_slice(&[0u8; mem::size_of::<NlMsgHdr>()]);

    let fib = FibRuleHdr {
        family: libc::AF_INET as u8,
        dst_len: 0,
        src_len: from_prefix,
        tos: 0,
        table: if table_id <= 255 { table_id as u8 } else { 0 },
        res1: 0,
        res2: 0,
        action: FR_ACT_TO_TBL,
        flags: 0,
    };
    let fib_bytes = unsafe {
        std::slice::from_raw_parts(&fib as *const FibRuleHdr as *const u8, mem::size_of::<FibRuleHdr>())
    };
    buf.extend_from_slice(fib_bytes);

    push_attr(&mut buf, FRA_SRC, &from_addr.octets());

    if !to_network.is_empty() {
        let (to_addr, to_prefix) = parse_network(to_network)?;
        push_attr(&mut buf, FRA_DST, &to_addr.octets());
        let dst_len_offset = mem::size_of::<NlMsgHdr>() + 1;
        buf[dst_len_offset] = to_prefix;
    }

    if table_id > 255 {
        push_attr_u32(&mut buf, FRA_TABLE, table_id);
    }

    push_attr_u32(&mut buf, FRA_PRIORITY, priority);

    let total_len = buf.len() as u32;
    let hdr = NlMsgHdr {
        nlmsg_len: total_len,
        nlmsg_type: RTM_DELRULE,
        nlmsg_flags: NLM_F_REQUEST | NLM_F_ACK,
        nlmsg_seq: seq,
        nlmsg_pid: 0,
    };
    let hdr_bytes = unsafe {
        std::slice::from_raw_parts(&hdr as *const NlMsgHdr as *const u8, mem::size_of::<NlMsgHdr>())
    };
    buf[..mem::size_of::<NlMsgHdr>()].copy_from_slice(hdr_bytes);

    sock.send_and_ack(&buf)
}

/// Add a route: ip route add <destination> dev <device> table <table>
/// Use "default" as destination for default route (0.0.0.0/0).
pub fn route_add(destination: &str, device: &str, table_name: &str) -> Result<(), String> {
    let mut sock = NetlinkSocket::open().map_err(|e| e.to_string())?;
    let seq = sock.next_seq();
    let table_id = resolve_table(table_name)?;
    let ifindex = if_nametoindex(device)?;

    let (dst_addr, dst_prefix) = if destination == "default" || destination == "0.0.0.0/0" {
        (Ipv4Addr::new(0, 0, 0, 0), 0u8)
    } else {
        parse_network(destination)?
    };

    let mut buf = Vec::with_capacity(256);
    buf.extend_from_slice(&[0u8; mem::size_of::<NlMsgHdr>()]);

    let rtm = RtMsg {
        rtm_family: libc::AF_INET as u8,
        rtm_dst_len: dst_prefix,
        rtm_src_len: 0,
        rtm_tos: 0,
        rtm_table: if table_id <= 255 { table_id as u8 } else { 0 },
        rtm_protocol: RTPROT_STATIC,
        rtm_scope: if dst_prefix == 0 { RT_SCOPE_UNIVERSE } else { RT_SCOPE_LINK },
        rtm_type: RTN_UNICAST,
        rtm_flags: 0,
    };
    let rtm_bytes = unsafe {
        std::slice::from_raw_parts(&rtm as *const RtMsg as *const u8, mem::size_of::<RtMsg>())
    };
    buf.extend_from_slice(rtm_bytes);

    // Destination (only if not default)
    if dst_prefix > 0 {
        push_attr(&mut buf, RTA_DST, &dst_addr.octets());
    }

    // Output interface
    push_attr_u32(&mut buf, RTA_OIF, ifindex);

    // Table (for IDs > 255)
    if table_id > 255 {
        push_attr_u32(&mut buf, RTA_TABLE, table_id);
    }

    let total_len = buf.len() as u32;
    let hdr = NlMsgHdr {
        nlmsg_len: total_len,
        nlmsg_type: RTM_NEWROUTE,
        nlmsg_flags: NLM_F_REQUEST | NLM_F_ACK | NLM_F_CREATE | NLM_F_EXCL,
        nlmsg_seq: seq,
        nlmsg_pid: 0,
    };
    let hdr_bytes = unsafe {
        std::slice::from_raw_parts(&hdr as *const NlMsgHdr as *const u8, mem::size_of::<NlMsgHdr>())
    };
    buf[..mem::size_of::<NlMsgHdr>()].copy_from_slice(hdr_bytes);

    sock.send_and_ack(&buf)
}

/// Delete a route.
pub fn route_delete(destination: &str, device: &str, table_name: &str) -> Result<(), String> {
    let mut sock = NetlinkSocket::open().map_err(|e| e.to_string())?;
    let seq = sock.next_seq();
    let table_id = resolve_table(table_name)?;
    let ifindex = if_nametoindex(device)?;

    let (dst_addr, dst_prefix) = if destination == "default" || destination == "0.0.0.0/0" {
        (Ipv4Addr::new(0, 0, 0, 0), 0u8)
    } else {
        parse_network(destination)?
    };

    let mut buf = Vec::with_capacity(256);
    buf.extend_from_slice(&[0u8; mem::size_of::<NlMsgHdr>()]);

    let rtm = RtMsg {
        rtm_family: libc::AF_INET as u8,
        rtm_dst_len: dst_prefix,
        rtm_src_len: 0,
        rtm_tos: 0,
        rtm_table: if table_id <= 255 { table_id as u8 } else { 0 },
        rtm_protocol: RTPROT_STATIC,
        rtm_scope: if dst_prefix == 0 { RT_SCOPE_UNIVERSE } else { RT_SCOPE_LINK },
        rtm_type: RTN_UNICAST,
        rtm_flags: 0,
    };
    let rtm_bytes = unsafe {
        std::slice::from_raw_parts(&rtm as *const RtMsg as *const u8, mem::size_of::<RtMsg>())
    };
    buf.extend_from_slice(rtm_bytes);

    if dst_prefix > 0 {
        push_attr(&mut buf, RTA_DST, &dst_addr.octets());
    }

    push_attr_u32(&mut buf, RTA_OIF, ifindex);

    if table_id > 255 {
        push_attr_u32(&mut buf, RTA_TABLE, table_id);
    }

    let total_len = buf.len() as u32;
    let hdr = NlMsgHdr {
        nlmsg_len: total_len,
        nlmsg_type: RTM_DELROUTE,
        nlmsg_flags: NLM_F_REQUEST | NLM_F_ACK,
        nlmsg_seq: seq,
        nlmsg_pid: 0,
    };
    let hdr_bytes = unsafe {
        std::slice::from_raw_parts(&hdr as *const NlMsgHdr as *const u8, mem::size_of::<NlMsgHdr>())
    };
    buf[..mem::size_of::<NlMsgHdr>()].copy_from_slice(hdr_bytes);

    sock.send_and_ack(&buf)
}

/// Ensure a routing table entry exists in /etc/iproute2/rt_tables.
pub fn ensure_table(table_id: u32, table_name: &str) -> Result<(), String> {
    let path = "/etc/iproute2/rt_tables";
    let entry = format!("{} {}", table_id, table_name);

    let content = std::fs::read_to_string(path)
        .unwrap_or_default();

    // Check if entry already exists
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 && parts[0] == table_id.to_string() && parts[1] == table_name {
            return Ok(()); // Already exists
        }
    }

    // Append entry
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| format!("Cannot write {}: {}", path, e))?;

    writeln!(file, "{}", entry)
        .map_err(|e| format!("Cannot write to {}: {}", path, e))
}

/// Flush route cache (no-op on Linux >= 3.6, included for compatibility).
pub fn flush_cache() -> Result<(), String> {
    // Modern kernels removed the route cache. Write to proc for older kernels.
    let _ = std::fs::write("/proc/sys/net/ipv4/route/flush", "1");
    Ok(())
}

/// Enable IP forwarding.
pub fn enable_ip_forward() -> Result<(), String> {
    std::fs::write("/proc/sys/net/ipv4/ip_forward", "1")
        .map_err(|e| format!("Cannot enable ip_forward: {}", e))
}