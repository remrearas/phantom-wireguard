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

Multighost E2E integration test — multihop + ghost mode, fully API-driven.

Runs INSIDE the master container. Uses:
- gateway_url -> daemon API (HTTP via socat)
- container_exec -> docker.sock exec into client container
- container_ip -> container IP discovery

Topology (phases 1-4):
    client --WG--> wg_phantom_main --FORWARD--> wg_phantom_exit --WG--> exit-server

Topology (phases 5-6, ghost mode active):
    client --wstunnel(wss:443)--> daemon --WG--> wg_phantom_exit --WG--> exit-server

API flow:
    1. POST /api/core/clients/assign     -> create client
    2. POST /api/multihop/import+enable   -> multihop setup
    3. Daemon connectivity inspection     -> ping + firewall
    4. POST /api/core/clients/config      -> client WG over raw UDP
    5. POST /api/ghost/enable             -> wstunnel server (self-signed TLS)
    6. Client connects via wstunnel       -> WG over wss, verify multihop chain
    7. Cleanup: ghost disable, multihop disable, revoke

Run with -s to see live output:
    pytest e2e_tests/multighost/tests/test_multighost.py -s
"""

from __future__ import annotations

import base64
import functools
import json
import time

import pytest
import requests


# Force line-by-line flush so output streams live under pytest -s
# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)


# -- Display helpers -------------------------------------------------

_SEP = "=" * 64
_THIN = "-" * 64


def _api_log(method: str, path: str, resp: requests.Response, body: dict | None = None) -> None:
    """Print API request/response summary."""
    print(f"\n  {method} {path}")
    if body:
        print(f"    request     : {json.dumps(body, ensure_ascii=False)}")
    print(f"    status      : {resp.status_code}")
    try:
        data = resp.json()
        compact = json.dumps(data, indent=2, ensure_ascii=False)
        for line in compact.splitlines()[:20]:
            print(f"    response    : {line}")
        if len(compact.splitlines()) > 20:
            print(f"    response    : ... ({len(compact.splitlines())} lines total)")
    except (ValueError, KeyError):
        print(f"    response    : {resp.text[:200]}")


def _exec_log(label: str, rc: int, out: str) -> None:
    """Print container exec result."""
    status = "OK" if rc == 0 else f"FAIL (rc={rc})"
    print(f"  {label:16s}: {status}")
    if out.strip():
        for line in out.strip().splitlines():
            print(f"    | {line}")


# -- Fixtures --------------------------------------------------------

@pytest.fixture(scope="module")
def api(gateway_url):
    """Thin wrapper for API calls with logging."""

    class _Api:
        def __init__(self, base: str):
            self.base = base

        def get(self, path: str) -> requests.Response:
            resp = requests.get(f"{self.base}{path}", timeout=10)
            _api_log("GET", path, resp)
            return resp

        def post(self, path: str, body: dict | None = None, **kwargs) -> requests.Response:
            if body is not None:
                kwargs["json"] = body
            resp = requests.post(f"{self.base}{path}", timeout=10, **kwargs)
            _api_log("POST", path, resp, body=body)
            return resp

    return _Api(gateway_url)


@pytest.fixture(scope="module")
def exit_conf(container_exec, container_ip):
    """Read exit-server WG config with resolved IP."""
    for _ in range(30):
        rc, out = container_exec("exit-server", "cat /config/client.conf", check=False)
        if rc == 0 and "PublicKey" in out:
            break
        time.sleep(1)
    else:
        pytest.fail("exit-server config not ready after 30s")

    exit_ip = container_ip("exit-server")
    _, conf = container_exec("exit-server", "cat /config/client.conf")
    return conf.replace("__EXIT_SERVER_IP__", exit_ip)


@pytest.fixture(scope="module")
def daemon_ip(container_ip):
    """Daemon container IP on E2E network."""
    return container_ip("daemon")


# -- Test class ------------------------------------------------------

class TestMultighost:
    """Multighost lifecycle E2E — 7 phases, multihop + ghost mode."""

    # ================================================================
    #  PHASE 1 — CLIENT SETUP
    # ================================================================

    def test_assign_client(self, api):
        """Create a test client via API."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 1 — CLIENT SETUP")
        print(f"{_SEP}")

        resp = api.post("/api/core/clients/assign", body={"name": "e2e-client"})
        assert resp.status_code == 201, f"assign: {resp.status_code} {resp.text}"

        data = resp.json()["data"]
        assert data["name"] == "e2e-client"
        assert data["ipv4_address"]
        assert data["private_key_hex"]
        assert data["preshared_key_hex"]

        print(f"\n  Client name   : {data['name']}")
        print(f"  IPv4 address  : {data['ipv4_address']}")
        print(f"  Public key    : {data['public_key_hex'][:16]}...")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 2 — MULTIHOP IMPORT + ENABLE
    # ================================================================

    def test_import_exit(self, api, exit_conf):
        """Import exit-server WG config."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 2a — IMPORT EXIT CONFIG")
        print(f"{_SEP}")

        # Show exit config
        print(f"\n  Exit config (from exit-server):")
        for line in exit_conf.strip().splitlines():
            print(f"    | {line}")

        resp = api.post("/api/multihop/import", body={"name": "test-exit", "config": exit_conf})
        assert resp.status_code == 201, f"import: {resp.status_code} {resp.text}"
        assert resp.json()["ok"] is True

        # Verify import via list
        resp = api.get("/api/multihop/list")
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()["data"]["exits"]]
        assert "test-exit" in names
        print(f"\n  Import verify : test-exit in {names}")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    def test_enable_multihop(self, api):
        """Enable multihop — brings up wg_phantom_exit + firewall preset."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 2b — ENABLE MULTIHOP")
        print(f"{_SEP}")

        resp = api.post("/api/multihop/enable", body={"name": "test-exit"})
        assert resp.status_code == 200, f"enable: {resp.status_code} {resp.text}"
        assert resp.json()["data"]["status"] == "enabled"

        # Verify status
        resp = api.get("/api/multihop/status")
        assert resp.status_code == 200
        status = resp.json()["data"]
        assert status["enabled"] is True
        assert status["active"] == "test-exit"

        print(f"\n  Multihop      : enabled={status['enabled']}  active={status['active']}")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 3 — DAEMON CONNECTIVITY + WG/FIREWALL INSPECTION
    # ================================================================

    def test_daemon_reaches_exit(self, api, container_exec):
        """Verify: daemon can ping exit-server through WG tunnel + inspect state."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 3 — DAEMON CONNECTIVITY & STATE INSPECTION")
        print(f"{_SEP}")

        time.sleep(5)  # wait for WG handshake

        # -- Ping exit-server --
        print(f"\n{_THIN}")
        print("  Connectivity: daemon -> exit-server (10.0.2.1)")
        print(f"{_THIN}")

        rc, out = container_exec("daemon", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("ping 10.0.2.1", rc, out)
        assert rc == 0, f"daemon cannot reach exit-server (10.0.2.1)\n{out}"

        # -- Firewall groups --
        print(f"\n{_THIN}")
        print("  Firewall state (API)")
        print(f"{_THIN}")

        resp = api.get("/api/core/firewall/groups/list")
        assert resp.status_code == 200
        groups = resp.json()["data"]
        group_names = [g["name"] for g in groups] if isinstance(groups, list) else list(groups.keys()) if isinstance(groups, dict) else []
        print(f"\n  Groups        : {group_names}")

        # -- Firewall rules for multihop-exit --
        resp = api.post("/api/core/firewall/rules/list", body={"group": "multihop-exit"})
        if resp.status_code == 200:
            rules = resp.json().get("data", [])
            print(f"  Rules (mhop)  : {len(rules)} rules")
        else:
            print(f"  Rules (mhop)  : {resp.status_code} (group may not exist)")

        # -- Firewall routing for multihop-exit --
        resp = api.post("/api/core/firewall/routing/list", body={"group": "multihop-exit"})
        if resp.status_code == 200:
            routing = resp.json().get("data", [])
            print(f"  Routing (mhop): {len(routing)} rules")
        else:
            print(f"  Routing (mhop): {resp.status_code} (group may not exist)")

        # -- Raw nftables table --
        resp = api.get("/api/core/firewall/table")
        if resp.status_code == 200:
            table = resp.json().get("data", "")
            table_str = table if isinstance(table, str) else json.dumps(table, indent=2)
            print(f"\n  nftables dump:")
            for line in table_str.strip().splitlines()[:30]:
                print(f"    | {line}")
            total_lines = len(table_str.strip().splitlines())
            if total_lines > 30:
                print(f"    | ... ({total_lines} lines total)")

        print(f"\n  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 4 — CLIENT E2E (FULL MULTIHOP CHAIN)
    # ================================================================

    def test_client_e2e(
        self, api, container_exec, container_write_file,
    ):
        """Client connects through full multihop chain."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 4 — CLIENT E2E (FULL MULTIHOP CHAIN)")
        print(f"{_SEP}")

        # -- Export client config via API (base64) --
        resp = api.post(
            "/api/core/clients/config",
            body={"name": "e2e-client", "version": "v4"},
        )
        assert resp.status_code == 200, f"config export: {resp.status_code} {resp.text}"

        client_conf_raw = base64.b64decode(resp.json()["data"]).decode()

        print(f"\n{_THIN}")
        print("  Client wg-quick config (from API, raw)")
        print(f"{_THIN}")
        for line in client_conf_raw.strip().splitlines():
            print(f"    | {line}")

        # Adapt config for E2E: /32 -> /24, 0.0.0.0/0 -> 10.0.0.0/8, strip DNS
        adapted_lines = []
        for line in client_conf_raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("DNS"):
                continue
            if stripped.startswith("Address") and "/32" in stripped:
                line = line.replace("/32", "/24")
            if stripped.startswith("AllowedIPs") and "0.0.0.0/0" in stripped:
                line = line.replace("0.0.0.0/0", "10.0.0.0/8")
            adapted_lines.append(line)
        client_conf = "\n".join(adapted_lines)

        print(f"\n{_THIN}")
        print("  Client wg-quick config (adapted for E2E)")
        print(f"{_THIN}")
        for line in client_conf.strip().splitlines():
            print(f"    | {line}")

        # -- Write config and bring up client tunnel --
        container_write_file("client", "/etc/wireguard/wg0.conf", client_conf)
        container_exec("client", "wg-quick up wg0")
        time.sleep(5)

        # -- Client WG show --
        print(f"\n{_THIN}")
        print("  Client WireGuard state")
        print(f"{_THIN}")

        rc, out = container_exec("client", "wg show wg0", check=False)
        _exec_log("wg show wg0", rc, out)

        # -- Client -> daemon WG (direct) --
        print(f"\n{_THIN}")
        print("  Connectivity: client -> daemon WG")
        print(f"{_THIN}")

        # Parse client address from exported config
        client_addr = ""
        for line in client_conf.splitlines():
            if line.strip().startswith("Address"):
                client_addr = line.split("=", 1)[1].strip().split("/")[0].split(",")[0].strip()
                break
        subnet = client_addr.rsplit(".", 1)[0]
        gateway_ip = f"{subnet}.1"

        rc, out = container_exec("client", f"ping -c 3 -W 2 {gateway_ip}", check=False)
        _exec_log(f"ping {gateway_ip}", rc, out)
        assert rc == 0, f"client cannot reach daemon WG ({gateway_ip})\n{out}"

        # -- Client -> exit-server (multihop) --
        print(f"\n{_THIN}")
        print("  Connectivity: client -> exit-server (multihop)")
        print(f"{_THIN}")

        rc, out = container_exec("client", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("ping 10.0.2.1", rc, out)
        assert rc == 0, f"client cannot reach exit-server via multihop (10.0.2.1)\n{out}"

        print(f"\n  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 5 — GHOST MODE ENABLE
    # ================================================================

    def test_enable_ghost(self, api, container_exec, daemon_ip):
        """Enable ghost mode — self-signed TLS, wstunnel server on daemon."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 5 — ENABLE GHOST MODE")
        print(f"{_SEP}")

        # Tear down client WG from phase 4 before switching to wstunnel
        container_exec("client", "wg-quick down wg0", check=False)

        # Generate self-signed cert on daemon
        cert_cmd = (
            "openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 "
            "-keyout /tmp/ghost.key -out /tmp/ghost.crt -days 1 -nodes "
            '-subj "/CN=ghost-e2e" 2>&1'
        )
        rc, out = container_exec("daemon", cert_cmd)
        _exec_log("openssl", rc, out)

        _, cert_pem = container_exec("daemon", "cat /tmp/ghost.crt")
        _, key_pem = container_exec("daemon", "cat /tmp/ghost.key")

        cert_b64 = base64.b64encode(cert_pem.encode()).decode()
        key_b64 = base64.b64encode(key_pem.encode()).decode()

        print(f"\n  Cert CN       : ghost-e2e")
        print(f"  Cert size     : {len(cert_pem)} bytes")
        print(f"  Key size      : {len(key_pem)} bytes")

        # Enable ghost mode via API
        resp = api.post("/api/ghost/enable", body={
            "domain": daemon_ip,
            "tls_certificate": cert_b64,
            "tls_private_key": key_b64,
        })
        assert resp.status_code == 201, f"ghost enable: {resp.status_code} {resp.text}"

        data = resp.json()["data"]
        assert data["status"] == "enabled"
        assert data["protocol"] == "wss"
        assert data["port"] == 443

        # Store secret for phase 6
        self.__class__._ghost_secret = data["restrict_path_prefix"]

        print(f"\n  Ghost status  : {data['status']}")
        print(f"  Protocol      : {data['protocol']}")
        print(f"  Port          : {data['port']}")
        print(f"  Secret path   : {data['restrict_path_prefix'][:8]}...")

        # Verify ghost + multihop-exit presets coexist
        resp = api.get("/api/core/firewall/groups/list")
        assert resp.status_code == 200
        groups = resp.json()["data"]
        group_names = [g["name"] for g in groups] if isinstance(groups, list) else list(groups.keys())
        assert "ghost" in group_names, f"ghost preset missing: {group_names}"
        assert "multihop-exit" in group_names, f"multihop-exit missing: {group_names}"
        print(f"\n  FW groups     : {group_names}")

        # Verify ghost status API
        resp = api.get("/api/ghost/status")
        status = resp.json()["data"]
        assert status["enabled"] is True
        assert status["tls_configured"] is True

        # Verify multihop still active
        resp = api.get("/api/multihop/status")
        mh = resp.json()["data"]
        assert mh["enabled"] is True
        print(f"  Multihop      : still enabled={mh['enabled']}")

        print(f"\n  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 6 — CLIENT E2E VIA WSTUNNEL
    # ================================================================

    def test_client_ghost_e2e(
        self, api, container_exec, container_write_file, daemon_ip,
    ):
        """Client connects through wstunnel -> WG -> multihop chain."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 6 — CLIENT E2E VIA WSTUNNEL")
        print(f"{_SEP}")

        # noinspection PyUnresolvedReferences
        secret = self.__class__._ghost_secret

        # Export client config via API
        resp = api.post(
            "/api/core/clients/config",
            body={"name": "e2e-client", "version": "v4"},
        )
        assert resp.status_code == 200, f"config export: {resp.status_code} {resp.text}"
        client_conf_raw = base64.b64decode(resp.json()["data"]).decode()

        # Adapt config: strip DNS, /32->/24, 0.0.0.0/0->10.0.0.0/8,
        # Endpoint -> wstunnel local proxy (127.0.0.1:51820)
        adapted_lines = []
        for line in client_conf_raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("DNS"):
                continue
            if stripped.startswith("Address") and "/32" in stripped:
                line = line.replace("/32", "/24")
            if stripped.startswith("AllowedIPs") and "0.0.0.0/0" in stripped:
                line = line.replace("0.0.0.0/0", "10.0.0.0/8")
            if stripped.startswith("Endpoint"):
                line = "Endpoint = 127.0.0.1:51820"
            adapted_lines.append(line)
        client_conf = "\n".join(adapted_lines)

        print(f"\n{_THIN}")
        print("  Client wg-quick config (adapted for wstunnel)")
        print(f"{_THIN}")
        for line in client_conf.strip().splitlines():
            print(f"    | {line}")

        container_write_file("client", "/etc/wireguard/wg0.conf", client_conf)

        # Start wstunnel client (background, TLS verify disabled for self-signed)
        wstunnel_cmd = (
            f"wstunnel client "
            f"--http-upgrade-path-prefix {secret} "
            f"-L udp://127.0.0.1:51820:127.0.0.1:51820 "
            f"wss://{daemon_ip}:443"
        )

        print(f"\n{_THIN}")
        print("  Starting wstunnel client")
        print(f"{_THIN}")
        print(f"  cmd: {wstunnel_cmd}")

        container_exec("client", f"nohup {wstunnel_cmd} > /tmp/wstunnel.log 2>&1 &")
        time.sleep(3)

        # Verify wstunnel running
        rc, out = container_exec("client", "pidof wstunnel", check=False)
        _exec_log("wstunnel pid", rc, out)
        assert rc == 0, f"wstunnel client not running\n{out}"

        rc, out = container_exec("client", "cat /tmp/wstunnel.log", check=False)
        if out.strip():
            print(f"\n  wstunnel log:")
            for line in out.strip().splitlines()[:10]:
                print(f"    | {line}")

        # Bring up WireGuard (over wstunnel)
        container_exec("client", "wg-quick up wg0")
        time.sleep(5)

        # -- Client WG show (via wstunnel) --
        print(f"\n{_THIN}")
        print("  Client WireGuard state (via wstunnel)")
        print(f"{_THIN}")

        rc, out = container_exec("client", "wg show wg0", check=False)
        _exec_log("wg show wg0", rc, out)

        # -- Client -> daemon WG (via wstunnel) --
        print(f"\n{_THIN}")
        print("  Connectivity: client -> daemon WG (via wstunnel)")
        print(f"{_THIN}")

        client_addr = ""
        for line in client_conf.splitlines():
            if line.strip().startswith("Address"):
                client_addr = line.split("=", 1)[1].strip().split("/")[0].split(",")[0].strip()
                break
        subnet = client_addr.rsplit(".", 1)[0]
        gateway_ip = f"{subnet}.1"

        rc, out = container_exec("client", f"ping -c 3 -W 2 {gateway_ip}", check=False)
        _exec_log(f"ping {gateway_ip}", rc, out)
        assert rc == 0, f"client cannot reach daemon WG via wstunnel ({gateway_ip})\n{out}"

        # -- Client -> exit-server (multihop via wstunnel) --
        print(f"\n{_THIN}")
        print("  Connectivity: client -> exit-server (multighost)")
        print(f"{_THIN}")

        rc, out = container_exec("client", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("ping 10.0.2.1", rc, out)
        assert rc == 0, f"client cannot reach exit-server via multighost (10.0.2.1)\n{out}"

        print(f"\n  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    # ================================================================
    #  PHASE 7 — CLEANUP
    # ================================================================

    def test_disable_ghost(self, api, container_exec):
        """Disable ghost mode — multihop must stay active."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 7a — DISABLE GHOST")
        print(f"{_SEP}")

        # Stop client wstunnel + WG
        container_exec("client", "wg-quick down wg0", check=False)
        container_exec("client", "kill $(pidof wstunnel) 2>/dev/null || true", check=False)

        resp = api.post("/api/ghost/disable")
        assert resp.status_code == 200

        resp = api.get("/api/ghost/status")
        assert resp.json()["data"]["enabled"] is False

        # Multihop must still be active
        resp = api.get("/api/multihop/status")
        mh = resp.json()["data"]
        assert mh["enabled"] is True, "multihop should survive ghost disable"

        print(f"\n  Ghost         : disabled")
        print(f"  Multihop      : still enabled={mh['enabled']}")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    def test_disable_multihop(self, api):
        """Disable multihop."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 7b — DISABLE MULTIHOP")
        print(f"{_SEP}")

        resp = api.post("/api/multihop/disable")
        assert resp.status_code == 200

        resp = api.get("/api/multihop/status")
        assert resp.json()["data"]["enabled"] is False

        print(f"\n  Multihop      : disabled")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")
        print(f"{_THIN}")

    def test_cleanup(self, api):
        """Remove exit config and revoke client."""
        t0 = time.perf_counter()

        print(f"\n{_SEP}")
        print("  PHASE 7c — CLEANUP")
        print(f"{_SEP}")

        api.post("/api/multihop/remove", body={"name": "test-exit"})
        api.post("/api/core/clients/revoke", body={"name": "e2e-client"})

        resp = api.get("/api/multihop/list")
        names = [e["name"] for e in resp.json()["data"]["exits"]]
        assert "test-exit" not in names

        print(f"\n  Exits after   : {names}")
        print(f"  Client        : e2e-client revoked")
        print(f"  Phase time    : {time.perf_counter() - t0:.2f}s")

        print(f"\n{_SEP}")
        print("  ALL PHASES PASSED")
        print(f"{_SEP}\n")
