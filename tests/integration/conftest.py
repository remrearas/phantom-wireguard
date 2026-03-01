"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration test fixtures for wstunnel-bridge v2.

Provides fresh WstunnelState instances, cert paths, and cleanup helpers.
All integration tests run inside Docker container with real .so library.
"""

import os
import subprocess
import tempfile
import time
import uuid

import pytest

from wstunnel_bridge.state import WstunnelState
from wstunnel_bridge.types import WstunnelError


@pytest.fixture(autouse=True)
def _ensure_lib_loaded():
    """Ensure .so is loaded and env var is intact before each test."""
    import wstunnel_bridge._ffi as ffi
    env_path = os.environ.get("WSTUNNEL_BRIDGE_LIB_PATH", "")
    if ffi._lib is None and env_path and os.path.isfile(env_path):
        ffi.get_lib()


@pytest.fixture
def uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def certs():
    """Self-signed certificate paths (created by Dockerfile)."""
    return {
        "cert": "/workspace/certs/cert.pem",
        "key": "/workspace/certs/key.pem",
    }


@pytest.fixture
def wstunnel_state(uid):
    """Function-scoped WstunnelState with fresh DB."""
    db_path = os.path.join(tempfile.gettempdir(), f"ws_{uid}.db")
    state = WstunnelState()
    state.init(db_path)
    yield state
    try:
        state.close()
    except (WstunnelError, OSError):
        pass
    for ext in ("", "-wal", "-shm"):
        path = db_path + ext
        if os.path.exists(path):
            os.remove(path)


def wait_for_port(port: int, timeout: int = 10) -> bool:
    """Wait until a TCP port is accepting connections."""
    for _ in range(timeout):
        try:
            result = subprocess.run(
                ["ncat", "-z", "127.0.0.1", str(port)],
                capture_output=True, timeout=2,
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(1)
    return False


def start_echo_server(protocol: str, port: int) -> subprocess.Popen:
    """Start socat echo server (UDP or TCP)."""
    if protocol == "udp":
        cmd = f"socat UDP-LISTEN:{port},fork EXEC:cat"
    else:
        cmd = f"socat TCP-LISTEN:{port},reuseaddr,fork EXEC:cat"
    return subprocess.Popen(cmd, shell=True)


def start_wstunnel_server(
    bind_url: str, cert: str, key: str, restrict_to: str = ""
) -> subprocess.Popen:
    """Start wstunnel CLI server as background process."""
    cmd = [
        "wstunnel", "server", bind_url,
        "--tls-certificate", cert,
        "--tls-private-key", key,
    ]
    if restrict_to:
        cmd.extend(["--restrict-to", restrict_to])
    return subprocess.Popen(cmd)


def start_wstunnel_client(
    remote_url: str, tunnel: str
) -> subprocess.Popen:
    """Start wstunnel CLI client as background process."""
    cmd = ["wstunnel", "client", remote_url, "-L", tunnel]
    return subprocess.Popen(cmd)


def cleanup_processes(*procs: subprocess.Popen):
    """Terminate and wait for background processes."""
    for p in procs:
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
