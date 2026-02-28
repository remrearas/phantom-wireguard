/// Error codes returned by all FFI functions.
/// 0 = success, negative = error.
#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ErrorCode {
    Ok = 0,
    AlreadyInitialized = -1,
    NotInitialized = -2,
    NftablesFailed = -3,
    NetlinkFailed = -4,
    InvalidParam = -5,
    IoError = -6,
    PermissionDenied = -7,
}

impl std::fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Ok => write!(f, "OK"),
            Self::AlreadyInitialized => write!(f, "Already initialized"),
            Self::NotInitialized => write!(f, "Not initialized"),
            Self::NftablesFailed => write!(f, "nftables operation failed"),
            Self::NetlinkFailed => write!(f, "Netlink operation failed"),
            Self::InvalidParam => write!(f, "Invalid parameter"),
            Self::IoError => write!(f, "I/O error"),
            Self::PermissionDenied => write!(f, "Permission denied (need CAP_NET_ADMIN)"),
        }
    }
}