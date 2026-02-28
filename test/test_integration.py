"""
wstunnel-bridge integration tests.

Runs tests inside a Docker container validating that the Python FFI
bridge correctly loads the .so, creates configs, and tunnels real
UDP/TCP traffic through a wstunnel WebSocket server.
"""

import logging
import time

import pytest

logger = logging.getLogger("wstunnel-bridge-test")


def _log_result(result: dict) -> None:
    """Log command output to pytest live log."""
    for line in result["output"].splitlines():
        logger.info(line)


@pytest.mark.docker
class TestWstunnelIntegration:
    """End-to-end tests using wstunnel server + bridge client."""

    def test_library_loads(self, wstunnel_container):
        """Bridge .so loads and returns version info."""
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "from wstunnel_bridge import get_version; "
            "v = get_version(); "
            "print(v); "
            "assert len(v) > 0'"
        )
        _log_result(result)
        assert result["success"], f"Library load failed: {result['output']}"

    def test_config_lifecycle(self, wstunnel_container):
        """Config create → configure → free without crash."""
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "from wstunnel_bridge import WstunnelClient; "
            "c = WstunnelClient(\"wss://127.0.0.1:8443\"); "
            "c.set_http_upgrade_path_prefix(\"test\"); "
            "c.set_tls_verify(False); "
            "c.set_websocket_ping_frequency(30); "
            "c.set_connection_min_idle(1); "
            "c.add_tunnel_udp(\"127.0.0.1\", 51820, \"127.0.0.1\", 9999); "
            "c.add_tunnel_tcp(\"127.0.0.1\", 51821, \"127.0.0.1\", 9998); "
            "c.free(); "
            "print(\"OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Config lifecycle failed: {result['output']}"
        assert "OK" in result["output"]

    def test_context_manager(self, wstunnel_container):
        """Context manager cleans up without crash."""
        result = wstunnel_container.exec_command(
            "python3 -c \"\n"
            "from wstunnel_bridge import WstunnelClient\n"
            "with WstunnelClient('wss://127.0.0.1:8443') as c:\n"
            "    c.add_tunnel_udp('127.0.0.1', 51820, '127.0.0.1', 9999)\n"
            "print('OK')\n"
            "\""
        )
        _log_result(result)
        assert result["success"], f"Context manager failed: {result['output']}"
        assert "OK" in result["output"]

    def test_log_callback(self, wstunnel_container):
        """Log callback can be set without crash."""
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "from wstunnel_bridge import set_log_callback; "
            "logs = []; "
            "set_log_callback(lambda level, msg: logs.append((level, msg))); "
            "print(\"OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Log callback failed: {result['output']}"
        assert "OK" in result["output"]

    def test_udp_tunnel(self, wstunnel_container):
        """UDP traffic passes through wstunnel WebSocket tunnel."""
        # Start wstunnel server
        wstunnel_container.exec_command(
            "wstunnel server wss://0.0.0.0:8443 "
            "--tls-certificate /workspace/certs/cert.pem "
            "--tls-private-key /workspace/certs/key.pem "
            "--restrict-to 127.0.0.1:9999 &"
        )
        time.sleep(1)

        # Start UDP echo server
        wstunnel_container.exec_command(
            "socat UDP-LISTEN:9999,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Run bridge client and send UDP data
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket, time; "
            "from wstunnel_bridge import WstunnelClient, LogLevel; "
            "c = WstunnelClient(\"wss://127.0.0.1:8443\", LogLevel.INFO); "
            "c.set_tls_verify(False); "
            "c.add_tunnel_udp(\"127.0.0.1\", 51820, \"127.0.0.1\", 9999); "
            "c.start(); "
            "time.sleep(1); "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
            "sock.settimeout(5); "
            "sock.sendto(b\"wstunnel-test\", (\"127.0.0.1\", 51820)); "
            "data, _ = sock.recvfrom(1024); "
            "sock.close(); "
            "c.stop(); "
            "c.free(); "
            "assert data == b\"wstunnel-test\", f\"Got: {data}\"; "
            "print(\"UDP_TUNNEL_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"UDP tunnel failed: {result['output']}"
        assert "UDP_TUNNEL_OK" in result["output"]

    def test_tcp_tunnel(self, wstunnel_container):
        """TCP traffic passes through wstunnel WebSocket tunnel."""
        # Ensure wstunnel server is running (may already be from UDP test)
        wstunnel_container.exec_command("pkill -f 'wstunnel server' || true")
        time.sleep(0.5)

        wstunnel_container.exec_command(
            "wstunnel server wss://0.0.0.0:8443 "
            "--tls-certificate /workspace/certs/cert.pem "
            "--tls-private-key /workspace/certs/key.pem "
            "--restrict-to 127.0.0.1:9998 &"
        )
        time.sleep(1)

        # Start TCP echo server
        wstunnel_container.exec_command("pkill -f 'socat TCP' || true")
        wstunnel_container.exec_command(
            "socat TCP-LISTEN:9998,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Run bridge client and send TCP data
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket, time; "
            "from wstunnel_bridge import WstunnelClient, LogLevel; "
            "c = WstunnelClient(\"wss://127.0.0.1:8443\", LogLevel.INFO); "
            "c.set_tls_verify(False); "
            "c.add_tunnel_tcp(\"127.0.0.1\", 51821, \"127.0.0.1\", 9998); "
            "c.start(); "
            "time.sleep(1); "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
            "sock.settimeout(5); "
            "sock.connect((\"127.0.0.1\", 51821)); "
            "sock.sendall(b\"wstunnel-tcp-test\"); "
            "data = sock.recv(1024); "
            "sock.close(); "
            "c.stop(); "
            "c.free(); "
            "assert data == b\"wstunnel-tcp-test\", f\"Got: {data}\"; "
            "print(\"TCP_TUNNEL_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"TCP tunnel failed: {result['output']}"
        assert "TCP_TUNNEL_OK" in result["output"]
