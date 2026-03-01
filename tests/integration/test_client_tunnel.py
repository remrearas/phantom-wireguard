"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration: Bridge client tunnels (CLI server + bridge client).

Ports: server=8443  echo=9999/9998  tunnel=51820/51821
"""

import socket
import time

import pytest

from wstunnel_bridge import WstunnelClient, LogLevel
from .conftest import (
    start_echo_server, start_wstunnel_server,
    wait_for_port, cleanup_processes,
)


@pytest.mark.docker
class TestClientTunnel:
    """CLI wstunnel server + bridge client — UDP/TCP echo."""

    # noinspection PyTypeChecker
    def test_udp_echo(self, certs):
        echo = start_echo_server("udp", 9999)
        time.sleep(0.5)

        server = start_wstunnel_server(
            "wss://0.0.0.0:8443", certs["cert"], certs["key"],
            restrict_to="127.0.0.1:9999",
        )
        assert wait_for_port(8443), "wstunnel server did not start"

        client = WstunnelClient("wss://127.0.0.1:8443", LogLevel.INFO)
        client.set_tls_verify(False)
        client.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 9999)
        client.start()
        time.sleep(1)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(b"wstunnel-udp-test", ("127.0.0.1", 51820))
            data, _ = sock.recvfrom(1024)
            sock.close()

            assert data == b"wstunnel-udp-test"
        finally:
            client.stop()
            client.free()
            cleanup_processes(server, echo)

    # noinspection PyTypeChecker
    def test_tcp_echo(self, certs):
        echo = start_echo_server("tcp", 9998)
        time.sleep(0.5)

        server = start_wstunnel_server(
            "wss://0.0.0.0:8443", certs["cert"], certs["key"],
            restrict_to="127.0.0.1:9998",
        )
        assert wait_for_port(8443), "wstunnel server did not start"

        client = WstunnelClient("wss://127.0.0.1:8443", LogLevel.INFO)
        client.set_tls_verify(False)
        client.add_tunnel_tcp("127.0.0.1", 51821, "127.0.0.1", 9998)
        client.start()
        time.sleep(1)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", 51821))
            sock.sendall(b"wstunnel-tcp-test")
            data = sock.recv(1024)
            sock.close()

            assert data == b"wstunnel-tcp-test"
        finally:
            client.stop()
            client.free()
            cleanup_processes(server, echo)

    # noinspection PyTypeChecker
    def test_state_driven_udp(self, wstunnel_state, certs):
        """DB config → WstunnelState start → UDP echo → stop."""
        echo = start_echo_server("udp", 9999)
        time.sleep(0.5)

        server = start_wstunnel_server(
            "wss://0.0.0.0:8443", certs["cert"], certs["key"],
            restrict_to="127.0.0.1:9999",
        )
        assert wait_for_port(8443), "wstunnel server did not start"

        state = wstunnel_state
        state.db().set_client_config(
            remote_url="wss://127.0.0.1:8443", tls_verify=0,
        )
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 9999)
        state.start(log_level=LogLevel.INFO)
        time.sleep(1)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(b"state-udp-test", ("127.0.0.1", 51820))
            data, _ = sock.recvfrom(1024)
            sock.close()

            assert data == b"state-udp-test"
            assert state.get_status()["status"] == "started"
        finally:
            state.stop()
            cleanup_processes(server, echo)
