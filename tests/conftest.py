"""Shared test configuration.

CLI options:
    --uds     → run tests over UDS against a running daemon
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
