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

IPC config builder and parser — pure functions, no FFI dependency.
"""

from __future__ import annotations


def build_server_config(private_key_hex: str, listen_port: int) -> str:
    """Build server-section IPC config string."""
    return f"private_key={private_key_hex}\nlisten_port={listen_port}\n"


def build_peer_config(
    public_key_hex: str,
    preshared_key_hex: str,
    ipv4_address: str,
    ipv6_address: str,
    keepalive: int,
) -> str:
    """Build a single peer IPC config block."""
    return (
        f"public_key={public_key_hex}\n"
        f"preshared_key={preshared_key_hex}\n"
        f"allowed_ip={ipv4_address}/32\n"
        f"allowed_ip={ipv6_address}/128\n"
        f"persistent_keepalive_interval={keepalive}\n"
    )


def build_full_config(
    private_key_hex: str,
    listen_port: int,
    clients: list[dict],
    keepalive: int,
) -> str:
    """Build complete IPC config with server + replace_peers + all peers."""
    parts = [build_server_config(private_key_hex, listen_port), "replace_peers=true\n"]
    for c in clients:
        parts.append(
            build_peer_config(
                public_key_hex=c["public_key_hex"],
                preshared_key_hex=c["preshared_key_hex"],
                ipv4_address=c["ipv4_address"],
                ipv6_address=c["ipv6_address"],
                keepalive=keepalive,
            )
        )
    return "".join(parts)


def build_peer_remove_config(public_key_hex: str) -> str:
    """Build IPC config to remove a single peer."""
    return f"public_key={public_key_hex}\nremove=true\n"


def parse_ipc_peers(ipc_output: str) -> set[str]:
    """Extract peer public keys from IPC get output."""
    peers: set[str] = set()
    for line in ipc_output.splitlines():
        if line.startswith("public_key="):
            peers.add(line.split("=", 1)[1])
    return peers
