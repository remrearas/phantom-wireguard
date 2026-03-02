"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.

Integration test — Multihop tunnel with FirewallBridge preset + crash recovery.

Topology (3 Docker containers on shared network):

                          Docker Network (fw-bridge-test-net)

    ┌──────────────┐       ┌──────────────────────────────────┐       ┌──────────────┐
    │ client       │       │ bridge (this test code)          │       │ exit-server  │
    │              │  WG   │                                  │  WG   │              │
    │ wg0          │──────►│ wg_main ────fwd────► wg_exit     │──────►│ wg0          │
    │ 10.0.1.2/24  │       │ 10.0.1.1/24       10.0.2.2/24    │       │ 10.0.2.1/24  │
    │              │       │ :51820      FirewallBridge preset│       │ :51821       │
    └──────────────┘       └──────────────────────────────────┘       └──────────────┘

    Subnets:
        10.0.1.0/24 — main (wg_main VPN server, client peers connect here)
        10.0.2.0/24 — exit (wg_exit tunnel to external exit-server)

    Ports:
        51820 — wg_main listen port (VPN server, client-facing)
        51821 — exit-server listen port (external VPN provider)

    WireGuard interfaces: OS kernel (ip link type wireguard + wg set)
    Forwarding rules:     FirewallBridge preset → Rust FFI → nftables + netlink

    Data path:
        client ──WG──► wg_main (51820) ──FORWARD──► wg_exit ──WG──► exit-server (51821)

Test phases:
    Phase 0 — YAML loading
        Verify raw YAML string == file Path loading via _load_spec.

    Phase 1 — WireGuard up + firewall preset
        Create wg_main (VPN server, :51820) + wg_exit (exit client) via OS kernel.
        Apply multihop preset via FirewallBridge → nftables + routing.
        Verify: nft rules, ip rules, ping through exit tunnel.

    Phase 2 — Crash + recovery
        Close FirewallBridge (no stop). Flush kernel state.
        Reinit from same SQLite DB, start() → rules restored.
        Verify: nft rules back, routing back, ping works.

    Phase 3 — Client connects through bridge
        Generate client keys, add peer to wg_main via wg set.
        Push wg-quick config to client container via Docker socket.
        Verify: client → wg_main → wg_exit → exit-server (end-to-end).

Requires: Docker (3 containers), orchestrated by test_runner.py.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from textwrap import dedent

import pytest
from rich.table import Table
from rich.tree import Tree

from .conftest import (
    sh, client_exec, client_write_file,
    console, _log, phase_banner, result_banner,
)

pytestmark = pytest.mark.docker


# ---------------------------------------------------------------------------
# Multihop preset — YAML spec that FirewallBridge will apply
# ---------------------------------------------------------------------------

MULTIHOP_PRESET_YAML = dedent("""\
    name: multihop-exit
    priority: 80
    metadata:
      description: Forward traffic wg_main to wg_exit

    table:
      - ensure: {id: 200, name: mh}
      - policy: {from: 10.0.1.0/24, to: 10.0.1.0/24, table: main, priority: 99}
      - policy: {from: 10.0.1.0/24, table: mh, priority: 100}
      - route:  {destination: default, device: wg_exit, table: mh}

    rules:
      - chain: forward
        action: accept
        in_iface: wg_main
        out_iface: wg_exit
      - chain: forward
        action: accept
        in_iface: wg_exit
        out_iface: wg_main
        state: established,related
      - chain: postrouting
        action: masquerade
        source: 10.0.1.0/24
        out_iface: wg_exit
""")


# ---------------------------------------------------------------------------
# Exit server config parser
# ---------------------------------------------------------------------------

def _get_exit_config() -> dict:
    """Read EXIT_SERVER_CONFIGURATION env var — raw WireGuard client config."""
    raw = os.environ.get("EXIT_SERVER_CONFIGURATION", "")
    if not raw:
        pytest.skip("EXIT_SERVER_CONFIGURATION not set (provided by test_runner)")

    result = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if key == "PrivateKey":
            result["client_priv"] = val
        elif key == "Address":
            result["client_ip"] = val
        elif key == "PublicKey":
            result["server_pub"] = val
        elif key == "PresharedKey":
            result["psk"] = val
        elif key == "Endpoint":
            result["endpoint"] = val
        elif key == "AllowedIPs":
            result["allowed_ips"] = val

    if "endpoint" not in result or "client_priv" not in result:
        pytest.skip("EXIT_SERVER_CONFIGURATION incomplete")

    _log("exit", "config: endpoint=%s, client_ip=%s" % (
        result["endpoint"], result["client_ip"]))
    return result


# ---------------------------------------------------------------------------
# WireGuard helpers (OS kernel — wg-quick / wg set)
# ---------------------------------------------------------------------------

def _wg_genkey() -> tuple[str, str]:
    """Generate WireGuard keypair via OS tools. Returns (privkey, pubkey) base64."""
    priv = subprocess.run(
        ["wg", "genkey"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    pub = subprocess.run(
        ["wg", "pubkey"], input=priv, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return priv, pub


def _wg_genpsk() -> str:
    """Generate WireGuard preshared key via OS tools. Returns base64."""
    return subprocess.run(
        ["wg", "genpsk"], capture_output=True, text=True, check=True,
    ).stdout.strip()


def _setup_wg_main(workdir: str) -> dict:
    """Create wg_main — VPN server interface (10.0.1.1/24, listen :51820)."""
    _log("bridge", "Setting up wg_main (VPN server)")

    priv, pub = _wg_genkey()
    priv_file = os.path.join(workdir, "wg_main.key")
    with open(priv_file, "w") as f:
        f.write(priv)

    sh("ip link add wg_main type wireguard")
    sh(f"wg set wg_main private-key {priv_file} listen-port 51820")
    sh("ip addr add 10.0.1.1/24 dev wg_main")
    sh("ip link set wg_main up")

    _log("bridge", "wg_main UP -- 10.0.1.1/24, listen :51820, pub=%s" % pub[:16])
    return {"priv": priv, "pub": pub}


def _setup_wg_exit(workdir: str, exit_cfg: dict):
    """Create wg_exit — exit tunnel client using provider-supplied config (→ exit-server :51821)."""
    _log("bridge", "Setting up wg_exit (exit client)")

    priv_file = os.path.join(workdir, "wg_exit.key")
    with open(priv_file, "w") as f:
        f.write(exit_cfg["client_priv"])

    psk_file = os.path.join(workdir, "wg_exit.psk")
    with open(psk_file, "w") as f:
        f.write(exit_cfg["psk"])

    sh("ip link add wg_exit type wireguard")
    sh(f"wg set wg_exit private-key {priv_file}")
    sh(f"wg set wg_exit peer {exit_cfg['server_pub']} "
       f"preshared-key {psk_file} "
       f"endpoint {exit_cfg['endpoint']} "
       f"allowed-ips {exit_cfg['allowed_ips']} "
       f"persistent-keepalive 25")
    sh(f"ip addr add {exit_cfg['client_ip']} dev wg_exit")
    sh("ip link set wg_exit up")

    _log("bridge", "wg_exit UP -- %s --> %s" % (exit_cfg["client_ip"], exit_cfg["endpoint"]))


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def _ping(target: str) -> bool:
    """3 pings, 2s timeout. Returns True on success."""
    r = sh(f"ping -c3 -W2 {target}", check=False)
    return r.returncode == 0


def _nft_list() -> str:
    """Get full nftables phantom table output."""
    r = sh("nft list table inet phantom", check=False)
    return r.stdout or ""


def _nft_list_json() -> dict:
    """Get nftables phantom table as JSON."""
    r = sh("nft -j list table inet phantom", check=False)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}


def _count_nft_rules() -> int:
    """Count rules in kernel phantom table."""
    data = _nft_list_json()
    return sum(1 for item in data.get("nftables", []) if "rule" in item)


def _ip_rules() -> str:
    """Get ip rule list output."""
    r = sh("ip rule show", check=False)
    return r.stdout or ""


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _cleanup(workdir: str):
    """Tear down WireGuard interfaces and temp directory."""
    sh("ip link delete wg_main", check=False)
    sh("ip link delete wg_exit", check=False)
    if os.path.isdir(workdir):
        shutil.rmtree(workdir)


# ===========================================================================
# TEST
# ===========================================================================

class TestMultihopTunnel:

    def test_full_lifecycle(self):
        """Full lifecycle: preset apply, crash recovery, client multihop.

        Phase 1: WireGuard up + firewall preset + verify kernel + ping
        Phase 2: Crash + recovery from DB + verify restored
        Phase 3: Client connects through bridge + end-to-end ping
        """
        workdir = tempfile.mkdtemp(prefix="fw-bridge-test-")
        db_path = os.path.join(workdir, "firewall.db")
        preset_file = Path(os.path.join(workdir, "multihop.yaml"))

        # Write YAML preset to file
        preset_file.write_text(MULTIHOP_PRESET_YAML, encoding="utf-8")

        # ---- Topology overview ----
        console.print()
        tree = Tree("Docker Network (fw-bridge-test-net)")
        bridge_node = tree.add("BRIDGE (fw-bridge) -- test host + firewall")
        bridge_node.add("wg_main  10.0.1.1/24  :51820")
        bridge_node.add("wg_exit  10.0.2.2/24  --> EXIT :51821")
        bridge_node.add("FirewallBridge + SQLite")
        exit_node = tree.add("EXIT (fw-exit-server)")
        exit_node.add("wg0  10.0.2.1/24  :51821")
        client_node = tree.add("CLIENT (fw-client)")
        client_node.add("wg0  10.0.1.2/24")
        console.print(tree)
        console.print()

        try:
            exit_cfg = _get_exit_config()

            # ==============================================================
            # PHASE 0: Verify raw YAML == file YAML
            # ==============================================================
            phase_banner(0, "Verify YAML String == File Path Loading")

            from firewall_bridge.presets import _load_spec

            spec_from_file = _load_spec(preset_file)
            spec_from_raw = _load_spec(MULTIHOP_PRESET_YAML)
            assert spec_from_file == spec_from_raw, \
                "Raw YAML string and file Path must produce identical spec"
            _log("verify", "_load_spec(Path) == _load_spec(str): OK")

            _log("verify", "PHASE 0 PASSED")

            # ==============================================================
            # PHASE 1: WireGuard up + firewall preset
            # ==============================================================
            phase_banner(1, "Tunnel Setup + Firewall Preset")

            # ---- Step 1.1: Create WireGuard interfaces via OS kernel ----
            main_keys = _setup_wg_main(workdir)
            _setup_wg_exit(workdir, exit_cfg)
            sh("sysctl -w net.ipv4.ip_forward=1")

            _log("bridge", "WireGuard interfaces created (OS kernel)")

            # ---- Step 1.2: Wait for WireGuard handshake ----
            time.sleep(5)

            # ---- Step 1.3: Verify exit tunnel connectivity ----
            assert _ping("10.0.1.1"), "wg_main not reachable"
            _log("verify", "BRIDGE <--> BRIDGE  ping 10.0.1.1 (wg_main): OK")
            assert _ping("10.0.2.1"), "exit-server not reachable via wg_exit"
            _log("verify", "BRIDGE  --> EXIT    ping 10.0.2.1 (wg_exit): OK")

            # ---- Step 1.4: Apply multihop preset via FirewallBridge ----
            from firewall_bridge import FirewallBridge
            from firewall_bridge.presets import apply_preset

            bridge = FirewallBridge(db_path)
            bridge.start()
            group = apply_preset(bridge, MULTIHOP_PRESET_YAML)
            _log("bridge", "Multihop preset applied: %s (raw YAML string)" % group.name)

            # ---- Step 1.5: Verify nftables rules in kernel ----
            nft_output = _nft_list()
            assert "wg_main" in nft_output, "wg_main missing in nft rules"
            assert "wg_exit" in nft_output, "wg_exit missing in nft rules"
            assert "masquerade" in nft_output, "masquerade missing in nft rules"

            rule_count = _count_nft_rules()
            assert rule_count >= 3, f"Expected 3+ nft rules, got {rule_count}"
            _log("verify", "nftables verified: %d rules in phantom table" % rule_count)

            # ---- Step 1.6: Verify routing rules in kernel ----
            ip_output = _ip_rules()
            assert "10.0.1.0/24" in ip_output, "policy route missing"
            _log("verify", "Routing policy verified")

            # ---- Step 1.7: Verify DB state ----
            fw_rules = bridge.list_firewall_rules("multihop-exit")
            rt_rules = bridge.list_routing_rules("multihop-exit")
            assert len(fw_rules) == 3, f"Expected 3 fw rules, got {len(fw_rules)}"
            assert len(rt_rules) == 4, f"Expected 4 rt rules, got {len(rt_rules)}"
            assert all(r.applied for r in fw_rules), "Not all fw rules applied"
            assert bridge.get_state() == "started"

            applied_fw = sum(1 for r in fw_rules if r.applied)
            applied_rt = sum(1 for r in rt_rules if r.applied)
            table = Table(title="DB State", show_lines=False)
            table.add_column("Type")
            table.add_column("Count", justify="right")
            table.add_column("Applied", justify="center")
            table.add_row("Firewall rules", str(len(fw_rules)), f"{applied_fw}/{len(fw_rules)}")
            table.add_row("Routing rules", str(len(rt_rules)), f"{applied_rt}/{len(rt_rules)}")
            table.add_row("State", "", bridge.get_state())
            console.print(table)

            _log("verify", "PHASE 1 PASSED")

            # ==============================================================
            # PHASE 2: Crash + recovery
            # ==============================================================
            phase_banner(2, "Crash + Recovery from DB")

            # ---- Step 2.1: Simulate crash (close without stop) ----
            _log("bridge", "bridge.close() -- crash simulation (no stop)")
            bridge.close()

            # ---- Step 2.2: Flush kernel state (simulate reboot) ----
            console.print("  ~~>  nft flush + delete table")
            sh("nft flush table inet phantom", check=False)
            sh("nft delete table inet phantom", check=False)
            console.print("  ~~>  kernel state wiped")

            # ---- Step 2.3: Reinit from same DB ----
            _log("bridge", "FirewallBridge(db_path) -- reinit from same DB")
            bridge2 = FirewallBridge(db_path)
            assert bridge2.get_state() == "stopped", "State should be stopped after reinit"
            _log("db", "state=stopped (reinit from existing DB)")

            # ---- Step 2.4: Start restores rules from DB ----
            console.print("  ==>  bridge.start() -- restoring from DB")
            bridge2.start()
            _log("bridge", "Rules restored from DB")

            # ---- Step 2.5: Verify nftables restored ----
            nft_output = _nft_list()
            assert "wg_main" in nft_output, "wg_main not restored"
            assert "wg_exit" in nft_output, "wg_exit not restored"
            assert "masquerade" in nft_output, "masquerade not restored"

            rule_count = _count_nft_rules()
            assert rule_count >= 3, f"Expected 3+ restored rules, got {rule_count}"
            _log("verify", "nftables restored: %d rules" % rule_count)

            # ---- Step 2.6: Verify routing restored ----
            ip_output = _ip_rules()
            assert "10.0.1.0/24" in ip_output, "policy route not restored"
            _log("verify", "Routing policy restored")

            # ---- Step 2.7: Verify DB applied flags ----
            fw_rules = bridge2.list_firewall_rules("multihop-exit")
            assert all(r.applied for r in fw_rules), "Not all rules re-applied"
            _log("db", "Applied flags verified")

            # ---- Step 2.8: Verify connectivity after recovery ----
            assert _ping("10.0.2.1"), "exit-server not reachable after recovery"
            _log("verify", "BRIDGE  --> EXIT    ping 10.0.2.1: OK (post-recovery)")

            _log("verify", "PHASE 2 PASSED")

            # ==============================================================
            # PHASE 3: Client connects through bridge
            # ==============================================================
            phase_banner(3, "Client Connects Through Bridge")

            # ---- Step 3.1: Generate client keys ----
            client_priv, client_pub = _wg_genkey()
            client_psk = _wg_genpsk()
            _log("client", "Keys generated")

            # ---- Step 3.2: Add client peer to wg_main ----
            psk_file = os.path.join(workdir, "client.psk")
            with open(psk_file, "w") as f:
                f.write(client_psk)
            sh(f"wg set wg_main peer {client_pub} "
               f"preshared-key {psk_file} "
               f"allowed-ips 10.0.1.2/32 "
               f"persistent-keepalive 25")
            _log("bridge", "Client peer added to wg_main")

            # ---- Step 3.3: Build client config ----
            r = sh("hostname -i", check=False)
            bridge_ip = (r.stdout or "").strip()

            client_conf = dedent(f"""\
                [Interface]
                PrivateKey = {client_priv}
                Address = 10.0.1.2/24

                [Peer]
                PublicKey = {main_keys['pub']}
                PresharedKey = {client_psk}
                AllowedIPs = 10.0.1.0/24, 10.0.2.0/24
                Endpoint = {bridge_ip}:51820
                PersistentKeepalive = 1
            """)
            _log("client", "Config built (endpoint=%s:51820)" % bridge_ip)

            # ---- Step 3.4: Push config to client container ----
            client_write_file("/etc/wireguard/wg0.conf", client_conf)
            _log("client", "Config pushed to client container")

            # ---- Step 3.5: Start WireGuard on client ----
            client_exec("wg-quick up wg0")
            _log("client", "wg-quick up wg0")

            # ---- Step 3.6: Wait for handshake ----
            time.sleep(5)

            # ---- Step 3.7: Verify client → wg_main ----
            rc, _ = client_exec("ping -c3 -W2 10.0.1.1", check=False)
            assert rc == 0, "client -> wg_main failed"
            _log("verify", "CLIENT  --> BRIDGE  ping 10.0.1.1 (wg_main): OK")

            # ---- Step 3.8: Verify client → exit-server (end-to-end multihop) ----
            rc, _ = client_exec("ping -c3 -W2 10.0.2.1", check=False)
            assert rc == 0, "client -> exit-server multihop failed"
            _log("verify", "CLIENT  --> EXIT    ping 10.0.2.1 (multihop): OK")

            # ---- Step 3.9: Show final state ----
            client_exec("wg show wg0", check=False)
            sh("wg show wg_main", check=False)
            sh("nft list table inet phantom", check=False)

            bridge2.close()

            _log("verify", "PHASE 3 PASSED")
            result_banner()

        finally:
            _cleanup(workdir)
