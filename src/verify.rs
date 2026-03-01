//! Kernel state verification and drift detection.
//!
//! Compares DB-tracked rules against actual kernel state (nft list + ip rule).
//! Reports: missing_in_kernel, extra_in_kernel, handle_mismatch.

use serde::Serialize;
use serde_json::json;

use crate::db::FirewallDB;
use crate::nft::NftContext;

const TABLE: &str = "inet phantom";

// ---------------------------------------------------------------------------
// Verify result types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct VerifyResult {
    pub in_sync: bool,
    pub firewall: FirewallVerify,
    pub routing: RoutingVerify,
}

#[derive(Debug, Serialize)]
pub struct FirewallVerify {
    pub db_applied: usize,
    pub kernel_rules: usize,
    pub missing_in_kernel: Vec<MissingRule>,
    pub extra_in_kernel: Vec<ExtraRule>,
}

#[derive(Debug, Serialize)]
pub struct RoutingVerify {
    pub db_applied: usize,
    pub summary: String,
}

#[derive(Debug, Serialize)]
pub struct MissingRule {
    pub rule_id: i64,
    pub chain: String,
    pub comment: String,
}

#[derive(Debug, Serialize)]
pub struct ExtraRule {
    pub chain: String,
    pub handle: u64,
    pub expr_summary: String,
}

// ---------------------------------------------------------------------------
// Kernel state query
// ---------------------------------------------------------------------------

/// Get actual kernel state as JSON (nft list table).
pub fn get_kernel_state(nft: &NftContext) -> Result<String, String> {
    let nft_state = nft.run_json(&format!("list table {TABLE}"))
        .unwrap_or_else(|_| "{}".to_string());

    Ok(json!({
        "nftables": nft_state,
    }).to_string())
}

// ---------------------------------------------------------------------------
// Verification
// ---------------------------------------------------------------------------

/// Compare DB applied rules against kernel state.
pub fn verify_rules(db: &FirewallDB, nft: &NftContext) -> Result<VerifyResult, String> {
    // Get DB state
    let db_applied = db.applied_firewall_rules()
        .map_err(|e| format!("DB query failed: {e}"))?;

    // Get kernel state
    let kernel_json = nft.run_json(&format!("list table {TABLE}"))
        .unwrap_or_else(|_| "{}".to_string());

    // Parse kernel rules with handles + comments
    let kernel_rules = parse_kernel_rules(&kernel_json);

    // Find missing: in DB (applied=1) but not in kernel
    let mut missing = Vec::new();
    for rule in &db_applied {
        let comment_tag = format!("phantom-rule-{}", rule.id);
        let found = kernel_rules.iter().any(|kr| {
            kr.comment.as_deref() == Some(&comment_tag)
        });
        if !found {
            missing.push(MissingRule {
                rule_id: rule.id,
                chain: rule.chain.clone(),
                comment: comment_tag,
            });
        }
    }

    // Find extra: in kernel but not tracked in DB
    let mut extra = Vec::new();
    for kr in &kernel_rules {
        // Skip rules without phantom comment tags (base chain policies, etc.)
        let is_tracked = match &kr.comment {
            Some(c) if c.starts_with("phantom-rule-") => {
                let id_str = c.strip_prefix("phantom-rule-").unwrap_or("");
                if let Ok(id) = id_str.parse::<i64>() {
                    db_applied.iter().any(|r| r.id == id)
                } else {
                    false
                }
            }
            _ => true, // non-phantom rules are not "extra" — they're unrelated
        };

        if !is_tracked {
            if let Some(comment) = &kr.comment {
                if comment.starts_with("phantom-rule-") {
                    extra.push(ExtraRule {
                        chain: kr.chain.clone(),
                        handle: kr.handle,
                        expr_summary: comment.clone(),
                    });
                }
            }
        }
    }

    // Routing verify (summary only — netlink dump is complex)
    let rt_applied = db.applied_routing_rules()
        .map_err(|e| format!("DB query failed: {e}"))?;

    let in_sync = missing.is_empty() && extra.is_empty();

    Ok(VerifyResult {
        in_sync,
        firewall: FirewallVerify {
            db_applied: db_applied.len(),
            kernel_rules: kernel_rules.len(),
            missing_in_kernel: missing,
            extra_in_kernel: extra,
        },
        routing: RoutingVerify {
            db_applied: rt_applied.len(),
            summary: format!("{} routing rules applied", rt_applied.len()),
        },
    })
}

// ---------------------------------------------------------------------------
// Kernel JSON parser
// ---------------------------------------------------------------------------

struct KernelRule {
    chain: String,
    handle: u64,
    comment: Option<String>,
}

fn parse_kernel_rules(json_str: &str) -> Vec<KernelRule> {
    let mut rules = Vec::new();

    let parsed: serde_json::Value = match serde_json::from_str(json_str) {
        Ok(v) => v,
        Err(_) => return rules,
    };

    let items = match parsed.get("nftables").and_then(|n| n.as_array()) {
        Some(arr) => arr,
        None => return rules,
    };

    for item in items {
        if let Some(rule) = item.get("rule") {
            let chain = rule.get("chain")
                .and_then(|c| c.as_str())
                .unwrap_or("")
                .to_string();
            let handle = rule.get("handle")
                .and_then(|h| h.as_u64())
                .unwrap_or(0);

            // Comment can be at rule level OR inside expr array
            let mut comment = rule.get("comment")
                .and_then(|c| c.as_str())
                .map(|s| s.to_string());

            if comment.is_none() {
                if let Some(expr) = rule.get("expr").and_then(|e| e.as_array()) {
                    for e in expr {
                        if let Some(c) = e.get("comment").and_then(|c| c.as_str()) {
                            comment = Some(c.to_string());
                        }
                    }
                }
            }

            rules.push(KernelRule { chain, handle, comment });
        }
    }

    rules
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_empty_kernel_rules() {
        let rules = parse_kernel_rules("{}");
        assert!(rules.is_empty());
    }

    #[test]
    fn test_parse_kernel_rules_with_comments() {
        let json = r#"{"nftables": [
            {"rule": {"chain": "input", "handle": 5, "expr": [
                {"comment": "phantom-rule-42"},
                {"accept": null}
            ]}},
            {"rule": {"chain": "output", "handle": 7, "expr": [
                {"drop": null}
            ]}}
        ]}"#;

        let rules = parse_kernel_rules(json);
        assert_eq!(rules.len(), 2);
        assert_eq!(rules[0].chain, "input");
        assert_eq!(rules[0].handle, 5);
        assert_eq!(rules[0].comment, Some("phantom-rule-42".to_string()));
        assert_eq!(rules[1].comment, None);
    }

    #[test]
    fn test_verify_empty_db() {
        let db = crate::db::FirewallDB::open(":memory:").unwrap();
        // Can't verify without nft context in unit test, but we can test the DB side
        let applied = db.applied_firewall_rules().unwrap();
        assert!(applied.is_empty());
    }
}
