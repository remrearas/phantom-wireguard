"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration: Bridge server + Bridge client (full FFI, no CLI binary).

Note: wstunnel .so uses global state — server and client cannot coexist
in the same process. Server runs in a subprocess.

Ports: server=8445/8447  echo=9995/9994  tunnel=51824/51825
"""

import os
import socket
import subprocess
import sys
import time
from textwrap import dedent

import pytest

from wstunnel_bridge import WstunnelClient, LogLevel
from .conftest import start_echo_server, wait_for_port, cleanup_processes


def _start_bridge_server(bind_url: str, cert: str, key: str,
                         restrict_to: str) -> subprocess.Popen:
    """Start bridge server in a separate process (own .so global state)."""
    script = dedent(f"""\
        import time
        from wstunnel_bridge import WstunnelServer, LogLevel
        s = WstunnelServer("{bind_url}", LogLevel.INFO)
        s.set_tls_certificate("{cert}")
        s.set_tls_private_key("{key}")
        s.add_restrict_to("{restrict_to}")
        s.start()
        while True:
            time.sleep(1)
    """)
    return subprocess.Popen(
        [sys.executable, "-c", script],
        env={**os.environ},
    )


@pytest.mark.docker
class TestBridgeToBridge:
    """Full FFI: bridge WstunnelServer + bridge WstunnelClient."""

    # noinspection PyTypeChecker
    def test_udp_echo(self, certs):
        echo = start_echo_server("udp", 9995)
        time.sleep(0.5)

        server_proc = _start_bridge_server(
            "wss://0.0.0.0:8445", certs["cert"], certs["key"],
            "127.0.0.1:9995",
        )
        assert wait_for_port(8445), "Bridge server did not start"

        client = WstunnelClient("wss://127.0.0.1:8445", LogLevel.INFO)
        client.set_tls_verify(False)
        client.add_tunnel_udp("127.0.0.1", 51824, "127.0.0.1", 9995)
        client.start()
        time.sleep(2)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            sock.sendto(b"bridge-bridge-udp", ("127.0.0.1", 51824))
            data, _ = sock.recvfrom(1024)
            sock.close()

            assert data == b"bridge-bridge-udp"
        finally:
            client.stop()
            client.free()
            cleanup_processes(server_proc, echo)

    # noinspection PyTypeChecker
    def test_tcp_echo(self, certs):
        echo = start_echo_server("tcp", 9994)
        time.sleep(0.5)

        server_proc = _start_bridge_server(
            "wss://0.0.0.0:8447", certs["cert"], certs["key"],
            "127.0.0.1:9994",
        )
        assert wait_for_port(8447), "Bridge server did not start"

        client = WstunnelClient("wss://127.0.0.1:8447", LogLevel.INFO)
        client.set_tls_verify(False)
        client.add_tunnel_tcp("127.0.0.1", 51825, "127.0.0.1", 9994)
        client.start()
        time.sleep(2)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(("127.0.0.1", 51825))
            sock.sendall(b"bridge-bridge-tcp")
            time.sleep(0.5)
            data = sock.recv(1024)
            sock.close()

            assert data == b"bridge-bridge-tcp"
        finally:
            client.stop()
            client.free()
            cleanup_processes(server_proc, echo)
