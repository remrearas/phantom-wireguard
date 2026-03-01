/// Error codes returned by all FFI functions.
/// 0 = success, negative = error.
/// v1 codes (-1 to -7) preserved for backward compatibility.
#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ErrorCode {
    Ok = 0,

    // v1 codes
    AlreadyInitialized = -1,
    NotInitialized = -2,
    NftablesFailed = -3,
    NetlinkFailed = -4,
    InvalidParam = -5,
    IoError = -6,
    PermissionDenied = -7,

    // v2 codes
    DbOpen = -10,
    DbQuery = -11,
    DbWrite = -12,
    GroupNotFound = -13,
    RuleNotFound = -14,
    InvalidState = -15,
    AlreadyStarted = -16,
    NotStarted = -17,
    PresetFailed = -18,
    VerifyFailed = -19,
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
            Self::DbOpen => write!(f, "Database open failed"),
            Self::DbQuery => write!(f, "Database query failed"),
            Self::DbWrite => write!(f, "Database write failed"),
            Self::GroupNotFound => write!(f, "Rule group not found"),
            Self::RuleNotFound => write!(f, "Rule not found"),
            Self::InvalidState => write!(f, "Invalid state for this operation"),
            Self::AlreadyStarted => write!(f, "Already started"),
            Self::NotStarted => write!(f, "Not started"),
            Self::PresetFailed => write!(f, "Preset application failed"),
            Self::VerifyFailed => write!(f, "Verification failed"),
        }
    }
}
