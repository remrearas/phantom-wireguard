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

Root test configuration.
Markers: docker (container tests), integration (requires .so + NET_ADMIN).
"""

import pytest


def pytest_addoption(parser):
    parser.addoption("--docker", action="store_true", default=False,
                     help="Run Docker-based integration tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: Docker-based integration tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring .so")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="Need --docker to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)
