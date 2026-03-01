//! firewall-bridge-linux — SQLite database layer.
//!
//! Manages all persistent state: config, rule groups, firewall rules, routing rules.
//! Schema mirrors wireguard-go-bridge v2 pattern: WAL mode, user_version migration.

use rusqlite::{params, Connection, Result as SqlResult};
use serde::Serialize;
use std::time::{SystemTime, UNIX_EPOCH};

const SCHEMA_VERSION: i32 = 1;

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

// ---------------------------------------------------------------------------
// Row types (serde for JSON export)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize)]
pub struct ConfigRow {
    pub state: String,
    pub ip_forward_enabled: bool,
    pub ipv6_blocked: bool,
    pub kill_switch_active: bool,
    pub updated_at: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct RuleGroupRow {
    pub id: i64,
    pub name: String,
    pub group_type: String,
    pub enabled: bool,
    pub priority: i32,
    pub metadata: String,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct FirewallRuleRow {
    pub id: i64,
    pub group_id: i64,
    pub chain: String,
    pub rule_type: String,
    pub family: i32,
    pub proto: String,
    pub dport: i32,
    pub sport: i32,
    pub source: String,
    pub destination: String,
    pub in_iface: String,
    pub out_iface: String,
    pub state_match: String,
    pub comment: String,
    pub position: i32,
    pub applied: bool,
    pub nft_handle: i64,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct RoutingRuleRow {
    pub id: i64,
    pub group_id: i64,
    pub rule_type: String,
    pub from_network: String,
    pub to_network: String,
    pub table_name: String,
    pub table_id: i32,
    pub priority: i32,
    pub destination: String,
    pub device: String,
    pub fwmark: i32,
    pub applied: bool,
    pub created_at: i64,
}

// ---------------------------------------------------------------------------
// FirewallDB
// ---------------------------------------------------------------------------

pub struct FirewallDB {
    conn: Connection,
}

impl FirewallDB {
    pub fn open(path: &str) -> Result<Self, String> {
        let conn = Connection::open(path).map_err(|e| format!("DB open failed: {e}"))?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")
            .map_err(|e| format!("PRAGMA failed: {e}"))?;
        let mut db = Self { conn };
        db.migrate()?;
        Ok(db)
    }

    fn migrate(&mut self) -> Result<(), String> {
        let version: i32 = self
            .conn
            .query_row("PRAGMA user_version", [], |r| r.get(0))
            .map_err(|e| format!("PRAGMA user_version failed: {e}"))?;

        if version < SCHEMA_VERSION {
            self.conn
                .execute_batch(SCHEMA_DDL)
                .map_err(|e| format!("Schema migration failed: {e}"))?;
            self.conn
                .execute_batch(&format!("PRAGMA user_version = {SCHEMA_VERSION};"))
                .map_err(|e| format!("Set user_version failed: {e}"))?;
        }
        Ok(())
    }

    // ---- Config ----

    pub fn init_config(&self) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT OR IGNORE INTO config (id, updated_at) VALUES (1, ?1)",
                params![now()],
            )
            .map_err(|e| format!("init_config: {e}"))?;
        Ok(())
    }

    pub fn get_config(&self) -> Result<ConfigRow, String> {
        self.conn
            .query_row("SELECT * FROM config WHERE id = 1", [], |row| {
                Ok(ConfigRow {
                    state: row.get("state")?,
                    ip_forward_enabled: row.get::<_, i32>("ip_forward_enabled")? != 0,
                    ipv6_blocked: row.get::<_, i32>("ipv6_blocked")? != 0,
                    kill_switch_active: row.get::<_, i32>("kill_switch_active")? != 0,
                    updated_at: row.get("updated_at")?,
                })
            })
            .map_err(|e| format!("get_config: {e}"))
    }

    pub fn set_state(&self, state: &str) -> Result<(), String> {
        self.conn
            .execute(
                "UPDATE config SET state = ?1, updated_at = ?2 WHERE id = 1",
                params![state, now()],
            )
            .map_err(|e| format!("set_state: {e}"))?;
        Ok(())
    }

    pub fn set_config_flag(&self, column: &str, value: bool) -> Result<(), String> {
        // Only allow known columns to prevent SQL injection
        let allowed = [
            "ip_forward_enabled",
            "ipv6_blocked",
            "kill_switch_active",
        ];
        if !allowed.contains(&column) {
            return Err(format!("Unknown config column: {column}"));
        }
        let sql = format!("UPDATE config SET {column} = ?1, updated_at = ?2 WHERE id = 1");
        self.conn
            .execute(&sql, params![value as i32, now()])
            .map_err(|e| format!("set_config_flag: {e}"))?;
        Ok(())
    }

    // ---- Rule Groups ----

    pub fn create_rule_group(
        &self,
        name: &str,
        group_type: &str,
        priority: i32,
        metadata: &str,
    ) -> Result<RuleGroupRow, String> {
        let ts = now();
        self.conn
            .execute(
                "INSERT INTO rule_groups (name, group_type, priority, metadata, created_at, updated_at)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?5)",
                params![name, group_type, priority, metadata, ts],
            )
            .map_err(|e| format!("create_rule_group: {e}"))?;
        self.get_rule_group(name)
    }

    pub fn get_rule_group(&self, name: &str) -> Result<RuleGroupRow, String> {
        self.conn
            .query_row(
                "SELECT * FROM rule_groups WHERE name = ?1",
                params![name],
                |row| Self::map_rule_group(row),
            )
            .map_err(|e| format!("get_rule_group '{name}': {e}"))
    }

    pub fn get_rule_group_by_id(&self, id: i64) -> Result<RuleGroupRow, String> {
        self.conn
            .query_row(
                "SELECT * FROM rule_groups WHERE id = ?1",
                params![id],
                |row| Self::map_rule_group(row),
            )
            .map_err(|e| format!("get_rule_group_by_id {id}: {e}"))
    }

    pub fn list_rule_groups(&self) -> Result<Vec<RuleGroupRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM rule_groups ORDER BY priority, name")
            .map_err(|e| format!("list_rule_groups: {e}"))?;
        let rows = stmt
            .query_map([], |row| Self::map_rule_group(row))
            .map_err(|e| format!("list_rule_groups query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("list_rule_groups collect: {e}"))
    }

    pub fn enabled_groups(&self) -> Result<Vec<RuleGroupRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM rule_groups WHERE enabled = 1 ORDER BY priority, name")
            .map_err(|e| format!("enabled_groups: {e}"))?;
        let rows = stmt
            .query_map([], |row| Self::map_rule_group(row))
            .map_err(|e| format!("enabled_groups query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("enabled_groups collect: {e}"))
    }

    pub fn set_group_enabled(&self, name: &str, enabled: bool) -> Result<(), String> {
        let affected = self
            .conn
            .execute(
                "UPDATE rule_groups SET enabled = ?1, updated_at = ?2 WHERE name = ?3",
                params![enabled as i32, now(), name],
            )
            .map_err(|e| format!("set_group_enabled: {e}"))?;
        if affected == 0 {
            return Err(format!("Rule group not found: {name}"));
        }
        Ok(())
    }

    pub fn delete_rule_group(&self, name: &str) -> Result<(), String> {
        let affected = self
            .conn
            .execute("DELETE FROM rule_groups WHERE name = ?1", params![name])
            .map_err(|e| format!("delete_rule_group: {e}"))?;
        if affected == 0 {
            return Err(format!("Rule group not found: {name}"));
        }
        Ok(())
    }

    fn map_rule_group(row: &rusqlite::Row) -> SqlResult<RuleGroupRow> {
        Ok(RuleGroupRow {
            id: row.get("id")?,
            name: row.get("name")?,
            group_type: row.get("group_type")?,
            enabled: row.get::<_, i32>("enabled")? != 0,
            priority: row.get("priority")?,
            metadata: row.get("metadata")?,
            created_at: row.get("created_at")?,
            updated_at: row.get("updated_at")?,
        })
    }

    // ---- Firewall Rules ----

    pub fn insert_firewall_rule(
        &self,
        group_id: i64,
        chain: &str,
        rule_type: &str,
        family: i32,
        proto: &str,
        dport: i32,
        sport: i32,
        source: &str,
        destination: &str,
        in_iface: &str,
        out_iface: &str,
        state_match: &str,
        comment: &str,
        position: i32,
    ) -> Result<i64, String> {
        self.conn
            .execute(
                "INSERT INTO firewall_rules
                 (group_id, chain, rule_type, family, proto, dport, sport,
                  source, destination, in_iface, out_iface, state_match,
                  comment, position, created_at)
                 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15)",
                params![
                    group_id, chain, rule_type, family, proto, dport, sport,
                    source, destination, in_iface, out_iface, state_match,
                    comment, position, now()
                ],
            )
            .map_err(|e| format!("insert_firewall_rule: {e}"))?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn update_fw_rule_applied(
        &self,
        rule_id: i64,
        applied: bool,
        nft_handle: i64,
    ) -> Result<(), String> {
        self.conn
            .execute(
                "UPDATE firewall_rules SET applied = ?1, nft_handle = ?2 WHERE id = ?3",
                params![applied as i32, nft_handle, rule_id],
            )
            .map_err(|e| format!("update_fw_rule_applied: {e}"))?;
        Ok(())
    }

    pub fn delete_firewall_rule(&self, rule_id: i64) -> Result<(), String> {
        self.conn
            .execute("DELETE FROM firewall_rules WHERE id = ?1", params![rule_id])
            .map_err(|e| format!("delete_firewall_rule: {e}"))?;
        Ok(())
    }

    pub fn firewall_rules_for_group(&self, group_id: i64) -> Result<Vec<FirewallRuleRow>, String> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT * FROM firewall_rules WHERE group_id = ?1 ORDER BY position, id",
            )
            .map_err(|e| format!("firewall_rules_for_group: {e}"))?;
        let rows = stmt
            .query_map(params![group_id], |row| Self::map_firewall_rule(row))
            .map_err(|e| format!("firewall_rules_for_group query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("firewall_rules_for_group collect: {e}"))
    }

    pub fn all_firewall_rules(&self) -> Result<Vec<FirewallRuleRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM firewall_rules ORDER BY group_id, position, id")
            .map_err(|e| format!("all_firewall_rules: {e}"))?;
        let rows = stmt
            .query_map([], |row| Self::map_firewall_rule(row))
            .map_err(|e| format!("all_firewall_rules query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("all_firewall_rules collect: {e}"))
    }

    pub fn applied_firewall_rules(&self) -> Result<Vec<FirewallRuleRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM firewall_rules WHERE applied = 1 ORDER BY group_id, position")
            .map_err(|e| format!("applied_firewall_rules: {e}"))?;
        let rows = stmt
            .query_map([], |row| Self::map_firewall_rule(row))
            .map_err(|e| format!("applied_firewall_rules query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("applied_firewall_rules collect: {e}"))
    }

    pub fn clear_fw_applied_state(&self) -> Result<(), String> {
        self.conn
            .execute(
                "UPDATE firewall_rules SET applied = 0, nft_handle = 0",
                [],
            )
            .map_err(|e| format!("clear_fw_applied_state: {e}"))?;
        Ok(())
    }

    fn map_firewall_rule(row: &rusqlite::Row) -> SqlResult<FirewallRuleRow> {
        Ok(FirewallRuleRow {
            id: row.get("id")?,
            group_id: row.get("group_id")?,
            chain: row.get("chain")?,
            rule_type: row.get("rule_type")?,
            family: row.get("family")?,
            proto: row.get("proto")?,
            dport: row.get("dport")?,
            sport: row.get("sport")?,
            source: row.get("source")?,
            destination: row.get("destination")?,
            in_iface: row.get("in_iface")?,
            out_iface: row.get("out_iface")?,
            state_match: row.get("state_match")?,
            comment: row.get("comment")?,
            position: row.get("position")?,
            applied: row.get::<_, i32>("applied")? != 0,
            nft_handle: row.get("nft_handle")?,
            created_at: row.get("created_at")?,
        })
    }

    // ---- Routing Rules ----

    pub fn insert_routing_rule(
        &self,
        group_id: i64,
        rule_type: &str,
        from_network: &str,
        to_network: &str,
        table_name: &str,
        table_id: i32,
        priority: i32,
        destination: &str,
        device: &str,
        fwmark: i32,
    ) -> Result<i64, String> {
        self.conn
            .execute(
                "INSERT INTO routing_rules
                 (group_id, rule_type, from_network, to_network, table_name,
                  table_id, priority, destination, device, fwmark, created_at)
                 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
                params![
                    group_id, rule_type, from_network, to_network, table_name,
                    table_id, priority, destination, device, fwmark, now()
                ],
            )
            .map_err(|e| format!("insert_routing_rule: {e}"))?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn update_rt_rule_applied(&self, rule_id: i64, applied: bool) -> Result<(), String> {
        self.conn
            .execute(
                "UPDATE routing_rules SET applied = ?1 WHERE id = ?2",
                params![applied as i32, rule_id],
            )
            .map_err(|e| format!("update_rt_rule_applied: {e}"))?;
        Ok(())
    }

    pub fn delete_routing_rule(&self, rule_id: i64) -> Result<(), String> {
        self.conn
            .execute("DELETE FROM routing_rules WHERE id = ?1", params![rule_id])
            .map_err(|e| format!("delete_routing_rule: {e}"))?;
        Ok(())
    }

    pub fn routing_rules_for_group(&self, group_id: i64) -> Result<Vec<RoutingRuleRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM routing_rules WHERE group_id = ?1 ORDER BY id")
            .map_err(|e| format!("routing_rules_for_group: {e}"))?;
        let rows = stmt
            .query_map(params![group_id], |row| Self::map_routing_rule(row))
            .map_err(|e| format!("routing_rules_for_group query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("routing_rules_for_group collect: {e}"))
    }

    pub fn applied_routing_rules(&self) -> Result<Vec<RoutingRuleRow>, String> {
        let mut stmt = self
            .conn
            .prepare("SELECT * FROM routing_rules WHERE applied = 1 ORDER BY group_id, id")
            .map_err(|e| format!("applied_routing_rules: {e}"))?;
        let rows = stmt
            .query_map([], |row| Self::map_routing_rule(row))
            .map_err(|e| format!("applied_routing_rules query: {e}"))?;
        rows.collect::<SqlResult<Vec<_>>>()
            .map_err(|e| format!("applied_routing_rules collect: {e}"))
    }

    pub fn clear_rt_applied_state(&self) -> Result<(), String> {
        self.conn
            .execute("UPDATE routing_rules SET applied = 0", [])
            .map_err(|e| format!("clear_rt_applied_state: {e}"))?;
        Ok(())
    }

    fn map_routing_rule(row: &rusqlite::Row) -> SqlResult<RoutingRuleRow> {
        Ok(RoutingRuleRow {
            id: row.get("id")?,
            group_id: row.get("group_id")?,
            rule_type: row.get("rule_type")?,
            from_network: row.get("from_network")?,
            to_network: row.get("to_network")?,
            table_name: row.get("table_name")?,
            table_id: row.get("table_id")?,
            priority: row.get("priority")?,
            destination: row.get("destination")?,
            device: row.get("device")?,
            fwmark: row.get("fwmark")?,
            applied: row.get::<_, i32>("applied")? != 0,
            created_at: row.get("created_at")?,
        })
    }
}

// ---------------------------------------------------------------------------
// Schema DDL
// ---------------------------------------------------------------------------

const SCHEMA_DDL: &str = "
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL DEFAULT 'initialized',
    ip_forward_enabled INTEGER NOT NULL DEFAULT 0,
    ipv6_blocked INTEGER NOT NULL DEFAULT 0,
    kill_switch_active INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rule_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    group_type TEXT NOT NULL DEFAULT 'custom',
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS firewall_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES rule_groups(id) ON DELETE CASCADE,
    chain TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    family INTEGER NOT NULL DEFAULT 2,
    proto TEXT NOT NULL DEFAULT '',
    dport INTEGER NOT NULL DEFAULT 0,
    sport INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    destination TEXT NOT NULL DEFAULT '',
    in_iface TEXT NOT NULL DEFAULT '',
    out_iface TEXT NOT NULL DEFAULT '',
    state_match TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0,
    nft_handle INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES rule_groups(id) ON DELETE CASCADE,
    rule_type TEXT NOT NULL,
    from_network TEXT NOT NULL DEFAULT '',
    to_network TEXT NOT NULL DEFAULT '',
    table_name TEXT NOT NULL DEFAULT '',
    table_id INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    destination TEXT NOT NULL DEFAULT '',
    device TEXT NOT NULL DEFAULT '',
    fwmark INTEGER NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fw_group ON firewall_rules(group_id);
CREATE INDEX IF NOT EXISTS idx_fw_applied ON firewall_rules(applied);
CREATE INDEX IF NOT EXISTS idx_rt_group ON routing_rules(group_id);
CREATE INDEX IF NOT EXISTS idx_rt_applied ON routing_rules(applied);
CREATE INDEX IF NOT EXISTS idx_rg_enabled ON rule_groups(enabled);
CREATE INDEX IF NOT EXISTS idx_rg_type ON rule_groups(group_type);
";

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn test_db() -> FirewallDB {
        FirewallDB::open(":memory:").expect("in-memory DB")
    }

    #[test]
    fn test_open_and_migrate() {
        let db = test_db();
        let tables: Vec<String> = db
            .conn
            .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            .unwrap()
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<SqlResult<_>>()
            .unwrap();
        assert_eq!(
            tables,
            vec!["config", "firewall_rules", "routing_rules", "rule_groups"]
        );
    }

    #[test]
    fn test_user_version() {
        let db = test_db();
        let ver: i32 = db.conn.query_row("PRAGMA user_version", [], |r| r.get(0)).unwrap();
        assert_eq!(ver, SCHEMA_VERSION);
    }

    #[test]
    fn test_config_lifecycle() {
        let db = test_db();
        db.init_config().unwrap();
        let cfg = db.get_config().unwrap();
        assert_eq!(cfg.state, "initialized");
        assert!(!cfg.ip_forward_enabled);

        db.set_state("started").unwrap();
        assert_eq!(db.get_config().unwrap().state, "started");

        db.set_config_flag("ip_forward_enabled", true).unwrap();
        assert!(db.get_config().unwrap().ip_forward_enabled);
    }

    #[test]
    fn test_rule_group_crud() {
        let db = test_db();
        let group = db.create_rule_group("vpn-basic", "vpn", 50, "{}").unwrap();
        assert_eq!(group.name, "vpn-basic");
        assert_eq!(group.group_type, "vpn");
        assert_eq!(group.priority, 50);
        assert!(group.enabled);

        let groups = db.list_rule_groups().unwrap();
        assert_eq!(groups.len(), 1);

        db.set_group_enabled("vpn-basic", false).unwrap();
        let updated = db.get_rule_group("vpn-basic").unwrap();
        assert!(!updated.enabled);

        db.delete_rule_group("vpn-basic").unwrap();
        assert!(db.get_rule_group("vpn-basic").is_err());
    }

    #[test]
    fn test_firewall_rule_crud() {
        let db = test_db();
        let group = db.create_rule_group("test", "custom", 100, "{}").unwrap();

        let rule_id = db
            .insert_firewall_rule(
                group.id, "input", "accept", 2, "udp", 51820, 0,
                "", "", "", "", "", "wg-port", 0,
            )
            .unwrap();
        assert!(rule_id > 0);

        let rules = db.firewall_rules_for_group(group.id).unwrap();
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].chain, "input");
        assert_eq!(rules[0].dport, 51820);
        assert!(!rules[0].applied);

        db.update_fw_rule_applied(rule_id, true, 42).unwrap();
        let applied = db.applied_firewall_rules().unwrap();
        assert_eq!(applied.len(), 1);
        assert_eq!(applied[0].nft_handle, 42);

        db.clear_fw_applied_state().unwrap();
        assert_eq!(db.applied_firewall_rules().unwrap().len(), 0);
    }

    #[test]
    fn test_routing_rule_crud() {
        let db = test_db();
        let group = db.create_rule_group("mh", "multihop", 100, "{}").unwrap();

        let rule_id = db
            .insert_routing_rule(
                group.id, "policy", "10.8.0.0/24", "", "multihop", 100, 100,
                "", "", 0,
            )
            .unwrap();
        assert!(rule_id > 0);

        let rules = db.routing_rules_for_group(group.id).unwrap();
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].rule_type, "policy");

        db.update_rt_rule_applied(rule_id, true).unwrap();
        assert_eq!(db.applied_routing_rules().unwrap().len(), 1);

        db.clear_rt_applied_state().unwrap();
        assert_eq!(db.applied_routing_rules().unwrap().len(), 0);
    }

    #[test]
    fn test_cascade_delete() {
        let db = test_db();
        let group = db.create_rule_group("del-test", "custom", 100, "{}").unwrap();
        db.insert_firewall_rule(group.id, "input", "accept", 2, "tcp", 443, 0, "", "", "", "", "", "", 0).unwrap();
        db.insert_firewall_rule(group.id, "forward", "accept", 2, "", 0, 0, "", "", "wg0", "eth0", "", "", 1).unwrap();
        db.insert_routing_rule(group.id, "policy", "10.0.0.0/8", "", "main", 254, 100, "", "", 0).unwrap();

        assert_eq!(db.firewall_rules_for_group(group.id).unwrap().len(), 2);
        assert_eq!(db.routing_rules_for_group(group.id).unwrap().len(), 1);

        db.delete_rule_group("del-test").unwrap();
        // All rules should be CASCADE deleted — query by group returns empty
        assert_eq!(db.all_firewall_rules().unwrap().len(), 0);
    }

    #[test]
    fn test_enabled_groups() {
        let db = test_db();
        db.create_rule_group("enabled", "vpn", 50, "{}").unwrap();
        db.create_rule_group("disabled", "vpn", 100, "{}").unwrap();
        db.set_group_enabled("disabled", false).unwrap();

        let enabled = db.enabled_groups().unwrap();
        assert_eq!(enabled.len(), 1);
        assert_eq!(enabled[0].name, "enabled");
    }

    #[test]
    fn test_idempotent_migration() {
        let db = test_db();
        // Second migrate should be a no-op
        assert!(db.conn.execute_batch(SCHEMA_DDL).is_ok());
    }
}
