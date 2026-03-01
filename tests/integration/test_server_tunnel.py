"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration: Bridge server + CLI client (reverse direction).

Ports: server=8444/8446  echo=9997/9996  tunnel=51822/51823
"""

import socket
import time

import pytest

from wstunnel_bridge import WstunnelServer, LogLevel
from .conftest import (
    start_echo_server, start_wstunnel_client,
    wait_for_port, cleanup_processes,
)


@pytest.mark.docker
class TestServerTunnel:
    """Bridge WstunnelServer + CLI wstunnel client — reverse direction."""

    # noinspection PyTypeChecker
    def test_udp_echo(self, certs):
        echo = start_echo_server("udp", 9997)
        time.sleep(0.5)

        server = WstunnelServer("wss://0.0.0.0:8444", LogLevel.INFO)
        server.set_tls_certificate(certs["cert"])
        server.set_tls_private_key(certs["key"])
        server.add_restrict_to("127.0.0.1:9997")
        server.start()
        assert wait_for_port(8444), "Bridge server did not start"

        cli_client = start_wstunnel_client(
            "wss://127.0.0.1:8444",
            "udp://127.0.0.1:51822:127.0.0.1:9997",
        )
        time.sleep(1)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(b"reverse-udp-test", ("127.0.0.1", 51822))
            data, _ = sock.recvfrom(1024)
            sock.close()

            assert data == b"reverse-udp-test"
        finally:
            cleanup_processes(cli_client)
            server.stop()
            server.free()
            cleanup_processes(echo)

    # noinspection PyTypeChecker
    def test_tcp_echo(self, certs):
        echo = start_echo_server("tcp", 9996)
        time.sleep(0.5)

        server = WstunnelServer("wss://0.0.0.0:8446", LogLevel.INFO)
        server.set_tls_certificate(certs["cert"])
        server.set_tls_private_key(certs["key"])
        server.add_restrict_to("127.0.0.1:9996")
        server.start()
        assert wait_for_port(8446), "Bridge server did not start"

        cli_client = start_wstunnel_client(
            "wss://127.0.0.1:8446",
            "tcp://127.0.0.1:51823:127.0.0.1:9996",
        )
        time.sleep(2)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", 51823))
            sock.sendall(b"reverse-tcp-test")
            time.sleep(0.5)
            data = sock.recv(1024)
            sock.close()

            assert data == b"reverse-tcp-test"
        finally:
            cleanup_processes(cli_client)
            server.stop()
            server.free()
            cleanup_processes(echo)
