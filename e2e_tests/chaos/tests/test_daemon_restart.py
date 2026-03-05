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

Chaos E2E: Daemon Restart Recovery (gradual teardown)

Builds full state (client + multihop + ghost), restarts daemon,
then gradually tears down each layer with a restart between each
to verify recovery at every degradation level.

Phases:
    1.  Setup: client + multihop + ghost
    2.  Pre-restart snapshot (full state)
    3.  Restart #1 — full recovery (multihop + ghost)
    4.  Post-restart verification + client E2E via wstunnel
    5.  Ghost disable + client teardown
    6.  Restart #2 — multihop-only recovery (no ghost)
    7.  Post-restart verification + client E2E via raw WG/UDP
    8.  Multihop disable + client teardown
    9.  Restart #3 — core-only recovery (no multihop, no ghost)
    10. Post-restart verification + client E2E (daemon-only)
    11. Final cleanup

Run with -s to see live output:
    pytest e2e_tests/chaos/tests/test_daemon_restart.py -s
"""

from __future__ import annotations

import base64
import functools
import time

import pytest
import requests


# Force line-by-line flush so output streams live under pytest -s
# noinspection PyShadowingBuiltins
print = functools.partial(print, flush=True)


# -- Display helpers -------------------------------------------------

_SEP = "=" * 64
_THIN = "-" * 64


def _phase(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(f"{_SEP}")


def _info(label: str, value: str) -> None:
    print(f"  {label:20s}: {value}")


def _elapsed(t0: float) -> None:
    print(f"  {'elapsed':20s}: {time.perf_counter() - t0:.2f}s")
    print(f"{_THIN}")


def _api(method: str, path: str, resp: requests.Response) -> None:
    """Compact single-line API log."""
    print(f"  {method:4s} {path:40s} -> {resp.status_code}")


def _exec_log(label: str, rc: int, out: str) -> None:
    status = "OK" if rc == 0 else f"FAIL (rc={rc})"
    print(f"  {label:20s}: {status}")
    if out.strip():
        for line in out.strip().splitlines():
            print(f"    | {line}")


def _adapt_config(raw: str, endpoint_override: str | None = None) -> str:
    """Adapt wg-quick config for E2E: strip DNS, /32->/24, narrow AllowedIPs."""
    adapted = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("DNS"):
            continue
        if stripped.startswith("Address") and "/32" in stripped:
            line = line.replace("/32", "/24")
        if stripped.startswith("AllowedIPs") and "0.0.0.0/0" in stripped:
            line = line.replace("0.0.0.0/0", "10.0.0.0/8")
        if endpoint_override and stripped.startswith("Endpoint"):
            line = f"Endpoint = {endpoint_override}"
        adapted.append(line)
    return "\n".join(adapted)


def _gateway_ip_from_conf(conf: str) -> str:
    """Extract gateway IP (x.x.x.1) from client config Address field."""
    for line in conf.splitlines():
        if line.strip().startswith("Address"):
            addr = line.split("=", 1)[1].strip().split("/")[0].split(",")[0].strip()
            return f"{addr.rsplit('.', 1)[0]}.1"
    raise ValueError("No Address in config")


def _print_server_state(
    multihop: dict | None = None,
    ghost: dict | None = None,
    fw_groups: list[str] | None = None,
) -> None:
    """Print compact server state block."""
    print(f"\n{_THIN}")
    print("  Server State")
    print(f"{_THIN}")
    if multihop is not None:
        active = multihop.get("active", "")
        endpoint = ""
        if multihop.get("exit"):
            endpoint = multihop["exit"].get("endpoint", "")
        _info("multihop", f"{'ENABLED' if multihop['enabled'] else 'disabled'}"
              + (f"  exit={active}  endpoint={endpoint}" if active else ""))
    if ghost is not None:
        if ghost["enabled"]:
            _info("ghost", f"ENABLED  running={'yes' if ghost.get('running') else 'no'}"
                  f"  bind={ghost.get('bind_url', '')}"
                  f"  tls={'yes' if ghost.get('tls_configured') else 'no'}")
        else:
            _info("ghost", "disabled")
    if fw_groups is not None:
        _info("firewall groups", ", ".join(fw_groups))


def _print_wg_show(container_exec, label: str = "Client WireGuard") -> None:
    """Print wg show wg0 output from client."""
    print(f"\n{_THIN}")
    print(f"  {label}")
    print(f"{_THIN}")
    rc, out = container_exec("client", "wg show wg0", check=False)
    _exec_log("wg show wg0", rc, out)


def _print_connectivity(container_exec, targets: list[tuple[str, str, bool]]) -> None:
    """Ping targets: list of (ip, label, should_succeed)."""
    print(f"\n{_THIN}")
    print("  Connectivity")
    print(f"{_THIN}")
    for ip, label, should_succeed in targets:
        rc, out = container_exec("client", f"ping -c 3 -W 2 {ip}", check=False)
        ok = rc == 0
        icon = "OK" if ok else "UNREACHABLE"
        print(f"  {label:20s}: {icon} ({ip})")
        if should_succeed:
            assert ok, f"{label} failed: {ip}\n{out}"
        else:
            assert not ok, f"{label} should be unreachable: {ip}"


# -- Fixtures --------------------------------------------------------

@pytest.fixture(scope="module")
def api(gateway_url):
    class _Api:
        def __init__(self, base: str):
            self.base = base

        def get(self, path: str, **kwargs) -> requests.Response:
            resp = requests.get(f"{self.base}{path}", timeout=10, **kwargs)
            _api("GET", path, resp)
            return resp

        def post(self, path: str, body: dict | None = None, **kwargs) -> requests.Response:
            if body is not None:
                kwargs["json"] = body
            resp = requests.post(f"{self.base}{path}", timeout=10, **kwargs)
            _api("POST", path, resp, )
            return resp

    return _Api(gateway_url)


@pytest.fixture(scope="module")
def exit_conf(container_exec, container_ip):
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
    return container_ip("daemon")


# -- Shared helpers --------------------------------------------------

def _get_server_state(api):
    """Fetch multihop, ghost, firewall state in one shot."""
    mh = api.get("/api/multihop/status").json()["data"]
    ghost = api.get("/api/ghost/status").json()["data"]
    resp = api.get("/api/core/firewall/groups/list")
    groups = resp.json()["data"]
    group_names = [g["name"] for g in groups] if isinstance(groups, list) else list(groups.keys())
    return mh, ghost, group_names


def _setup_client_wg(
    api, container_exec, container_write_file,
    endpoint_override: str | None = None,
) -> str:
    """Export config, adapt, write, bring up WG on client. Returns adapted conf."""
    resp = api.post("/api/core/clients/config", body={"name": "chaos-client", "version": "v4"})
    assert resp.status_code == 200
    raw = base64.b64decode(resp.json()["data"]).decode()
    conf = _adapt_config(raw, endpoint_override=endpoint_override)
    container_write_file("client", "/etc/wireguard/wg0.conf", conf)
    container_exec("client", "wg-quick down wg0 2>/dev/null || true", check=False)
    container_exec("client", "wg-quick up wg0")
    time.sleep(5)
    return conf


def _teardown_client(container_exec) -> None:
    """Stop client WG and wstunnel."""
    container_exec("client", "wg-quick down wg0 2>/dev/null || true", check=False)
    container_exec("client", "kill $(pidof wstunnel) 2>/dev/null || true", check=False)


# -- Test class ------------------------------------------------------

class TestDaemonRestart:
    """Daemon restart recovery — gradual teardown with restart at each level."""

    # ================================================================
    #  PHASE 1 — SETUP: CLIENT + MULTIHOP + GHOST
    # ================================================================

    def test_setup_client(self, api):
        t0 = time.perf_counter()
        _phase("PHASE 1a — CLIENT SETUP")

        resp = api.post("/api/core/clients/assign", body={"name": "chaos-client"})
        assert resp.status_code == 201

        data = resp.json()["data"]
        _info("name", data["name"])
        _info("ipv4", data["ipv4_address"])
        _info("ipv6", data.get("ipv6_address", ""))
        _info("public key", data["public_key_hex"][:16] + "...")
        _elapsed(t0)

    def test_setup_multihop(self, api, exit_conf):
        t0 = time.perf_counter()
        _phase("PHASE 1b — MULTIHOP SETUP")

        resp = api.post("/api/multihop/import", body={"name": "chaos-exit", "config": exit_conf})
        assert resp.status_code == 201

        data = resp.json()["data"]
        _info("exit name", data["name"])
        _info("endpoint", data["endpoint"])
        _info("address", data["address"])
        _info("allowed IPs", data["allowed_ips"])

        resp = api.post("/api/multihop/enable", body={"name": "chaos-exit"})
        assert resp.status_code == 200
        _info("status", resp.json()["data"]["status"])

        time.sleep(5)
        _elapsed(t0)

    def test_setup_ghost(self, api, container_exec, daemon_ip):
        t0 = time.perf_counter()
        _phase("PHASE 1c — GHOST SETUP")

        cert_cmd = (
            "openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 "
            "-keyout /tmp/ghost.key -out /tmp/ghost.crt -days 1 -nodes "
            '-subj "/CN=chaos-e2e" 2>&1'
        )
        container_exec("daemon", cert_cmd)

        _, cert_pem = container_exec("daemon", "cat /tmp/ghost.crt")
        _, key_pem = container_exec("daemon", "cat /tmp/ghost.key")

        resp = api.post("/api/ghost/enable", body={
            "domain": daemon_ip,
            "tls_certificate": base64.b64encode(cert_pem.encode()).decode(),
            "tls_private_key": base64.b64encode(key_pem.encode()).decode(),
        })
        assert resp.status_code == 201

        data = resp.json()["data"]
        self.__class__._ghost_secret = data["restrict_path_prefix"]

        _info("domain", data["domain"])
        _info("protocol", f"{data['protocol']}:{data['port']}")
        _info("secret prefix", data["restrict_path_prefix"][:8] + "...")
        _info("cert CN", "chaos-e2e")
        _elapsed(t0)

    # ================================================================
    #  PHASE 2 — PRE-RESTART STATE SNAPSHOT
    # ================================================================

    def test_pre_restart_state(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 2 — PRE-RESTART STATE SNAPSHOT")

        mh, ghost, fw_groups = _get_server_state(api)
        assert mh["enabled"] is True
        assert ghost["enabled"] is True
        assert "ghost" in fw_groups
        assert "multihop-exit" in fw_groups

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)

        # Daemon → exit-server connectivity
        print(f"\n{_THIN}")
        print("  Daemon Connectivity")
        print(f"{_THIN}")
        rc, out = container_exec("daemon", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("daemon -> exit", rc, out)
        assert rc == 0

        _elapsed(t0)

    # ================================================================
    #  PHASE 3 — RESTART #1 (FULL STATE: MULTIHOP + GHOST)
    # ================================================================

    def test_restart_full(self, restart_daemon):
        t0 = time.perf_counter()
        _phase("PHASE 3 — RESTART #1 (full state: multihop + ghost)")

        recovery_time = restart_daemon(timeout=60)
        _info("recovery time", f"{recovery_time:.2f}s")
        _elapsed(t0)

    # ================================================================
    #  PHASE 4 — POST-RESTART #1 VERIFICATION + CLIENT E2E
    # ================================================================

    def test_full_recovery_state(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 4a — POST-RESTART #1: STATE VERIFICATION")

        mh, ghost, fw_groups = _get_server_state(api)
        assert mh["enabled"] is True, f"multihop not recovered: {mh}"
        assert mh["active"] == "chaos-exit"
        assert ghost["enabled"] is True, f"ghost not recovered: {ghost}"
        assert ghost["running"] is True, f"ghost not running: {ghost}"
        assert "ghost" in fw_groups
        assert "multihop-exit" in fw_groups

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)

        # Daemon → exit connectivity
        time.sleep(5)
        print(f"\n{_THIN}")
        print("  Daemon Connectivity")
        print(f"{_THIN}")
        rc, out = container_exec("daemon", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("daemon -> exit", rc, out)
        assert rc == 0

        _elapsed(t0)

    def test_full_recovery_client_e2e(
        self, api, container_exec, container_write_file, daemon_ip,
    ):
        t0 = time.perf_counter()
        _phase("PHASE 4b — CLIENT E2E (wstunnel -> multihop -> exit)")

        # noinspection PyUnresolvedReferences
        secret = self.__class__._ghost_secret
        wstunnel_cmd = (
            f"wstunnel client "
            f"--http-upgrade-path-prefix {secret} "
            f"-L udp://127.0.0.1:51820:127.0.0.1:51820 "
            f"wss://{daemon_ip}:443"
        )

        _teardown_client(container_exec)

        _info("wstunnel target", f"wss://{daemon_ip}:443")
        container_exec("client", f"nohup {wstunnel_cmd} > /tmp/wstunnel.log 2>&1 &")
        time.sleep(3)

        rc, _ = container_exec("client", "pidof wstunnel", check=False)
        assert rc == 0, "wstunnel client not running"
        _info("wstunnel", "running")

        conf = _setup_client_wg(
            api, container_exec, container_write_file,
            endpoint_override="127.0.0.1:51820",
        )

        _print_wg_show(container_exec, "Client WireGuard (via wstunnel)")

        gw = _gateway_ip_from_conf(conf)
        _print_connectivity(container_exec, [
            (gw, "client -> daemon WG", True),
            ("10.0.2.1", "client -> exit (mhop)", True),
        ])
        _elapsed(t0)

    # ================================================================
    #  PHASE 5 — GHOST DISABLE + CLIENT TEARDOWN
    # ================================================================

    def test_disable_ghost(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 5 — GHOST DISABLE")

        _teardown_client(container_exec)

        resp = api.post("/api/ghost/disable")
        assert resp.status_code == 200

        mh, ghost, fw_groups = _get_server_state(api)
        assert ghost["enabled"] is False
        assert mh["enabled"] is True

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)
        _elapsed(t0)

    # ================================================================
    #  PHASE 6 — RESTART #2 (MULTIHOP ONLY, NO GHOST)
    # ================================================================

    def test_restart_multihop_only(self, restart_daemon):
        t0 = time.perf_counter()
        _phase("PHASE 6 — RESTART #2 (multihop only, no ghost)")

        recovery_time = restart_daemon(timeout=60)
        _info("recovery time", f"{recovery_time:.2f}s")
        _elapsed(t0)

    # ================================================================
    #  PHASE 7 — POST-RESTART #2 VERIFICATION + CLIENT RAW WG
    # ================================================================

    def test_multihop_only_state(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 7a — POST-RESTART #2: STATE (multihop, no ghost)")

        mh, ghost, fw_groups = _get_server_state(api)
        assert mh["enabled"] is True
        assert mh["active"] == "chaos-exit"
        assert ghost["enabled"] is False
        assert "multihop-exit" in fw_groups
        assert "ghost" not in fw_groups, f"ghost should be gone: {fw_groups}"

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)

        time.sleep(5)
        print(f"\n{_THIN}")
        print("  Daemon Connectivity")
        print(f"{_THIN}")
        rc, out = container_exec("daemon", "ping -c 3 -W 2 10.0.2.1", check=False)
        _exec_log("daemon -> exit", rc, out)
        assert rc == 0

        _elapsed(t0)

    def test_multihop_only_client_e2e(
        self, api, container_exec, container_write_file,
    ):
        t0 = time.perf_counter()
        _phase("PHASE 7b — CLIENT E2E (raw WG/UDP -> multihop -> exit)")

        conf = _setup_client_wg(api, container_exec, container_write_file)

        _print_wg_show(container_exec, "Client WireGuard (raw UDP)")

        gw = _gateway_ip_from_conf(conf)
        _print_connectivity(container_exec, [
            (gw, "client -> daemon WG", True),
            ("10.0.2.1", "client -> exit (mhop)", True),
        ])
        _elapsed(t0)

    # ================================================================
    #  PHASE 8 — MULTIHOP DISABLE + CLIENT TEARDOWN
    # ================================================================

    def test_disable_multihop(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 8 — MULTIHOP DISABLE")

        _teardown_client(container_exec)

        resp = api.post("/api/multihop/disable")
        assert resp.status_code == 200

        mh, ghost, fw_groups = _get_server_state(api)
        assert mh["enabled"] is False
        assert ghost["enabled"] is False

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)
        _elapsed(t0)

    # ================================================================
    #  PHASE 9 — RESTART #3 (CORE ONLY)
    # ================================================================

    def test_restart_core_only(self, restart_daemon):
        t0 = time.perf_counter()
        _phase("PHASE 9 — RESTART #3 (core only)")

        recovery_time = restart_daemon(timeout=60)
        _info("recovery time", f"{recovery_time:.2f}s")
        _elapsed(t0)

    # ================================================================
    #  PHASE 10 — POST-RESTART #3 VERIFICATION + CLIENT (DAEMON ONLY)
    # ================================================================

    def test_core_only_state(self, api):
        t0 = time.perf_counter()
        _phase("PHASE 10a — POST-RESTART #3: STATE (core only)")

        mh, ghost, fw_groups = _get_server_state(api)
        assert mh["enabled"] is False
        assert ghost["enabled"] is False
        assert "multihop-exit" not in fw_groups
        assert "ghost" not in fw_groups

        _print_server_state(multihop=mh, ghost=ghost, fw_groups=fw_groups)

        # Client config still exportable
        resp = api.post("/api/core/clients/config", body={"name": "chaos-client", "version": "v4"})
        assert resp.status_code == 200
        _info("client config", "exportable")

        _elapsed(t0)

    def test_core_only_client_e2e(
        self, api, container_exec, container_write_file,
    ):
        t0 = time.perf_counter()
        _phase("PHASE 10b — CLIENT E2E (daemon only, no multihop)")

        conf = _setup_client_wg(api, container_exec, container_write_file)

        _print_wg_show(container_exec, "Client WireGuard (core only)")

        gw = _gateway_ip_from_conf(conf)
        _print_connectivity(container_exec, [
            (gw, "client -> daemon WG", True),
            ("10.0.2.1", "client -> exit", False),  # multihop disabled
        ])
        _elapsed(t0)

    # ================================================================
    #  PHASE 11 — FINAL CLEANUP
    # ================================================================

    def test_cleanup(self, api, container_exec):
        t0 = time.perf_counter()
        _phase("PHASE 11 — FINAL CLEANUP")

        _teardown_client(container_exec)

        api.post("/api/multihop/remove", body={"name": "chaos-exit"})
        api.post("/api/core/clients/revoke", body={"name": "chaos-client"})

        _info("exit", "chaos-exit removed")
        _info("client", "chaos-client revoked")

        resp = api.get("/api/multihop/list")
        names = [e["name"] for e in resp.json()["data"]["exits"]]
        assert "chaos-exit" not in names

        _elapsed(t0)

        print(f"\n{_SEP}")
        print("  ALL PHASES PASSED")
        print(f"{_SEP}\n")
