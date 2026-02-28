"""
wstunnel-bridge integration tests.

Runs tests inside a Docker container validating that the Python FFI
bridge correctly loads the .so, creates configs, and tunnels real
UDP/TCP traffic through wstunnel WebSocket tunnels.

Test matrix:
  TestWstunnelIntegration  — CLI server  + Bridge client  (original)
  TestServerIntegration    — Bridge server + CLI client    (reverse)
  TestBridgeToBridge       — Bridge server + Bridge client (full FFI)
"""

import logging
import time

import pytest

logger = logging.getLogger("wstunnel-bridge-test")


def _log_result(result: dict) -> None:
    """Log command output to pytest live log."""
    for line in result["output"].splitlines():
        logger.info(line)


def _cleanup(container) -> None:
    """Kill all background wstunnel/socat/python processes."""
    container.exec_command("pkill -9 -f 'wstunnel' || true")
    container.exec_command("pkill -9 -f 'socat' || true")
    container.exec_command("pkill -9 -f 'run_server\\|run_client' || true")
    container.exec_command("pkill -9 -f 'python3 -c' || true")
    time.sleep(1)


def _write_and_run_bg(container, script: str, script_name: str) -> None:
    """Write a Python script to /tmp and run it in the background.

    Background Python processes crash with SIGPIPE when started via
    `python3 -c '...' &` because the parent shell closes stdout/stderr.
    Writing to a file first avoids the quoting and pipe issues.
    """
    container.exec_command(
        f"cat > /tmp/{script_name}.py << 'PYEOF'\n{script}\nPYEOF"
    )
    container.exec_command(
        f"python3 /tmp/{script_name}.py > /tmp/{script_name}.log 2>&1 &"
    )


def _wait_for_port(container, port: int, timeout: int = 10) -> bool:
    """Wait until a TCP port is accepting connections."""
    for _ in range(timeout):
        result = container.exec_command(f"ncat -z 127.0.0.1 {port} && echo OPEN")
        if "OPEN" in result["output"]:
            return True
        time.sleep(1)
    return False


# ═══════════════════════════════════════════════════════════════
# CLI server + Bridge client (original)
# Ports: server=8443  echo=9999/9998  tunnel=51820/51821
# ═══════════════════════════════════════════════════════════════

@pytest.mark.docker
class TestWstunnelIntegration:
    """End-to-end tests using CLI wstunnel server + bridge client."""

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
        """Client config create → configure → free without crash."""
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
        _cleanup(wstunnel_container)

        # Start wstunnel CLI server
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
        _cleanup(wstunnel_container)

        # Start wstunnel CLI server
        wstunnel_container.exec_command(
            "wstunnel server wss://0.0.0.0:8443 "
            "--tls-certificate /workspace/certs/cert.pem "
            "--tls-private-key /workspace/certs/key.pem "
            "--restrict-to 127.0.0.1:9998 &"
        )
        time.sleep(1)

        # Start TCP echo server
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


# ═══════════════════════════════════════════════════════════════
# Bridge server + CLI client (reverse)
# Ports: server=8444/8446  echo=9997/9996  tunnel=51822/51823
# ═══════════════════════════════════════════════════════════════

@pytest.mark.docker
class TestServerIntegration:
    """Reverse tests: bridge WstunnelServer + CLI wstunnel client."""

    def test_server_config_lifecycle(self, wstunnel_container):
        """Server config create → configure → free without crash."""
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "from wstunnel_bridge import WstunnelServer; "
            "s = WstunnelServer(\"wss://0.0.0.0:8444\"); "
            "s.set_tls_certificate(\"/workspace/certs/cert.pem\"); "
            "s.set_tls_private_key(\"/workspace/certs/key.pem\"); "
            "s.add_restrict_to(\"127.0.0.1:9997\"); "
            "s.add_restrict_path_prefix(\"v1\"); "
            "s.set_websocket_ping_frequency(30); "
            "s.free(); "
            "print(\"OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Server config lifecycle failed: {result['output']}"
        assert "OK" in result["output"]

    def test_server_context_manager(self, wstunnel_container):
        """Server context manager cleans up without crash."""
        result = wstunnel_container.exec_command(
            "python3 -c \"\n"
            "from wstunnel_bridge import WstunnelServer\n"
            "with WstunnelServer('wss://0.0.0.0:8444') as s:\n"
            "    s.set_tls_certificate('/workspace/certs/cert.pem')\n"
            "    s.set_tls_private_key('/workspace/certs/key.pem')\n"
            "    s.add_restrict_to('127.0.0.1:9997')\n"
            "print('OK')\n"
            "\""
        )
        _log_result(result)
        assert result["success"], f"Server context manager failed: {result['output']}"
        assert "OK" in result["output"]

    def test_server_udp_tunnel(self, wstunnel_container):
        """UDP traffic: bridge server + CLI client (reverse direction)."""
        _cleanup(wstunnel_container)

        # Start UDP echo server
        wstunnel_container.exec_command(
            "socat UDP-LISTEN:9997,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Start bridge server (file-based to avoid SIGPIPE)
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelServer, LogLevel
s = WstunnelServer("wss://0.0.0.0:8444", LogLevel.INFO)
s.set_tls_certificate("/workspace/certs/cert.pem")
s.set_tls_private_key("/workspace/certs/key.pem")
s.add_restrict_to("127.0.0.1:9997")
s.start()
while True:
    time.sleep(1)
""", "run_server")
        assert _wait_for_port(wstunnel_container, 8444), "Bridge server did not start"

        # Start CLI client connecting to bridge server
        wstunnel_container.exec_command(
            "wstunnel client wss://127.0.0.1:8444 "
            "-L udp://127.0.0.1:51822:127.0.0.1:9997 &"
        )
        time.sleep(1)

        # Send UDP data through the tunnel
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket; "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
            "sock.settimeout(5); "
            "sock.sendto(b\"reverse-udp-test\", (\"127.0.0.1\", 51822)); "
            "data, _ = sock.recvfrom(1024); "
            "sock.close(); "
            "assert data == b\"reverse-udp-test\", f\"Got: {data}\"; "
            "print(\"REVERSE_UDP_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Reverse UDP tunnel failed: {result['output']}"
        assert "REVERSE_UDP_OK" in result["output"]

    def test_server_tcp_tunnel(self, wstunnel_container):
        """TCP traffic: bridge server + CLI client (reverse direction)."""
        _cleanup(wstunnel_container)

        # Start TCP echo server
        wstunnel_container.exec_command(
            "socat TCP-LISTEN:9996,reuseaddr,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Start bridge server (different port from UDP test to avoid reuse)
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelServer, LogLevel
s = WstunnelServer("wss://0.0.0.0:8446", LogLevel.INFO)
s.set_tls_certificate("/workspace/certs/cert.pem")
s.set_tls_private_key("/workspace/certs/key.pem")
s.add_restrict_to("127.0.0.1:9996")
s.start()
while True:
    time.sleep(1)
""", "run_server")
        assert _wait_for_port(wstunnel_container, 8446), "Bridge server did not start"

        # Start CLI client
        wstunnel_container.exec_command(
            "wstunnel client wss://127.0.0.1:8446 "
            "-L tcp://127.0.0.1:51823:127.0.0.1:9996 &"
        )
        time.sleep(2)

        # Send TCP data through the tunnel
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket, time; "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
            "sock.settimeout(5); "
            "sock.connect((\"127.0.0.1\", 51823)); "
            "sock.sendall(b\"reverse-tcp-test\"); "
            "time.sleep(0.5); "
            "data = sock.recv(1024); "
            "sock.close(); "
            "assert data == b\"reverse-tcp-test\", f\"Got: {data}\"; "
            "print(\"REVERSE_TCP_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Reverse TCP tunnel failed: {result['output']}"
        assert "REVERSE_TCP_OK" in result["output"]


# ═══════════════════════════════════════════════════════════════
# Bridge server + Bridge client (full FFI, no CLI binary)
# Ports: server=8445/8447  echo=9995/9994  tunnel=51824/51825
# ═══════════════════════════════════════════════════════════════

@pytest.mark.docker
class TestBridgeToBridge:
    """Full FFI tests: bridge WstunnelServer + bridge WstunnelClient."""

    def test_bridge_udp_tunnel(self, wstunnel_container):
        """UDP traffic: bridge server + bridge client (pure FFI)."""
        _cleanup(wstunnel_container)

        # Start UDP echo server
        wstunnel_container.exec_command(
            "socat UDP-LISTEN:9995,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Start bridge server (separate process — own .so global state)
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelServer, LogLevel
s = WstunnelServer("wss://0.0.0.0:8445", LogLevel.INFO)
s.set_tls_certificate("/workspace/certs/cert.pem")
s.set_tls_private_key("/workspace/certs/key.pem")
s.add_restrict_to("127.0.0.1:9995")
s.start()
while True:
    time.sleep(1)
""", "run_server")
        assert _wait_for_port(wstunnel_container, 8445), "Bridge server did not start"

        # Start bridge client (separate process — own .so global state)
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelClient, LogLevel
c = WstunnelClient("wss://127.0.0.1:8445", LogLevel.INFO)
c.set_tls_verify(False)
c.add_tunnel_udp("127.0.0.1", 51824, "127.0.0.1", 9995)
c.start()
while True:
    time.sleep(1)
""", "run_client")
        time.sleep(2)

        # Send UDP data — pure socket, no FFI needed
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket; "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
            "sock.settimeout(5); "
            "sock.sendto(b\"bridge-bridge-udp\", (\"127.0.0.1\", 51824)); "
            "data, _ = sock.recvfrom(1024); "
            "sock.close(); "
            "assert data == b\"bridge-bridge-udp\", f\"Got: {data}\"; "
            "print(\"BRIDGE_UDP_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Bridge-to-bridge UDP failed: {result['output']}"
        assert "BRIDGE_UDP_OK" in result["output"]

    def test_bridge_tcp_tunnel(self, wstunnel_container):
        """TCP traffic: bridge server + bridge client (pure FFI)."""
        _cleanup(wstunnel_container)

        # Start TCP echo server
        wstunnel_container.exec_command(
            "socat TCP-LISTEN:9994,reuseaddr,fork EXEC:cat &"
        )
        time.sleep(0.5)

        # Start bridge server (different port from UDP test)
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelServer, LogLevel
s = WstunnelServer("wss://0.0.0.0:8447", LogLevel.INFO)
s.set_tls_certificate("/workspace/certs/cert.pem")
s.set_tls_private_key("/workspace/certs/key.pem")
s.add_restrict_to("127.0.0.1:9994")
s.start()
while True:
    time.sleep(1)
""", "run_server")
        assert _wait_for_port(wstunnel_container, 8447), "Bridge server did not start"

        # Start bridge client
        _write_and_run_bg(wstunnel_container, """
import time
from wstunnel_bridge import WstunnelClient, LogLevel
c = WstunnelClient("wss://127.0.0.1:8447", LogLevel.INFO)
c.set_tls_verify(False)
c.add_tunnel_tcp("127.0.0.1", 51825, "127.0.0.1", 9994)
c.start()
while True:
    time.sleep(1)
""", "run_client")
        time.sleep(2)

        # Send TCP data
        result = wstunnel_container.exec_command(
            "python3 -c '"
            "import socket, time; "
            "sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
            "sock.settimeout(5); "
            "sock.connect((\"127.0.0.1\", 51825)); "
            "sock.sendall(b\"bridge-bridge-tcp\"); "
            "time.sleep(0.5); "
            "data = sock.recv(1024); "
            "sock.close(); "
            "assert data == b\"bridge-bridge-tcp\", f\"Got: {data}\"; "
            "print(\"BRIDGE_TCP_OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Bridge-to-bridge TCP failed: {result['output']}"
        assert "BRIDGE_TCP_OK" in result["output"]
