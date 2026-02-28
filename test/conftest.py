"""
Pytest configuration for firewall_bridge tests.

Usage:
    pytest test/test_types.py              # Unit tests (no .so needed)
    pytest --docker test/                  # All tests including Docker integration
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--docker", action="store_true", default=False,
        help="Run integration tests that require Docker"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: requires Docker container")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="Need --docker flag to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)