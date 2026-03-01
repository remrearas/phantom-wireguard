"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

wstunnel-bridge test configuration.

--docker flag gates integration tests that require native .so library.
Unit tests run on any platform without the flag.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--docker", action="store_true", default=False,
        help="Run Docker-based integration tests",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: Docker-based integration tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker"):
        skip_marker = pytest.mark.skip(reason="Need --docker to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_marker)
