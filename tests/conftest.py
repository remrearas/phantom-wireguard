"""Shared test configuration.

CLI options:
    --uds     → run tests over UDS against a running daemon
    --docker  → run Docker-based integration tests (3-container topology)
"""

from __future__ import annotations

import pytest

UDS_DEFAULT = "/var/run/phantom/daemon.sock"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--uds",
        default=None,
        help=f"Run tests over UDS against a running daemon (default path: {UDS_DEFAULT})",
    )
    parser.addoption(
        "--docker",
        action="store_true",
        default=False,
        help="Run Docker-based integration tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "docker: Docker-based integration tests (3-container topology)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="Need --docker to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)
