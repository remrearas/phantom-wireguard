//! FirewallState — lifecycle state machine for firewall-bridge v2.
//!
//! Mirrors wireguard-go-bridge BridgeState pattern:
//! Uninitialized → Initialized → Started ⇄ Stopped → Uninitialized
//!
//! Owns the SQLite DB and nftables context. All mutations go through
//! this struct, serialized by a Mutex in lib.rs.

use serde_json::json;

use crate::db::FirewallDB;
use crate::error::ErrorCode;
use crate::{emit_log, LOG_INFO, LOG_ERROR, LOG_DEBUG};
use crate::nft::{self, NftContext};

// ---------------------------------------------------------------------------
// Status enum
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Status {
    Uninitialized,
    Initialized,
    Started,
    Stopped,
    Error,
}

impl Status {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Uninitialized => "uninitialized",
            Self::Initialized => "initialized",
            Self::Started => "started",
            Self::Stopped => "stopped",
            Self::Error => "error",
        }
    }
}

// ---------------------------------------------------------------------------
// FirewallState
// ---------------------------------------------------------------------------

pub struct FirewallState {
    db: Option<FirewallDB>,
    nft: Option<NftContext>,
    status: Status,
    last_error: String,
}

impl FirewallState {
    pub const fn new() -> Self {
        Self {
            db: None,
            nft: None,
            status: Status::Uninitialized,
            last_error: String::new(),
        }
    }

    // ---- Lifecycle ----

    /// Initialize: open DB, create nft context, ensure phantom table.
    /// Auto-closes previous state if re-initialized (singleton safe).
    pub fn init(&mut self, db_path: &str) -> Result<(), (ErrorCode, String)> {
        // Auto-close if already initialized (idempotent re-init)
        if self.status != Status::Uninitialized {
            let _ = self.close_internal();
        }

        // Open SQLite
        let db = FirewallDB::open(db_path).map_err(|e| (ErrorCode::DbOpen, e))?;
        db.init_config().map_err(|e| (ErrorCode::DbWrite, e))?;

        // Clear stale applied state from previous crash
        db.clear_fw_applied_state().map_err(|e| (ErrorCode::DbWrite, e))?;
        db.clear_rt_applied_state().map_err(|e| (ErrorCode::DbWrite, e))?;

        // Create nftables context
        let ctx = NftContext::new().map_err(|_| {
            (ErrorCode::NftablesFailed, "Failed to create nftables context".into())
        })?;

        // Ensure phantom table + chains exist (input, output, forward, postrouting)
        nft::ensure_table(&ctx).map_err(|e| (ErrorCode::NftablesFailed, e))?;

        db.set_state("initialized").map_err(|e| (ErrorCode::DbWrite, e))?;

        self.db = Some(db);
        self.nft = Some(ctx);
        self.status = Status::Initialized;
        self.last_error.clear();
        emit_log(LOG_INFO, &format!("Initialized: {db_path}"));
        Ok(())
    }

    /// Start: apply all enabled rule groups from DB to kernel.
    pub fn start(&mut self) -> Result<(), (ErrorCode, String)> {
        match self.status {
            Status::Initialized | Status::Stopped => {}
            Status::Started => return Err((ErrorCode::AlreadyStarted, "Already started".into())),
            _ => return Err((ErrorCode::InvalidState, format!("Cannot start from {}", self.status.as_str()))),
        }

        let db = self.db.as_ref().ok_or((ErrorCode::NotInitialized, "DB not open".into()))?;
        let nft = self.nft.as_ref().ok_or((ErrorCode::NotInitialized, "NFT not open".into()))?;

        // Flush phantom table first (clean slate for reconciliation)
        nft::flush_table(nft).map_err(|e| (ErrorCode::NftablesFailed, e))?;

        // Re-apply all enabled rule groups ordered by priority
        let groups = db.enabled_groups().map_err(|e| (ErrorCode::DbQuery, e))?;
        for group in &groups {
            let rules = db.firewall_rules_for_group(group.id).map_err(|e| (ErrorCode::DbQuery, e))?;
            for rule in &rules {
                match nft::apply_rule(nft, rule) {
                    Ok(handle) => {
                        let _ = db.update_fw_rule_applied(rule.id, true, handle as i64);
                    }
                    Err(e) => {
                        self.last_error = format!("Failed to apply rule {}: {}", rule.id, e);
                        // Continue applying other rules — partial start is better than no start
                    }
                }
            }

            let rt_rules = db.routing_rules_for_group(group.id).map_err(|e| (ErrorCode::DbQuery, e))?;
            for rule in &rt_rules {
                match crate::route::apply_routing_rule(rule) {
                    Ok(()) => {
                        let _ = db.update_rt_rule_applied(rule.id, true);
                    }
                    Err(e) => {
                        self.last_error = format!("Failed to apply routing rule {}: {}", rule.id, e);
                    }
                }
            }
        }

        db.set_state("started").map_err(|e| (ErrorCode::DbWrite, e))?;
        self.status = Status::Started;
        emit_log(LOG_INFO, &format!("Started: {} groups, applied rules", groups.len()));
        Ok(())
    }

    /// Stop: flush all applied rules from kernel, mark unapplied in DB.
    pub fn stop(&mut self) -> Result<(), (ErrorCode, String)> {
        if self.status != Status::Started {
            return Err((ErrorCode::NotStarted, "Not started".into()));
        }

        let db = self.db.as_ref().ok_or((ErrorCode::NotInitialized, "DB not open".into()))?;
        let nft = self.nft.as_ref().ok_or((ErrorCode::NotInitialized, "NFT not open".into()))?;

        // Flush phantom table (removes all firewall rules)
        let _ = nft::flush_table(nft);

        // Remove applied routing rules
        if let Ok(rt_rules) = db.applied_routing_rules() {
            for rule in &rt_rules {
                let _ = crate::route::remove_routing_rule(rule);
            }
        }

        // Clear applied state in DB
        let _ = db.clear_fw_applied_state();
        let _ = db.clear_rt_applied_state();

        db.set_state("stopped").map_err(|e| (ErrorCode::DbWrite, e))?;
        self.status = Status::Stopped;
        emit_log(LOG_INFO, "Stopped: all rules flushed");
        Ok(())
    }

    /// Close: stop if started, drop nft context, close DB.
    pub fn close(&mut self) -> Result<(), (ErrorCode, String)> {
        self.close_internal()
    }

    fn close_internal(&mut self) -> Result<(), (ErrorCode, String)> {
        if self.status == Status::Started {
            let _ = self.stop();
        }
        self.nft = None;
        self.db = None;
        self.status = Status::Uninitialized;
        self.last_error.clear();
        Ok(())
    }

    // ---- Status ----

    pub fn get_status_json(&self) -> String {
        let (enabled_groups, total_fw, applied_fw, total_rt, applied_rt) = match &self.db {
            Some(db) => {
                let eg = db.enabled_groups().map(|g| g.len()).unwrap_or(0);
                let tfw = db.all_firewall_rules().map(|r| r.len()).unwrap_or(0);
                let afw = db.applied_firewall_rules().map(|r| r.len()).unwrap_or(0);
                let trt = db.applied_routing_rules().map(|r| r.len()).unwrap_or(0); // reuse for total
                let art = db.applied_routing_rules().map(|r| r.len()).unwrap_or(0);
                (eg, tfw, afw, trt, art)
            }
            None => (0, 0, 0, 0, 0),
        };

        json!({
            "status": self.status.as_str(),
            "enabled_groups": enabled_groups,
            "firewall_rules": { "total": total_fw, "applied": applied_fw },
            "routing_rules": { "total": total_rt, "applied": applied_rt },
            "last_error": self.last_error,
        })
        .to_string()
    }

    pub fn status(&self) -> Status {
        self.status
    }

    pub fn set_last_error(&mut self, msg: &str) {
        self.last_error = msg.to_string();
    }

    pub fn last_error(&self) -> &str {
        &self.last_error
    }

    // ---- Accessor helpers ----

    pub fn db(&self) -> Result<&FirewallDB, (ErrorCode, String)> {
        self.db.as_ref().ok_or((ErrorCode::NotInitialized, "DB not open".into()))
    }

    pub fn nft(&self) -> Result<&NftContext, (ErrorCode, String)> {
        self.nft.as_ref().ok_or((ErrorCode::NotInitialized, "NFT context not available".into()))
    }

    pub fn is_started(&self) -> bool {
        self.status == Status::Started
    }
}
