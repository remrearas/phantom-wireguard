"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
wireguard-go-bridge integration test configuration.

Uses Docker SDK via docker_test_helper to run netns-based WireGuard
tests inside a privileged Debian container.
"""

import logging

import docker
from docker.errors import DockerException
import pytest

from docker_test_helper import BridgeTestContainer

logger = logging.getLogger("wireguard-go-bridge-test")


def pytest_addoption(parser):
    parser.addoption("--docker", action="store_true", default=False, help="Run Docker-based integration tests")
    parser.addoption("--no-docker-cleanup", action="store_true", default=False, help="Keep container after tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "docker: Docker-based integration tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker"):
        skip_marker = pytest.mark.skip(reason="Need --docker to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def docker_available():
    """Check Docker daemon is reachable."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except (DockerException, ConnectionError, FileNotFoundError):
        pytest.skip("Docker not available")


@pytest.fixture(scope="session")
def bridge_container(request, docker_available):
    """Session-scoped container for all integration tests."""
    container = BridgeTestContainer()
    container.build_image()
    container.start_container()

    yield container

    if not request.config.getoption("--no-docker-cleanup"):
        container.cleanup()
    else:
        logger.info(f"Container preserved: {container.container_name}")