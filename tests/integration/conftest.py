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

Integration test fixtures.
new_bridge: function-scoped running bridge per test.
new_bridge_factory: creates isolated bridge instances for recovery tests.
"""

import os
import tempfile
import uuid
from typing import Optional

import pytest

from wireguard_go_bridge.client import BridgeClient
from wireguard_go_bridge.types import WireGuardError


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker", default=False):
        skip = pytest.mark.skip(reason="Need --docker to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def uid():
    """Unique 8-char hex for each test."""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def new_bridge(uid):
    """Function-scoped bridge — fresh for every test."""
    db_path = os.path.join(tempfile.gettempdir(), f"bridge_{uid}.db")
    ifname = f"wg-{uid[:6]}"

    bridge = BridgeClient(db_path, ifname, 51820, log_level=1)
    bridge.setup(
        endpoint="10.0.0.1:51820",
        network="10.100.0.0/24",
        dns_primary="1.1.1.1",
        dns_secondary="9.9.9.9",
    )
    bridge.start()

    yield bridge

    try:
        bridge.stop()
    except WireGuardError:
        pass
    try:
        bridge.close()
    except WireGuardError:
        pass

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def new_bridge_factory():
    """Factory for isolated bridge instances (crash recovery tests)."""
    active: Optional[BridgeClient] = None
    counter = [0]

    def _create(db_path: Optional[str] = None,
                ifname: Optional[str] = None,
                port: Optional[int] = None) -> tuple[BridgeClient, str]:
        nonlocal active

        if active is not None:
            try:
                active.close()
            except WireGuardError:
                pass

        idx = counter[0]
        counter[0] += 1

        if db_path is None:
            db_path = os.path.join(tempfile.gettempdir(), f"factory_{uuid.uuid4().hex[:8]}.db")
        if ifname is None:
            ifname = f"wg-f{idx}-{uuid.uuid4().hex[:4]}"
        if port is None:
            port = 52000 + idx

        bridge = BridgeClient(db_path, ifname, port)
        active = bridge
        return bridge, db_path

    yield _create

    if active is not None:
        try:
            active.close()
        except WireGuardError:
            pass