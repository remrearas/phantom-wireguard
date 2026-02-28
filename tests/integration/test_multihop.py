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

Multihop tunnel integration tests.

Test steps:
  1. Create tunnel → keys generated, stored in DB
  2. Start tunnel → WG device created, enabled for crash recovery
  3. Stop tunnel → device torn down, stays enabled
  4. Disable tunnel → not restored on restart
  5. Crash recovery → enabled tunnels auto-restore
  6. Connectivity → real WG handshake via netns + veth
"""

import base64
import os
import subprocess
import tempfile
import textwrap
import time

import pytest

from wireguard_go_bridge.client import BridgeClient


# ============================================================================
# Netns helpers
# ============================================================================

def _run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)


def _run_in_ns(ns: str, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(f"ip netns exec {ns} {cmd}", check=check)


def _generate_wg_keys() -> tuple[str, str]:
    priv = _run("wg genkey").stdout.strip()
    pub = _run(f"echo '{priv}' | wg pubkey").stdout.strip()
    return priv, pub


@pytest.fixture
def exit_netns(uid):
    """Isolated exit server namespace with veth pair."""
    ns = f"exit-{uid}"
    veth_m = f"vm-{uid[:6]}"
    veth_e = f"ve-{uid[:6]}"

    _run(f"ip netns del {ns}", check=False)
    _run(f"ip link del {veth_m}", check=False)

    _run(f"ip netns add {ns}")
    _run(f"ip link add {veth_m} type veth peer name {veth_e}")
    _run(f"ip link set {veth_e} netns {ns}")
    _run(f"ip addr add 172.16.200.1/24 dev {veth_m}")
    _run(f"ip link set {veth_m} up")
    _run_in_ns(ns, f"ip addr add 172.16.200.2/24 dev {veth_e}")
    _run_in_ns(ns, f"ip link set {veth_e} up")
    _run_in_ns(ns, "ip link set lo up")
    _run_in_ns(ns, "ip route add default via 172.16.200.1")

    yield ns

    _run(f"ip netns del {ns}", check=False)
    _run(f"ip link del {veth_m}", check=False)


# ============================================================================
# Tunnel CRUD
# ============================================================================

@pytest.mark.docker
class TestMultihopCRUD:

    def test_create(self, new_bridge, uid):
        name = f"mh-{uid}"
        t = new_bridge.create_multihop_tunnel(
            name=name, iface_name=f"wg-{uid[:6]}",
            remote_endpoint="203.0.113.5:51820",
            remote_pub_key="a" * 64, fwmark=51820,
        )
        assert t.name == name
        assert t.status == "stopped"
        assert t.enabled is False
        assert len(t.public_key) == 64

    def test_list(self, new_bridge, uid):
        new_bridge.create_multihop_tunnel(f"l1-{uid}", f"wg-a{uid[:4]}", "1.1.1.1:51820", "a" * 64)
        new_bridge.create_multihop_tunnel(f"l2-{uid}", f"wg-b{uid[:4]}", "2.2.2.2:51820", "b" * 64)
        names = {t.name for t in new_bridge.list_multihop_tunnels()}
        assert f"l1-{uid}" in names and f"l2-{uid}" in names

    def test_delete(self, new_bridge, uid):
        name = f"del-{uid}"
        new_bridge.create_multihop_tunnel(name, f"wg-d{uid[:4]}", "1.1.1.1:51820", "c" * 64)
        new_bridge.delete_multihop_tunnel(name)
        assert all(t.name != name for t in new_bridge.list_multihop_tunnels())


# ============================================================================
# Start / Stop / Disable
# ============================================================================

@pytest.mark.docker
class TestMultihopLifecycle:

    def test_start(self, new_bridge, uid):
        name = f"start-{uid}"
        new_bridge.create_multihop_tunnel(name, f"wg-s{uid[:4]}", "192.0.2.1:51820", "d" * 64)
        new_bridge.start_multihop_tunnel(name)
        t = new_bridge.get_multihop_tunnel(name)
        assert t.status == "running"
        assert t.enabled is True

    def test_stop_keeps_enabled(self, new_bridge, uid):
        name = f"stop-{uid}"
        new_bridge.create_multihop_tunnel(name, f"wg-p{uid[:4]}", "192.0.2.2:51820", "e" * 64)
        new_bridge.start_multihop_tunnel(name)
        new_bridge.stop_multihop_tunnel(name)
        t = new_bridge.get_multihop_tunnel(name)
        assert t.status == "stopped"
        assert t.enabled is True

    def test_disable(self, new_bridge, uid):
        name = f"dis-{uid}"
        new_bridge.create_multihop_tunnel(name, f"wg-i{uid[:4]}", "192.0.2.3:51820", "f" * 64)
        new_bridge.start_multihop_tunnel(name)
        new_bridge.disable_multihop_tunnel(name)
        t = new_bridge.get_multihop_tunnel(name)
        assert t.enabled is False


# ============================================================================
# Crash Recovery
# ============================================================================

@pytest.mark.docker
class TestMultihopRecovery:

    def test_enabled_restores(self, new_bridge_factory, uid):
        bridge, db_path = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:52060")
        bridge.start()

        name = f"rec-{uid}"
        bridge.create_multihop_tunnel(name, f"wg-r{uid[:4]}", "192.0.2.4:51820", "0" * 64)
        bridge.start_multihop_tunnel(name)
        bridge.close()

        bridge2 = BridgeClient(db_path, f"wg-r2-{uid[:4]}", 52060)
        try:
            bridge2.start()
            t = bridge2.get_multihop_tunnel(name)
            assert t.enabled is True
            assert t.status in ("running", "error")
            bridge2.stop()
        finally:
            bridge2.close()

    def test_disabled_stays_stopped(self, new_bridge_factory, uid):
        bridge, db_path = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:52061")
        bridge.start()

        name = f"nrec-{uid}"
        bridge.create_multihop_tunnel(name, f"wg-n{uid[:4]}", "192.0.2.5:51820", "1" * 64)
        bridge.start_multihop_tunnel(name)
        bridge.disable_multihop_tunnel(name)
        bridge.close()

        bridge2 = BridgeClient(db_path, f"wg-n2-{uid[:4]}", 52061)
        try:
            bridge2.start()
            t = bridge2.get_multihop_tunnel(name)
            assert t.enabled is False
            assert t.status == "stopped"
            bridge2.stop()
        finally:
            bridge2.close()


# ============================================================================
# Connectivity — real WireGuard tunnel via netns
# ============================================================================

@pytest.mark.docker
class TestMultihopConnectivity:

    def test_tunnel_handshake(self, exit_netns, new_bridge_factory, uid):
        """WireGuard handshake through veth to exit namespace."""
        exit_priv, exit_pub = _generate_wg_keys()

        bridge, _ = new_bridge_factory()
        bridge.setup(endpoint="10.0.0.1:52070", network="10.70.0.0/24")
        bridge.start()

        name = f"conn-{uid}"
        iface = f"wg-c{uid[:4]}"
        exit_pub_hex = base64.b64decode(exit_pub).hex()

        bridge.create_multihop_tunnel(
            name=name, iface_name=iface,
            remote_endpoint="172.16.200.2:51900",
            remote_pub_key=exit_pub_hex,
        )

        tunnel = bridge.get_multihop_tunnel(name)
        tunnel_pub_b64 = base64.b64encode(bytes.fromhex(tunnel.public_key)).decode()

        # Setup exit WireGuard server in namespace
        exit_conf = textwrap.dedent(f"""\
            [Interface]
            PrivateKey = {exit_priv}
            Address = 10.99.0.1/24
            ListenPort = 51900

            [Peer]
            PublicKey = {tunnel_pub_b64}
            AllowedIPs = 10.99.0.2/32
        """)
        # wg-quick derives interface name from filename — must be ≤15 chars
        conf_path = os.path.join(tempfile.gettempdir(), f"wge{uid[:6]}.conf")
        with open(conf_path, "w") as f:
            f.write(exit_conf)
        os.chmod(conf_path, 0o600)

        try:
            r = _run_in_ns(exit_netns, f"wg-quick up {conf_path}", check=False)
            assert r.returncode == 0, f"wg-quick failed: {r.stderr} {r.stdout}"

            bridge.start_multihop_tunnel(name)
            time.sleep(2)

            t = bridge.get_multihop_tunnel(name)
            assert t.status == "running"

            result = _run(f"ip link show {iface}", check=False)
            assert result.returncode == 0, f"Interface {iface} not found"

        finally:
            _run_in_ns(exit_netns, f"wg-quick down {conf_path}", check=False)
            if os.path.exists(conf_path):
                os.remove(conf_path)
            bridge.stop()
