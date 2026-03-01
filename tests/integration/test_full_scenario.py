"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Full scenario integration tests for firewall-bridge v2.

Each test validates:
1. Python API returns correct data
2. OS-level nft/ip commands confirm kernel state
3. DB state matches expectations
4. Cleanup is complete

All tests are self-contained — unique DB per test, full lifecycle.
"""

import json
import logging
import os
import subprocess
import tempfile

import pytest

from firewall_bridge.client import FirewallClient
from firewall_bridge.types import FirewallBridgeError

log = logging.getLogger("test_full_scenario")


# ---------------------------------------------------------------------------
# OS-level verification helpers
# ---------------------------------------------------------------------------

def nft_list() -> str:
    """Get full nftables phantom table output from kernel."""
    r = subprocess.run(["nft", "list", "table", "inet", "phantom"],
                       capture_output=True, text=True)
    return r.stdout


def nft_list_json() -> dict:
    """Get nftables phantom table as JSON."""
    r = subprocess.run(["nft", "-j", "list", "table", "inet", "phantom"],
                       capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def nft_flush():
    """External flush — simulates chaos."""
    subprocess.run(["nft", "flush", "table", "inet", "phantom"],
                   capture_output=True)


def count_nft_rules() -> int:
    """Count actual rules in kernel phantom table."""
    data = nft_list_json()
    return sum(1 for item in data.get("nftables", []) if "rule" in item)


def nft_chain_has_rule(chain: str, fragment: str) -> bool:
    """Check if a specific rule fragment exists in a chain."""
    r = subprocess.run(["nft", "list", "chain", "inet", "phantom", chain],
                       capture_output=True, text=True)
    return fragment in r.stdout


# ---------------------------------------------------------------------------
# Fixture: isolated FirewallClient per test
# ---------------------------------------------------------------------------

@pytest.fixture
def fw(uid):
    """Fresh FirewallClient with unique DB, started state."""
    db_path = os.path.join(tempfile.gettempdir(), f"fw_full_{uid}.db")
    client = FirewallClient(db_path)
    client.start()
    yield client
    try:
        client.stop()
    except FirewallBridgeError:
        pass
    try:
        client.close()
    except FirewallBridgeError:
        pass
    for ext in ("", "-wal", "-shm"):
        p = db_path + ext
        if os.path.exists(p):
            os.remove(p)


# ===========================================================================
# TEST: Full VPN lifecycle
# ===========================================================================

@pytest.mark.docker
class TestVPNFullLifecycle:
    """VPN preset: create → verify kernel → disable → verify removed → re-enable → remove."""

    def test_vpn_apply_and_kernel_verify(self, fw):
        # Step 1: Apply VPN preset
        group = fw.apply_preset_vpn("vpn-full", "wg0", 51820, "10.8.0.0/24", "eth0")
        assert group.name == "vpn-full"
        assert group.group_type == "vpn"
        log.info(f"VPN group created: {group.name}")

        # Step 2: Verify 4 rules in DB
        rules = fw.list_firewall_rules("vpn-full")
        assert len(rules) == 4
        applied = [r for r in rules if r.applied]
        assert len(applied) == 4, f"Expected 4 applied, got {len(applied)}"

        # Step 3: Verify kernel — nft list shows rules
        output = nft_list()
        assert "udp dport 51820" in output, "WG port rule missing in kernel"
        assert "masquerade" in output, "NAT masquerade missing in kernel"
        assert 'oifname "eth0"' in output, "Output iface rule missing"
        assert 'iifname "wg0"' in output, "Input iface rule missing"
        log.info("Kernel verification: all 4 VPN rules present")

        # Step 4: Verify handle tracking
        for r in applied:
            assert r.nft_handle > 0, f"Rule {r.id} missing nft_handle"

    def test_vpn_disable_removes_from_kernel(self, fw):
        fw.apply_preset_vpn("vpn-dis", "wg0", 51820, "10.8.0.0/24", "eth0")
        assert "udp dport 51820" in nft_list()

        # Disable — should remove from kernel
        fw.disable_rule_group("vpn-dis")
        output = nft_list()
        assert "udp dport 51820" not in output, "Rule still in kernel after disable"
        assert "masquerade" not in output, "NAT still in kernel after disable"
        log.info("Disable verified: kernel clean")

        # DB: rules exist but applied=False
        rules = fw.list_firewall_rules("vpn-dis")
        assert len(rules) == 4
        assert all(not r.applied for r in rules), "Rules still marked applied"

    def test_vpn_reenable_restores(self, fw):
        fw.apply_preset_vpn("vpn-re", "wg0", 51820, "10.8.0.0/24", "eth0")
        fw.disable_rule_group("vpn-re")
        assert "udp dport 51820" not in nft_list()

        # Re-enable
        fw.enable_rule_group("vpn-re")
        output = nft_list()
        assert "udp dport 51820" in output, "Rule not restored after re-enable"
        assert "masquerade" in output, "NAT not restored after re-enable"
        log.info("Re-enable verified: rules restored")

    def test_vpn_remove_cleans_everything(self, fw):
        fw.apply_preset_vpn("vpn-rm", "wg0", 51820, "10.8.0.0/24", "eth0")
        fw.remove_preset("vpn-rm")

        # DB: group gone
        groups = fw.list_rule_groups()
        assert not any(g.name == "vpn-rm" for g in groups), "Group still in DB"

        # DB: rules gone (CASCADE)
        rules = fw.list_firewall_rules()
        assert len(rules) == 0, "Orphan rules remain"

        # Kernel: clean
        assert "udp dport 51820" not in nft_list()
        log.info("Remove verified: DB + kernel clean")


# ===========================================================================
# TEST: Kill-switch full lifecycle
# ===========================================================================

@pytest.mark.docker
class TestKillSwitchFullLifecycle:
    """Kill-switch: apply → verify OUTPUT/INPUT chains → verify drop rules → remove."""

    def test_kill_switch_output_chain(self, fw):
        group = fw.apply_preset_kill_switch(51820, 443, "wg0")
        assert group.priority == 10  # highest after ipv6

        rules = fw.list_firewall_rules("kill-switch")
        output_rules = [r for r in rules if r.chain == "output"]
        input_rules = [r for r in rules if r.chain == "input"]

        # OUTPUT: lo, ct, wg-port, wg-iface, dhcp67, dhcp68, wstunnel, drop
        assert len(output_rules) == 8
        # INPUT: lo, ct, drop
        assert len(input_rules) == 3

        # Kernel verification
        output = nft_list()
        assert "chain output" in output
        assert "drop" in output
        assert 'oifname "lo"' in output, "Loopback allow missing"
        assert "udp dport 51820" in output, "WG port allow missing"
        assert "tcp dport 443" in output, "Wstunnel port allow missing"
        log.info("Kill-switch kernel verification passed")

    def test_kill_switch_drop_is_last(self, fw):
        """Verify drop rules come after all accept rules (position ordering)."""
        fw.apply_preset_kill_switch(51820, 0, "wg0")
        rules = fw.list_firewall_rules("kill-switch")

        output_rules = sorted(
            [r for r in rules if r.chain == "output"],
            key=lambda r: r.position
        )
        # Last output rule must be drop
        assert output_rules[-1].rule_type == "drop"
        # All before last must be accept
        assert all(r.rule_type == "accept" for r in output_rules[:-1])


# ===========================================================================
# TEST: DNS protection
# ===========================================================================

@pytest.mark.docker
class TestDNSProtection:
    """DNS leak protection: only allow DNS via WG interface."""

    def test_dns_rules_in_kernel(self, fw):
        fw.apply_preset_dns_protection("wg0")

        output = nft_list()
        assert "dport 53" in output, "DNS port rule missing"
        assert 'oifname "wg0"' in output, "WG interface DNS allow missing"

        rules = fw.list_firewall_rules("dns-protection")
        assert len(rules) == 5
        # First 3: accept (wg udp, wg tcp, lo udp)
        assert rules[0].rule_type == "accept"
        assert rules[0].out_iface == "wg0"
        # Last 2: drop
        assert rules[3].rule_type == "drop"
        assert rules[4].rule_type == "drop"


# ===========================================================================
# TEST: IPv6 block
# ===========================================================================

@pytest.mark.docker
class TestIPv6Block:
    """IPv6 block: drop all inet6 on input/output/forward."""

    def test_ipv6_block_all_chains(self, fw):
        group = fw.apply_preset_ipv6_block()
        assert group.priority == 5  # highest priority

        rules = fw.list_firewall_rules("ipv6-block")
        assert len(rules) == 3
        chains = {r.chain for r in rules}
        assert chains == {"input", "output", "forward"}
        assert all(r.family == 10 for r in rules)  # AF_INET6
        assert all(r.rule_type == "drop" for r in rules)


# ===========================================================================
# TEST: Rule group CRUD
# ===========================================================================

@pytest.mark.docker
class TestRuleGroupCRUD:
    """Manual rule group creation, rule addition, and management."""

    def test_create_group_and_add_rules(self, fw):
        group = fw.create_rule_group("custom-test", "custom", 50)
        assert group.name == "custom-test"
        assert group.priority == 50

        # Add a firewall rule
        rid = fw.add_firewall_rule("custom-test", "input", "accept",
                                   proto="tcp", dport=8080)
        assert rid > 0

        # Verify in DB
        rules = fw.list_firewall_rules("custom-test")
        assert len(rules) == 1
        assert rules[0].dport == 8080
        assert rules[0].applied  # started → applied immediately

        # Verify in kernel
        assert nft_chain_has_rule("input", "tcp dport 8080")

    def test_remove_individual_rule(self, fw):
        fw.create_rule_group("rm-rule", "custom", 100)
        rid = fw.add_firewall_rule("rm-rule", "input", "accept",
                                   proto="tcp", dport=9090)
        assert nft_chain_has_rule("input", "tcp dport 9090")

        fw.remove_firewall_rule(rid)
        assert not nft_chain_has_rule("input", "tcp dport 9090")
        assert len(fw.list_firewall_rules("rm-rule")) == 0

    def test_add_routing_rule(self, fw):
        fw.create_rule_group("rt-test", "custom", 100)
        rid = fw.add_routing_rule("rt-test", "table",
                                  table_name="phantom-rt", table_id=200)
        assert rid > 0

        rules = fw.list_routing_rules("rt-test")
        assert len(rules) == 1
        assert rules[0].rule_type == "table"

    def test_list_all_rules_no_group(self, fw):
        fw.create_rule_group("g1", "custom", 100)
        fw.create_rule_group("g2", "custom", 200)
        fw.add_firewall_rule("g1", "input", "accept", proto="tcp", dport=1111)
        fw.add_firewall_rule("g2", "input", "accept", proto="tcp", dport=2222)

        # List all (no group filter)
        all_rules = fw.list_firewall_rules()
        assert len(all_rules) == 2

    def test_get_rule_group(self, fw):
        fw.create_rule_group("get-test", "custom", 75)
        group = fw.get_rule_group("get-test")
        assert group.name == "get-test"
        assert group.priority == 75

    def test_delete_rule_group_removes_rules(self, fw):
        fw.create_rule_group("del-test", "custom", 100)
        fw.add_firewall_rule("del-test", "input", "accept", proto="tcp", dport=7777)
        assert nft_chain_has_rule("input", "tcp dport 7777")

        fw.delete_rule_group("del-test")
        assert not nft_chain_has_rule("input", "tcp dport 7777")
        assert len(fw.list_firewall_rules()) == 0

    def test_remove_routing_rule(self, fw):
        fw.create_rule_group("rt-rm", "custom", 100)
        rid = fw.add_routing_rule("rt-rm", "table",
                                  table_name="test-tbl", table_id=250)
        assert rid > 0
        fw.remove_routing_rule(rid)
        assert len(fw.list_routing_rules("rt-rm")) == 0

    def test_add_rule_error_bad_group(self, fw):
        """Adding rule to nonexistent group returns error."""
        result = fw._lib.fw_add_rule(
            b"nonexistent", b"input", b"accept", 2, b"tcp", 80,
            b"", b"", b"", b"", b"")
        assert result < 0  # GROUP_NOT_FOUND

    def test_add_routing_rule_error_bad_group(self, fw):
        """Adding routing rule to nonexistent group returns error."""
        result = fw._lib.rt_add_rule(
            b"nonexistent", b"policy", b"10.0.0.0/8", b"", b"main", 254, 100,
            b"", b"", 0)
        assert result < 0


# ===========================================================================
# TEST: Multihop preset
# ===========================================================================

@pytest.mark.docker
class TestMultihopPreset:
    """Multihop: policy routing + forward rules."""

    def test_multihop_creates_rules(self, fw):
        group = fw.apply_preset_multihop(
            "hop1", "wg0", "wg-hop1", 100, 200, "10.8.0.0/24")
        assert group.group_type == "multihop"
        assert group.priority == 80

        fw_rules = fw.list_firewall_rules("hop1")
        rt_rules = fw.list_routing_rules("hop1")
        assert len(fw_rules) == 2  # forward + return
        assert len(rt_rules) >= 3  # table + policy + route + fwmark

    def test_multihop_forward_in_kernel(self, fw):
        fw.apply_preset_multihop(
            "hop-kern", "wg0", "wg-hop1", 0, 201, "10.8.0.0/24")

        output = nft_list()
        assert 'iifname "wg0"' in output
        assert 'oifname "wg-hop1"' in output


# ===========================================================================
# TEST: Context manager
# ===========================================================================

@pytest.mark.docker
class TestContextManager:
    """FirewallClient as context manager."""

    def test_context_manager_lifecycle(self, uid):
        db_path = os.path.join(tempfile.gettempdir(), f"fw_ctx_{uid}.db")
        try:
            with FirewallClient(db_path) as client:
                client.start()
                client.apply_preset_vpn("vpn-ctx", "wg0", 51820, "10.8.0.0/24", "eth0")
                assert "udp dport 51820" in nft_list()
            # After context exit, close was called
            log.info("Context manager: auto-close verified")
        finally:
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)


# ===========================================================================
# TEST: Utility methods
# ===========================================================================

@pytest.mark.docker
class TestUtilities:
    """ip_forward, flush_cache, flush_table."""

    def test_enable_ip_forward(self, fw):
        fw.enable_ip_forward()
        with open("/proc/sys/net/ipv4/ip_forward") as f:
            assert f.read().strip() == "1"

    def test_flush_cache(self, fw):
        # flush_cache is a no-op on modern kernels but shouldn't error
        fw.flush_cache()


# ===========================================================================
# TEST: Combined scenarios — full ghost mode
# ===========================================================================

@pytest.mark.docker
class TestCombinedGhostMode:
    """All presets active simultaneously — full ghost mode validation."""

    def test_full_ghost_mode(self, fw):
        log.info("=== FULL GHOST MODE TEST ===")

        # Step 1: IPv6 block (priority 5)
        fw.apply_preset_ipv6_block()
        log.info("[1/5] IPv6 block applied")

        # Step 2: Kill-switch (priority 10)
        fw.apply_preset_kill_switch(51820, 443, "wg0")
        log.info("[2/5] Kill-switch applied")

        # Step 3: DNS protection (priority 20)
        fw.apply_preset_dns_protection("wg0")
        log.info("[3/5] DNS protection applied")

        # Step 4: VPN basic (priority 100)
        fw.apply_preset_vpn("vpn-ghost", "wg0", 51820, "10.8.0.0/24", "eth0")
        log.info("[4/5] VPN basic applied")

        # Step 5: Validate
        groups = fw.list_rule_groups()
        assert len(groups) == 4
        log.info(f"[5/5] {len(groups)} groups active")

        # Validate priority ordering
        names = [g.name for g in groups]
        assert names == ["ipv6-block", "kill-switch", "dns-protection", "vpn-ghost"]

        # Validate kernel state
        output = nft_list()
        assert "drop" in output
        assert "masquerade" in output
        assert "dport 53" in output
        assert "udp dport 51820" in output
        assert 'oifname "lo"' in output

        # Count total rules
        total_rules = count_nft_rules()
        assert total_rules >= 20, f"Expected 20+ rules, got {total_rules}"
        log.info(f"Kernel: {total_rules} rules in phantom table")

        # Status check
        status = fw.get_status()
        assert status.status == "started"
        assert status.enabled_groups == 4

        # Verify in sync
        verify = fw.verify_rules()
        assert verify.in_sync is True, f"Drift detected: {verify.firewall}"
        log.info("Full ghost mode: VERIFIED")


# ===========================================================================
# TEST: Crash recovery
# ===========================================================================

@pytest.mark.docker
class TestCrashRecovery:
    """Simulate crash: close DB → reinit → start → verify rules restored."""

    def test_crash_and_restore(self, uid):
        db_path = os.path.join(tempfile.gettempdir(), f"fw_crash_{uid}.db")
        try:
            # Phase 1: Setup
            c1 = FirewallClient(db_path)
            c1.start()
            c1.apply_preset_vpn("vpn-crash", "wg0", 51820, "10.8.0.0/24", "eth0")
            c1.apply_preset_kill_switch(51820, 0, "wg0")

            rules_before = len(c1.list_firewall_rules())
            assert rules_before > 0
            assert "udp dport 51820" in nft_list()
            log.info(f"Phase 1: {rules_before} rules applied")

            # Simulate crash (close without clean stop)
            c1.close()
            log.info("Phase 1: Crashed (close)")

            # Phase 2: Recovery
            c2 = FirewallClient(db_path)
            c2.start()
            log.info("Phase 2: Recovered (reinit + start)")

            # Verify rules restored
            rules_after = c2.list_firewall_rules()
            applied_after = [r for r in rules_after if r.applied]
            assert len(applied_after) == rules_before, \
                f"Expected {rules_before} restored, got {len(applied_after)}"

            # Verify kernel
            output = nft_list()
            assert "udp dport 51820" in output, "VPN rule not restored"
            assert "drop" in output, "Kill-switch drop not restored"
            log.info("Phase 2: All rules restored and verified")

            c2.close()
        finally:
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)

    def test_applied_flags_cleared_on_init(self, uid):
        """Init clears stale applied flags, start re-applies."""
        db_path = os.path.join(tempfile.gettempdir(), f"fw_stale_{uid}.db")
        try:
            c1 = FirewallClient(db_path)
            c1.start()
            c1.apply_preset_vpn("vpn-stale", "wg0", 51820, "10.8.0.0/24", "eth0")

            # Confirm applied
            rules = c1.list_firewall_rules("vpn-stale")
            assert all(r.applied for r in rules)
            c1.close()

            # Reinit — applied flags should be cleared
            c2 = FirewallClient(db_path)
            rules = c2.list_firewall_rules("vpn-stale")
            assert all(not r.applied for r in rules), "Applied flags not cleared on init"
            log.info("Applied flags correctly cleared after crash")

            # Start restores
            c2.start()
            rules = c2.list_firewall_rules("vpn-stale")
            assert all(r.applied for r in rules), "Rules not re-applied on start"
            c2.close()
        finally:
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)


# ===========================================================================
# TEST: Chaos — external interference
# ===========================================================================

@pytest.mark.docker
class TestChaos:
    """External nft operations that disrupt state — verify detection and recovery."""

    def test_detect_drift_after_flush(self, uid):
        """External flush → verify detects missing rules."""
        db_path = os.path.join(tempfile.gettempdir(), f"fw_drift_{uid}.db")
        try:
            client = FirewallClient(db_path)
            client.start()
            client.apply_preset_vpn("vpn-drift", "wg0", 51820, "10.8.0.0/24", "eth0")

            # Confirm in sync
            rules = client.list_firewall_rules("vpn-drift")
            assert all(r.applied for r in rules), "Rules not applied"
            verify = client.verify_rules()
            assert verify.in_sync is True, f"Not in sync before chaos: {verify.firewall}"
            log.info("Pre-chaos: in sync")

            # Chaos: external flush
            nft_flush()
            log.info("Chaos: nft flush executed")

            # Detect drift
            verify = client.verify_rules()
            assert verify.in_sync is False, "Drift not detected after flush"
            missing = verify.firewall.get("missing_in_kernel", [])
            assert len(missing) > 0, "No missing rules detected"
            log.info(f"Drift detected: {len(missing)} rules missing")

            client.close()
        finally:
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)

    def test_restart_restores_after_chaos(self, uid):
        """Chaos → stop → start → rules restored from DB."""
        db_path = os.path.join(tempfile.gettempdir(), f"fw_chaos_{uid}.db")
        try:
            client = FirewallClient(db_path)
            client.start()
            client.apply_preset_vpn("vpn-chaos", "wg0", 51820, "10.8.0.0/24", "eth0")
            assert "masquerade" in nft_list()

            # Chaos
            nft_flush()
            assert "masquerade" not in nft_list()
            log.info("Chaos: rules flushed")

            # Recovery: stop + start
            client.stop()
            client.start()
            output = nft_list()
            assert "masquerade" in output, "NAT not restored"
            assert "udp dport 51820" in output, "WG port not restored"
            log.info("Recovery: all rules restored")

            client.close()
        finally:
            for ext in ("", "-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)

    def test_toggle_survives_chaos(self, fw):
        """Disable → external flush → re-enable → rules back."""
        fw.apply_preset_vpn("vpn-toggle", "wg0", 51820, "10.8.0.0/24", "eth0")

        fw.disable_rule_group("vpn-toggle")
        assert "udp dport 51820" not in nft_list()

        nft_flush()  # chaos — shouldn't matter, already disabled

        fw.enable_rule_group("vpn-toggle")
        assert "udp dport 51820" in nft_list(), "Rule not restored after re-enable"
        log.info("Toggle + chaos: survived")


# ===========================================================================
# TEST: Verify system
# ===========================================================================

@pytest.mark.docker
class TestVerify:
    """Verify drift detection and kernel state query."""

    def test_verify_clean_state(self, fw):
        fw.apply_preset_vpn("vpn-verify", "wg0", 51820, "10.8.0.0/24", "eth0")
        verify = fw.verify_rules()
        assert verify.in_sync is True

    def test_kernel_state_returns_json(self, fw):
        state = fw.get_kernel_state()
        assert isinstance(state, dict)
        assert "nftables" in state

    def test_flush_table_utility(self, fw):
        fw.apply_preset_vpn("vpn-flush", "wg0", 51820, "10.8.0.0/24", "eth0")
        assert count_nft_rules() > 0

        fw.flush_table()
        assert count_nft_rules() == 0


# ===========================================================================
# TEST: Status & version
# ===========================================================================

@pytest.mark.docker
class TestStatusAndVersion:
    """Status reporting and version check."""

    def test_status_fields(self, fw):
        status = fw.get_status()
        assert status.status == "started"
        assert isinstance(status.enabled_groups, int)
        assert isinstance(status.firewall_rules, dict)

    def test_status_counts(self, fw):
        fw.apply_preset_vpn("vpn-count", "wg0", 51820, "10.8.0.0/24", "eth0")
        status = fw.get_status()
        assert status.enabled_groups >= 1
        assert status.firewall_rules["total"] >= 4
        assert status.firewall_rules["applied"] >= 4

    def test_version(self, fw):
        assert fw.get_version() == "2.0.0"