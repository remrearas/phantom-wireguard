"""Shared helpers for multihop E2E tests."""

from __future__ import annotations

import os
from textwrap import dedent

from e2e_tests.tests.conftest import sh


# ── Presets ────────────────────────────────────────────────────────

MULTIHOP_V4_PRESET = dedent("""\
    name: multihop-exit
    priority: 80
    metadata:
      description: Forward IPv4 traffic wg_main to wg_exit

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

MULTIHOP_V6_PRESET = dedent("""\
    name: multihop-exit-v6
    priority: 80
    metadata:
      description: Forward IPv6 traffic wg_main to wg_exit

    table:
      - ensure: {id: 201, name: mh6, family: 10}
      - policy: {from: "fd00:10:1::/64", to: "fd00:10:1::/64", table: main, priority: 99, family: 10}
      - policy: {from: "fd00:10:1::/64", table: mh6, priority: 100, family: 10}
      - route:  {destination: default, device: wg_exit, table: mh6, family: 10}

    rules:
      - chain: forward
        action: accept
        family: 10
        in_iface: wg_main
        out_iface: wg_exit
      - chain: forward
        action: accept
        family: 10
        in_iface: wg_exit
        out_iface: wg_main
        state: established,related
      - chain: postrouting
        action: masquerade
        family: 10
        source: "fd00:10:1::/64"
        out_iface: wg_exit
""")


# ── WireGuard helpers ─────────────────────────────────────────────

def wg_genkey() -> tuple[str, str]:
    priv = sh("wg genkey").stdout.strip()
    pub = sh(f"echo '{priv}' | wg pubkey").stdout.strip()
    return priv, pub


def wg_genpsk() -> str:
    return sh("wg genpsk").stdout.strip()


def parse_exit_config(raw: str) -> dict:
    result = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def setup_wg_main(workdir: str, addr: str, port: int = 51820) -> dict:
    priv, pub = wg_genkey()
    priv_file = os.path.join(workdir, "wg_main.key")
    with open(priv_file, "w") as f:
        f.write(priv)

    sh("ip link add wg_main type wireguard")
    sh(f"wg set wg_main private-key {priv_file} listen-port {port}")
    sh(f"ip addr add {addr} dev wg_main")
    sh("ip link set wg_main up")
    print(f"  wg_main UP — {addr} :{port}", flush=True)
    return {"priv": priv, "pub": pub}


def setup_wg_exit(workdir: str, exit_cfg: dict):
    priv_file = os.path.join(workdir, "wg_exit.key")
    with open(priv_file, "w") as f:
        f.write(exit_cfg["PrivateKey"])

    sh("ip link add wg_exit type wireguard")
    sh(f"wg set wg_exit private-key {priv_file}")

    peer_cmd = f"wg set wg_exit peer {exit_cfg['PublicKey']}"
    if exit_cfg.get("PresharedKey"):
        psk_file = os.path.join(workdir, "wg_exit.psk")
        with open(psk_file, "w") as f:
            f.write(exit_cfg["PresharedKey"])
        peer_cmd += f" preshared-key {psk_file}"
    peer_cmd += f" endpoint {exit_cfg['Endpoint']}"
    peer_cmd += f" allowed-ips {exit_cfg['AllowedIPs']}"
    peer_cmd += " persistent-keepalive 25"
    sh(peer_cmd)

    sh(f"ip addr add {exit_cfg['Address']} dev wg_exit")
    sh("ip link set wg_exit up")
    print(f"  wg_exit UP — {exit_cfg['Address']} → {exit_cfg['Endpoint']}", flush=True)


def cleanup_wg():
    sh("ip link delete wg_main", check=False)
    sh("ip link delete wg_exit", check=False)


def ping(target: str) -> bool:
    r = sh(f"ping -c3 -W2 {target}", check=False)
    return r.returncode == 0


def ping6(target: str) -> bool:
    r = sh(f"ping -6 -c3 -W2 {target}", check=False)
    return r.returncode == 0
