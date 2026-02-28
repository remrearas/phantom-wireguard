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

Network namespace tunnel + multihop exit tests.

Topology 1 — Basic tunnel:
    Main ns (BridgeClient)              ns-client (kernel WG)
    wg-srv 10.100.0.1  ←── veth ──→  wg-cli 10.100.0.2

Topology 2 — Multihop with exit:
    Main ns                  ns-client              ns-exit
    wg-srv 10.100.0.1  ←──→  wg-cli 10.100.0.2     wg-exit 10.200.0.1
    wg-mh  10.200.0.2  ←────────── veth ──────────→  (kernel WG exit)

Requires: --docker flag (privileged container with NET_ADMIN)
"""

import base64
import json
import logging
import os
import subprocess
import tempfile
import time
import uuid

import pytest

from wireguard_go_bridge.client import BridgeClient
from wireguard_go_bridge.types import WireGuardError

log = logging.getLogger("netns")


# ============================================================================
# Helpers
# ============================================================================

def _run(cmd: str, check: bool = True, label: str = "") -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    tag = f"[{label}] " if label else ""
    if r.returncode != 0:
        log.debug(f"{tag}FAIL({r.returncode}): {cmd}")
        if r.stderr.strip():
            log.debug(f"  stderr: {r.stderr.strip()[:300]}")
        if check:
            r.check_returncode()
    else:
        log.debug(f"{tag}OK: {cmd}")
    return r


def _ns(ns: str, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(f"ip netns exec {ns} {cmd}", check=check, label=ns)


def _wait_iperf(ns: str = "", timeout: int = 10):
    prefix = f"ip netns exec {ns} " if ns else ""
    for _ in range(timeout * 10):
        r = _run(f"{prefix}ss -tlp 'sport = 5201'", check=False)
        if "iperf3" in r.stdout:
            return
        time.sleep(0.1)
    raise TimeoutError("iperf3 not ready")


# ============================================================================
# Basic tunnel fixture
# ============================================================================

@pytest.fixture(scope="module")
def tunnel():
    """BridgeClient server (main ns) ↔ kernel WG client (netns)."""
    uid = uuid.uuid4().hex[:8]
    ns = f"nsc-{uid}"
    srv_iface = f"wgs{uid[:4]}"
    cli_iface = f"wgc{uid[:4]}"
    vs = f"vs-{uid[:6]}"
    vc = f"vc-{uid[:6]}"
    db_path = os.path.join(tempfile.gettempdir(), f"netns_{uid}.db")

    log.info(f"=== TUNNEL SETUP (uid={uid}) ===")

    # Cleanup
    _run(f"ip netns del {ns}", check=False)
    _run(f"ip link del {vs}", check=False)

    # Step 1: Namespace + veth
    log.info(f"Step 1: Creating namespace {ns} + veth ({vs} ↔ {vc})")
    _run(f"ip netns add {ns}")
    _ns(ns, "ip link set up dev lo")
    _run(f"ip link add {vs} type veth peer name {vc}")
    _run(f"ip link set {vc} netns {ns}")
    _run(f"ip addr add 172.16.1.1/24 dev {vs}")
    _run(f"ip link set {vs} up")
    _ns(ns, f"ip addr add 172.16.1.2/24 dev {vc}")
    _ns(ns, f"ip link set {vc} up")

    # Step 2: BridgeClient server
    log.info(f"Step 2: BridgeClient init (iface={srv_iface}, port=51820)")
    bridge = BridgeClient(db_path, srv_iface, 51820, log_level=0)
    bridge.setup(endpoint="172.16.1.1:51820", network="10.100.0.0/24")
    bridge.start()
    log.info(f"  Bridge status: {bridge.get_status()['status']}")

    # Step 3: Assign IP + UP
    log.info(f"Step 3: Server interface IP + UP")
    _run(f"ip addr add 10.100.0.1/24 dev {srv_iface}")
    _run(f"ip link set up dev {srv_iface}")

    # Step 4: Add client
    log.info("Step 4: Adding client")
    client = bridge.add_client()
    device = bridge.get_device_info()
    log.info(f"  Server pub: {device.public_key[:20]}...")
    log.info(f"  Client ip={client.allowed_ip} pub={client.public_key[:20]}...")

    # Step 5: Kernel WG client in netns
    log.info(f"Step 5: Kernel WG client in {ns} (iface={cli_iface})")
    _ns(ns, f"ip link add {cli_iface} type wireguard")
    _ns(ns, f"ip addr add 10.100.0.2/24 dev {cli_iface}")

    priv_b64 = base64.b64encode(bytes.fromhex(client.private_key)).decode()
    srv_pub_b64 = base64.b64encode(bytes.fromhex(device.public_key)).decode()
    psk_b64 = base64.b64encode(bytes.fromhex(client.preshared_key)).decode()

    priv_path = os.path.join(tempfile.gettempdir(), f"priv_{uid}")
    psk_path = os.path.join(tempfile.gettempdir(), f"psk_{uid}")
    for p, v in [(priv_path, priv_b64), (psk_path, psk_b64)]:
        with open(p, "w") as f:
            f.write(v)
        os.chmod(p, 0o600)

    _ns(ns, (
        f"wg set {cli_iface} private-key {priv_path} "
        f"peer {srv_pub_b64} preshared-key {psk_path} "
        f"endpoint 172.16.1.1:51820 allowed-ips 10.100.0.0/24 "
        f"persistent-keepalive 25"
    ))
    _ns(ns, f"ip link set up dev {cli_iface}")

    # Step 6: Wait for handshake
    log.info("Step 6: Waiting for WG handshake...")
    time.sleep(2)
    _ns(ns, "ping -c 1 -W 3 10.100.0.1", check=False)
    time.sleep(1)

    r = _ns(ns, f"wg show {cli_iface}", check=False)
    handshake_ok = "latest handshake" in r.stdout
    log.info(f"  Handshake: {'OK' if handshake_ok else 'NOT YET'}")

    log.info("=== TUNNEL READY ===")

    info = {
        "ns": ns, "server_ip": "10.100.0.1", "client_ip": "10.100.0.2",
        "srv_iface": srv_iface, "cli_iface": cli_iface, "bridge": bridge,
    }

    yield info

    log.info("=== TUNNEL TEARDOWN ===")
    try:
        bridge.stop()
    except WireGuardError:
        pass
    try:
        bridge.close()
    except WireGuardError:
        pass
    pids = _run(f"ip netns pids {ns}", check=False).stdout.strip()
    if pids:
        _run(f"kill {pids}", check=False)
    _run(f"ip netns del {ns}", check=False)
    _run(f"ip link del {vs}", check=False)
    for p in [db_path, priv_path, psk_path]:
        if os.path.exists(p):
            os.remove(p)


# ============================================================================
# Basic tunnel tests
# ============================================================================

@pytest.mark.docker
class TestNetNSTunnel:

    def test_ping_client_to_server(self, tunnel):
        log.info("TEST: ping client → server (10.100.0.2 → 10.100.0.1)")
        r = _ns(tunnel["ns"], f"ping -c 5 -W 2 {tunnel['server_ip']}", check=False)
        log.info(f"  Result: {r.stdout.strip().split(chr(10))[-1]}")
        assert r.returncode == 0, f"Ping failed:\n{r.stdout}\n{r.stderr}"

    def test_ping_server_to_client(self, tunnel):
        log.info("TEST: ping server → client (10.100.0.1 → 10.100.0.2)")
        r = _run(f"ping -c 5 -W 2 {tunnel['client_ip']}", check=False)
        log.info(f"  Result: {r.stdout.strip().split(chr(10))[-1]}")
        assert r.returncode == 0, f"Ping failed:\n{r.stdout}\n{r.stderr}"

    def test_tcp_iperf(self, tunnel):
        log.info("TEST: TCP iperf3 through tunnel")
        _run(f"iperf3 -s -1 -B {tunnel['server_ip']} -D", check=False)
        _wait_iperf()

        r = _ns(tunnel["ns"], f"iperf3 -c {tunnel['server_ip']} -t 3 -J", check=False)
        assert r.returncode == 0, f"TCP iperf failed:\n{r.stderr}"

        result = json.loads(r.stdout)
        bps = result["end"]["sum_received"]["bits_per_second"]
        mbps = bps / 1_000_000
        log.info(f"  TCP throughput: {mbps:.1f} Mbps")
        assert bps > 0

    def test_udp_iperf(self, tunnel):
        log.info("TEST: UDP iperf3 through tunnel")
        _run(f"iperf3 -s -1 -B {tunnel['server_ip']} -D", check=False)
        _wait_iperf()

        r = _ns(tunnel["ns"], f"iperf3 -c {tunnel['server_ip']} -u -b 100M -t 3 -J", check=False)
        assert r.returncode == 0, f"UDP iperf failed:\n{r.stderr}"

        result = json.loads(r.stdout)
        bps = result["end"]["sum"]["bits_per_second"]
        mbps = bps / 1_000_000
        log.info(f"  UDP throughput: {mbps:.1f} Mbps")
        assert bps > 0

    def test_handshake_established(self, tunnel):
        r = _ns(tunnel["ns"], f"wg show {tunnel['cli_iface']}", check=False)
        assert "latest handshake" in r.stdout, f"No handshake:\n{r.stdout}"
        log.info("  Handshake: OK")

    def test_transfer_stats(self, tunnel):
        r = _ns(tunnel["ns"], f"wg show {tunnel['cli_iface']} transfer", check=False)
        parts = r.stdout.strip().split()
        assert len(parts) >= 3, f"Unexpected: {r.stdout}"
        rx, tx = int(parts[1]), int(parts[2])
        log.info(f"  Transfer: rx={rx} tx={tx}")
        assert rx > 0 and tx > 0


# ============================================================================
# Multihop exit fixture
# ============================================================================

@pytest.fixture(scope="module")
def multihop_tunnel(tunnel):
    """Extends tunnel with an exit node: server → exit via BridgeClient multihop."""
    uid = uuid.uuid4().hex[:8]
    ns_exit = f"nse-{uid}"
    mh_iface = f"wgm{uid[:4]}"
    exit_iface = f"wge{uid[:4]}"
    vs_exit = f"vse{uid[:5]}"
    vc_exit = f"vce{uid[:5]}"
    bridge = tunnel["bridge"]  # noqa

    log.info(f"=== MULTIHOP SETUP (uid={uid}) ===")

    _run(f"ip netns del {ns_exit}", check=False)
    _run(f"ip link del {vs_exit}", check=False)

    # Step 1: Exit namespace + veth
    log.info(f"Step 1: Exit namespace {ns_exit} + veth")
    _run(f"ip netns add {ns_exit}")
    _ns(ns_exit, "ip link set up dev lo")
    _run(f"ip link add {vs_exit} type veth peer name {vc_exit}")
    _run(f"ip link set {vc_exit} netns {ns_exit}")
    _run(f"ip addr add 172.16.2.1/24 dev {vs_exit}")
    _run(f"ip link set {vs_exit} up")
    _ns(ns_exit, f"ip addr add 172.16.2.2/24 dev {vc_exit}")
    _ns(ns_exit, f"ip link set {vc_exit} up")

    # Step 2: Kernel WG exit server
    log.info(f"Step 2: Kernel WG exit server (iface={exit_iface})")
    _ns(ns_exit, f"ip link add {exit_iface} type wireguard")
    _ns(ns_exit, f"ip addr add 10.200.0.1/24 dev {exit_iface}")

    exit_priv = _run("wg genkey").stdout.strip()
    exit_pub = _run(f"echo '{exit_priv}' | wg pubkey").stdout.strip()
    exit_priv_path = os.path.join(tempfile.gettempdir(), f"exit_priv_{uid}")
    with open(exit_priv_path, "w") as f:
        f.write(exit_priv)
    os.chmod(exit_priv_path, 0o600)
    log.info(f"  Exit pub: {exit_pub[:20]}...")

    # Step 3: BridgeClient creates multihop tunnel
    log.info(f"Step 3: BridgeClient.create_multihop_tunnel → {mh_iface}")
    exit_pub_hex = base64.b64decode(exit_pub).hex()
    mh_name = f"exit-{uid}"
    bridge.create_multihop_tunnel(
        name=mh_name, iface_name=mh_iface,
        remote_endpoint="172.16.2.2:52000",
        remote_pub_key=exit_pub_hex,
    )

    mh_info = bridge.get_multihop_tunnel(mh_name)
    mh_pub_b64 = base64.b64encode(bytes.fromhex(mh_info.public_key)).decode()
    log.info(f"  Multihop pub: {mh_pub_b64[:20]}...")

    # Step 4: Configure exit server peer
    log.info("Step 4: Configure exit server to accept multihop tunnel")
    _ns(ns_exit, (
        f"wg set {exit_iface} private-key {exit_priv_path} "
        f"listen-port 52000 "
        f"peer {mh_pub_b64} allowed-ips 10.200.0.2/32"
    ))
    _ns(ns_exit, f"ip link set up dev {exit_iface}")

    # Step 5: Start multihop tunnel + assign IP
    log.info("Step 5: Start multihop tunnel")
    bridge.start_multihop_tunnel(mh_name)
    _run(f"ip addr add 10.200.0.2/24 dev {mh_iface}", check=False)
    _run(f"ip link set up dev {mh_iface}", check=False)

    # Step 6: Wait handshake
    log.info("Step 6: Waiting for multihop handshake...")
    time.sleep(2)
    _run("ping -c 1 -W 3 10.200.0.1", check=False)
    time.sleep(1)

    r = _ns(ns_exit, f"wg show {exit_iface}", check=False)
    handshake_ok = "latest handshake" in r.stdout
    log.info(f"  Exit handshake: {'OK' if handshake_ok else 'NOT YET'}")

    log.info("=== MULTIHOP READY ===")

    info = {
        **tunnel,
        "ns_exit": ns_exit, "exit_ip": "10.200.0.1", "mh_ip": "10.200.0.2",
        "mh_iface": mh_iface, "exit_iface": exit_iface, "mh_name": mh_name,
    }

    yield info

    log.info("=== MULTIHOP TEARDOWN ===")
    bridge.delete_multihop_tunnel(mh_name)
    pids = _run(f"ip netns pids {ns_exit}", check=False).stdout.strip()
    if pids:
        _run(f"kill {pids}", check=False)
    _run(f"ip netns del {ns_exit}", check=False)
    _run(f"ip link del {vs_exit}", check=False)
    if os.path.exists(exit_priv_path):
        os.remove(exit_priv_path)


# ============================================================================
# Multihop tests
# ============================================================================

@pytest.mark.docker
class TestMultihopNetNS:

    def test_ping_server_to_exit(self, multihop_tunnel):
        log.info("TEST: ping server → exit (10.200.0.2 → 10.200.0.1)")
        r = _run(f"ping -c 5 -W 2 {multihop_tunnel['exit_ip']}", check=False)
        log.info(f"  Result: {r.stdout.strip().split(chr(10))[-1]}")
        assert r.returncode == 0, f"Ping failed:\n{r.stdout}\n{r.stderr}"

    def test_exit_handshake(self, multihop_tunnel):
        r = _ns(multihop_tunnel["ns_exit"], f"wg show {multihop_tunnel['exit_iface']}", check=False)
        assert "latest handshake" in r.stdout, f"No handshake:\n{r.stdout}"
        log.info("  Exit handshake: OK")

    def test_multihop_tunnel_status(self, multihop_tunnel):
        bridge: BridgeClient = multihop_tunnel["bridge"]  # noqa
        t = bridge.get_multihop_tunnel(multihop_tunnel["mh_name"])
        log.info(f"  Tunnel status={t.status} enabled={t.enabled}")
        assert t.status == "running"
        assert t.enabled is True

    def test_tcp_iperf_to_exit(self, multihop_tunnel):
        log.info("TEST: TCP iperf3 server → exit through multihop")
        ns_exit = multihop_tunnel["ns_exit"]
        exit_ip = multihop_tunnel["exit_ip"]

        _ns(ns_exit, f"iperf3 -s -1 -B {exit_ip} -D", check=False)
        _wait_iperf(ns_exit)

        r = _run(f"iperf3 -c {exit_ip} -t 3 -J", check=False)
        assert r.returncode == 0, f"TCP iperf failed:\n{r.stderr}"

        result = json.loads(r.stdout)
        bps = result["end"]["sum_received"]["bits_per_second"]
        mbps = bps / 1_000_000
        log.info(f"  TCP throughput to exit: {mbps:.1f} Mbps")
        assert bps > 0