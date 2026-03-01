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

Integration test fixtures for firewall-bridge v2.
"""

import os
import tempfile
import uuid

import pytest

from firewall_bridge.client import FirewallClient
from firewall_bridge.types import FirewallBridgeError


@pytest.fixture(autouse=True)
def _ensure_lib_loaded():
    """Ensure .so is loaded and env var is intact before each integration test.

    Unit tests may clear _lib and env var — this restores them.
    """
    import firewall_bridge._ffi as ffi
    env_path = os.environ.get("FIREWALL_BRIDGE_LIB_PATH", "")
    if ffi._lib is None and env_path and os.path.isfile(env_path):
        ffi.get_lib()


@pytest.fixture
def uid():
    return uuid.uuid4().hex[:8]


@pytest.fixture
def new_firewall(uid):
    """Function-scoped firewall client — fresh per test."""
    db_path = os.path.join(tempfile.gettempdir(), f"fw_{uid}.db")
    client = FirewallClient(db_path)
    yield client
    try:
        client.stop()
    except FirewallBridgeError:
        pass
    try:
        client.close()
    except FirewallBridgeError:
        pass
    for ext in ("", "-wal", "-shm"):
        path = db_path + ext
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture
def started_firewall(new_firewall):
    """Firewall client in started state."""
    new_firewall.start()
    return new_firewall
