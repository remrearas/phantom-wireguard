"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration test — Ghost Mode tunnel via wstunnel + WireGuard multihop.

Topology (3 Docker containers on shared network):

                              Docker Network (ws-bridge-test-net)

    ┌───────────────────┐       ┌──────────────────────────────────┐       ┌──────────────┐
    │ client            │       │ bridge (this test code)          │       │ exit-server  │
    │                   │  WSS  │                                  │  WG   │              │
    │ wstunnel client   │──────►│ WstunnelBridge (FFI server)      │       │ wg0          │
    │ wss://BRIDGE:443  │       │ wss://[::]:443  restrict_to=     │       │ 10.0.2.1/24  │
    │                   │       │ 127.0.0.1:51820                  │       │ :51821       │
    │ wg0 10.0.1.2/24   │       │                                  │       │              │
    │ Endpoint=         │       │ wg_main ────fwd────► wg_exit     │──────►│              │
    │  127.0.0.1:51820  │       │ 10.0.1.1/24 :51820  10.0.2.2/24  │       │              │
    │ (via wstunnel)    │       │ table 100 + NAT + ghost          │       │ ip_fwd + NAT │
    └───────────────────┘       └──────────────────────────────────┘       └──────────────┘

    Ghost Mode data path:
        client ──wstunnel──► BRIDGE:443 ──► 127.0.0.1:51820 (WG)
               ──► wg_main ──FORWARD──► wg_exit ──WG──► exit-server

    Ghost firewall (port 51820 invisible to network):
        iptables : INPUT tcp/443 ACCEPT, INPUT udp/51820 src=127.0.0.1 ACCEPT, DROP

    Forwarding rules:
        ip rule  : 10.0.1.0/24 → routing table 100 → default via wg_exit
        iptables : FORWARD wg_main ↔ wg_exit (stateful), MASQUERADE on wg_exit

    Exit server config delivered via EXIT_SERVER_CONFIGURATION env var
    (standard WireGuard client config — external VPN service provider format).

Test phases:
    Phase 1 — WireGuard + wstunnel server + ghost firewall
        Create wg_main (VPN server) + wg_exit (exit client), set up multihop
        forwarding. Start WstunnelBridge via FFI, apply ghost firewall.
        Verify ping to exit (10.0.2.1), DB state == "started".

    Phase 2 — Crash recovery
        Close WstunnelBridge, reopen from same DB (no config replay).
        Verify is_running(), DB config matches, WG topology intact.

    Phase 3 — Client connects via wstunnel (Ghost Mode E2E)
        Start wstunnel client on client container, bring up wg0 through
        tunnel. Verify end-to-end multihop:
        client(10.0.1.2) → wg_main → wg_exit → exit-server(10.0.2.1).

Requires: Docker (3 containers), orchestrated by test_runner.py.
"""

import os
import shutil
import subprocess
import tempfile
import time
import uuid

import pytest

from wstunnel_bridge.types import BridgeError

from .conftest import (
    _log, phase_banner, result_banner,
    sh, client_exec, client_write_file,
)

pytestmark = pytest.mark.docker


# ============================================================================
# Helpers
# ============================================================================

def _parse_wg_config(conf: str) -> dict:
    """Parse standard WireGuard client config into dict."""
    result = {}
    for line in conf.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()

        if key == "PrivateKey":
            result["private_key"] = val
        elif key == "Address":
            result["address"] = val
        elif key == "PublicKey":
            result["public_key"] = val
        elif key == "PresharedKey":
            result["preshared_key"] = val
        elif key == "Endpoint":
            result["endpoint"] = val
        elif key == "AllowedIPs":
            result["allowed_ips"] = val
        elif key == "PersistentKeepalive":
            result["persistent_keepalive"] = val
    return result


def _get_exit_config() -> dict:
    """Read EXIT_SERVER_CONFIGURATION env var — raw WireGuard client config."""
    raw = os.environ.get("EXIT_SERVER_CONFIGURATION", "")
    if not raw:
        pytest.skip("EXIT_SERVER_CONFIGURATION not set (provided by test_runner)")

    cfg = _parse_wg_config(raw)
    if "endpoint" not in cfg or "private_key" not in cfg:
        pytest.skip("EXIT_SERVER_CONFIGURATION incomplete")

    _log("exit", f"endpoint={cfg['endpoint']}, address={cfg.get('address', '?')}")
    return cfg


def _wg_genkey() -> tuple[str, str]:
    """Generate WireGuard keypair. Returns (private_key, public_key)."""
    priv = subprocess.run(
        "wg genkey", shell=True, capture_output=True, text=True, check=True,
    ).stdout.strip()
    pub = subprocess.run(
        f"echo {priv} | wg pubkey", shell=True, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return priv, pub


def _wg_genpsk() -> str:
    """Generate WireGuard preshared key."""
    return subprocess.run(
        "wg genpsk", shell=True, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _write_key(workdir: str, name: str, value: str) -> str:
    """Write key to temp file, return path. wg set requires file paths."""
    path = os.path.join(workdir, name)
    with open(path, "w") as f:
        f.write(value)
    os.chmod(path, 0o600)
    return path


def _setup_wg_main(workdir: str) -> dict:
    """Create wg_main — bridge WireGuard server (10.0.1.1/24, listen :51820)."""
    _log("bridge", "Setting up wg_main (10.0.1.1/24, :51820)")
    priv, pub = _wg_genkey()
    priv_file = _write_key(workdir, "wg_main.key", priv)

    sh("ip link add wg_main type wireguard")
    sh(f"wg set wg_main listen-port 51820 private-key {priv_file}")
    sh("ip addr add 10.0.1.1/24 dev wg_main")
    sh("ip link set wg_main up")

    _log("bridge", f"wg_main up: pub={pub[:12]}...")
    return {"priv": priv, "pub": pub}


def _setup_wg_exit(workdir: str, exit_cfg: dict) -> None:
    """Create wg_exit — exit tunnel client (10.0.2.2/24) from exit server config."""
    _log("bridge", "Setting up wg_exit (exit server client)")

    priv_file = _write_key(workdir, "wg_exit.key", exit_cfg["private_key"])

    sh("ip link add wg_exit type wireguard")

    # Build wg set command
    wg_cmd = f"wg set wg_exit private-key {priv_file}"
    wg_cmd += f" peer {exit_cfg['public_key']}"
    wg_cmd += f" endpoint {exit_cfg['endpoint']}"
    wg_cmd += f" allowed-ips {exit_cfg['allowed_ips']}"
    wg_cmd += " persistent-keepalive 25"
    if exit_cfg.get("preshared_key"):
        psk_file = _write_key(workdir, "wg_exit.psk", exit_cfg["preshared_key"])
        wg_cmd += f" preshared-key {psk_file}"
    sh(wg_cmd)

    sh(f"ip addr add {exit_cfg['address']} dev wg_exit")
    sh("ip link set wg_exit up")

    _log("bridge", f"wg_exit up: -> {exit_cfg['endpoint']}")


def _setup_multihop() -> None:
    """Set up policy routing + iptables for wg_main -> wg_exit forwarding."""
    _log("bridge", "Setting up multihop forwarding")
    sh("sysctl -w net.ipv4.ip_forward=1")
    sh("ip rule add from 10.0.1.0/24 to 10.0.1.0/24 table main priority 99")
    sh("ip rule add from 10.0.1.0/24 table 100 priority 100")
    sh("ip route add default dev wg_exit table 100")
    sh("iptables -A FORWARD -i wg_main -o wg_exit -j ACCEPT")
    sh("iptables -A FORWARD -i wg_exit -o wg_main -m state --state RELATED,ESTABLISHED -j ACCEPT")
    sh("iptables -t nat -A POSTROUTING -s 10.0.1.0/24 -o wg_exit -j MASQUERADE")
    _log("bridge", "wg_main(10.0.1.0/24) -> table 100 -> wg_exit")


def _apply_ghost_firewall() -> None:
    """Ghost firewall: 443 ACCEPT, 51820 localhost-only, DROP external."""
    _log("bridge", "Applying ghost firewall rules")
    sh("iptables -A INPUT -p tcp --dport 443 -j ACCEPT")
    sh("iptables -A INPUT -p udp --dport 51820 -s 127.0.0.1 -j ACCEPT")
    sh("iptables -A INPUT -p udp --dport 51820 -j DROP")


def _ping(target: str) -> bool:
    """Send 3 ICMP pings with 2s timeout."""
    r = sh(f"ping -c3 -W2 {target}", check=False)
    return r.returncode == 0


def _cleanup(workdir: str) -> None:
    """Tear down WireGuard interfaces, forwarding rules, firewall, temp dir."""
    sh("ip link delete wg_main", check=False)
    sh("ip link delete wg_exit", check=False)
    sh("iptables -F FORWARD", check=False)
    sh("iptables -F INPUT", check=False)
    sh("iptables -t nat -F POSTROUTING", check=False)
    sh("ip rule del from 10.0.1.0/24 to 10.0.1.0/24 table main priority 99", check=False)
    sh("ip rule del from 10.0.1.0/24 table 100 priority 100", check=False)
    sh("ip route flush table 100", check=False)
    if os.path.isdir(workdir):
        shutil.rmtree(workdir)


# ============================================================================
# Test
# ============================================================================

class TestGhostModeTunnel:

    def test_full_lifecycle(self):
        """Full lifecycle: wstunnel server + WG multihop, crash recovery, client E2E.

        Phase 1: WireGuard + wstunnel server + ghost firewall
        Phase 2: Crash recovery — close + reopen from DB
        Phase 3: Client connects via wstunnel (Ghost Mode E2E)
        """
        workdir = tempfile.mkdtemp(prefix="ws-bridge-test-")
        secret = uuid.uuid4().hex
        db_path = os.path.join(workdir, "bridge.db")
        bridge = None
        bridge2 = None

        try:
            exit_cfg = _get_exit_config()

            # ================================================================
            # Phase 1: WireGuard + wstunnel server + ghost firewall
            # ================================================================
            phase_banner(1, "WireGuard + wstunnel server + ghost firewall")

            # WireGuard interfaces
            main_keys = _setup_wg_main(workdir)
            _setup_wg_exit(workdir, exit_cfg)
            _setup_multihop()

            _log("bridge", "Waiting for WG handshake...")
            time.sleep(5)

            _log("verify", "Ping wg_main 10.0.1.1")
            assert _ping("10.0.1.1"), "wg_main not reachable"

            _log("verify", "Ping exit 10.0.2.1")
            assert _ping("10.0.2.1"), "exit not reachable via wg_exit"

            # WstunnelBridge — configure + start
            from wstunnel_bridge import WstunnelBridge

            _log("bridge", "Starting WstunnelBridge (FFI server)")
            bridge = WstunnelBridge(db_path)
            bridge.configure(
                bind_url="wss://[::]:443",
                restrict_to="127.0.0.1:51820",
                restrict_path_prefix=secret,
                tls_certificate="/certs/cert.pem",
                tls_private_key="/certs/key.pem",
            )
            bridge.start()

            assert bridge.is_running(), "wstunnel server not running after start"
            _log("bridge", "WstunnelBridge started (wss://[::]:443)")

            # Ghost firewall
            _apply_ghost_firewall()

            # Verify DB state
            from wstunnel_bridge import WstunnelDB
            db = WstunnelDB(db_path)
            assert db.get_state() == "started", "DB state != started"
            cfg = db.get_config()
            assert cfg.bind_url == "wss://[::]:443"
            assert cfg.restrict_to == "127.0.0.1:51820"
            db.close()

            _log("verify", "Phase 1: DB state=started, is_running=True")
            _log("bridge", "PHASE 1 PASSED")

            # ================================================================
            # Phase 2: Crash recovery
            # ================================================================
            phase_banner(2, "Crash recovery")

            _log("bridge", "Closing WstunnelBridge (simulating crash)")
            bridge.close()
            bridge = None

            _log("bridge", "Reopening WstunnelBridge from same DB")
            bridge2 = WstunnelBridge(db_path)
            bridge2.start()

            assert bridge2.is_running(), "wstunnel server not running after recovery"
            _log("verify", "is_running=True after recovery")

            # Verify DB config persisted
            db = WstunnelDB(db_path)
            cfg = db.get_config()
            assert cfg.bind_url == "wss://[::]:443"
            assert cfg.restrict_to == "127.0.0.1:51820"
            assert cfg.restrict_path_prefix == secret
            assert cfg.tls_certificate == "/certs/cert.pem"
            assert cfg.tls_private_key == "/certs/key.pem"
            db.close()

            _log("verify", "DB config matches original")
            _log("bridge", "PHASE 2 PASSED")

            # ================================================================
            # Phase 3: Client connects via wstunnel (Ghost Mode E2E)
            # ================================================================
            phase_banner(3, "Client connects via wstunnel (Ghost Mode E2E)")

            # Generate client WG keys
            client_priv, client_pub = _wg_genkey()
            client_psk = _wg_genpsk()

            # Add client peer to wg_main
            _log("bridge", "Adding client peer to wg_main")
            psk_file = _write_key(workdir, "client.psk", client_psk)
            sh(f"wg set wg_main peer {client_pub} "
               f"preshared-key {psk_file} "
               f"allowed-ips 10.0.1.2/32")

            # Get bridge container IP
            bridge_ip = subprocess.run(
                "hostname -I", shell=True, capture_output=True, text=True,
            ).stdout.strip().split()[0]
            _log("bridge", f"Bridge container IP: {bridge_ip}")

            # Start wstunnel client on client container (background)
            _log("client", "Starting wstunnel client")
            wstunnel_cmd = (
                f"nohup wstunnel client "
                f"--http-upgrade-path-prefix {secret} "
                f"-L udp://127.0.0.1:51820:127.0.0.1:51820 "
                f"wss://{bridge_ip}:443 "
                f">/tmp/wstunnel.log 2>&1 & echo $!"
            )
            client_exec(wstunnel_cmd, check=False)

            _log("client", "Waiting for wstunnel tunnel...")
            time.sleep(3)

            # Diagnostics: verify wstunnel process + tunnel
            _log("client", "wstunnel process check:")
            client_exec("ps aux | grep wstunnel | grep -v grep || echo NO_WSTUNNEL", check=False)
            _log("client", "wstunnel log:")
            client_exec("cat /tmp/wstunnel.log 2>/dev/null || echo NO_LOG", check=False)
            _log("client", "UDP listeners:")
            client_exec("ss -ulnp 2>/dev/null || netstat -ulnp 2>/dev/null || echo NO_SS", check=False)

            # Write WG config + bring up on client
            client_wg_conf = (
                f"[Interface]\n"
                f"PrivateKey = {client_priv}\n"
                f"Address = 10.0.1.2/24\n"
                f"\n"
                f"[Peer]\n"
                f"PublicKey = {main_keys['pub']}\n"
                f"PresharedKey = {client_psk}\n"
                f"Endpoint = 127.0.0.1:51820\n"
                f"AllowedIPs = 10.0.1.0/24, 10.0.2.0/24\n"
                f"PersistentKeepalive = 25\n"
            )
            _log("client", "Writing WG config + wg-quick up")
            client_exec("mkdir -p /etc/wireguard")
            client_write_file("/etc/wireguard/wg0.conf", client_wg_conf)
            client_exec("wg-quick up wg0")

            _log("client", "Waiting for WG handshake...")
            time.sleep(5)

            # Diagnostics: WG state before assertion
            _log("client", "wg show wg0:")
            client_exec("wg show wg0", check=False)
            _log("client", "wstunnel log (post-handshake):")
            client_exec("tail -20 /tmp/wstunnel.log 2>/dev/null || echo NO_LOG", check=False)

            # Verify: client -> bridge wg_main
            _log("verify", "Client ping 10.0.1.1 (bridge wg_main)")
            rc, _ = client_exec("ping -c3 -W2 10.0.1.1", check=False)
            assert rc == 0, "client -> wg_main failed"

            # Verify: client -> exit-server (multihop)
            _log("verify", "Client ping 10.0.2.1 (exit-server, multihop)")
            rc, _ = client_exec("ping -c3 -W2 10.0.2.1", check=False)
            assert rc == 0, "client -> exit failed (multihop)"

            _log("bridge", "PHASE 3 PASSED")

            # Cleanup bridge
            bridge2.close()
            bridge2 = None

            result_banner(passed=True)

        finally:
            if bridge is not None:
                try:
                    bridge.close()
                except (BridgeError, OSError):
                    pass
            if bridge2 is not None:
                try:
                    bridge2.close()
                except (BridgeError, OSError):
                    pass
            client_exec("wg-quick down wg0", check=False)
            _cleanup(workdir)
