# noinspection DuplicatedCode
# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS
# Licensed under AGPL-3.0 - see LICENSE file for details
# Third-party licenses - see THIRD_PARTY_LICENSES file for details
# WireGuard® is a registered trademark of Jason A. Donenfeld.

import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--docker",
        action="store_true",
        default=False,
        help="Run Docker-based integration tests"
    )
    parser.addoption(
        "--no-docker-cleanup",
        action="store_true",
        default=False,
        help="Don't cleanup Docker containers after tests (for debugging)"
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "docker: mark test to run only with Docker containers"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--docker"):
        skip_docker = pytest.mark.skip(reason="need --docker option to run")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)


@pytest.fixture(scope="session")
def docker_available():
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception as e:
        logger.warning(f"Docker not available: {e}")
        return False


@pytest.fixture(scope="session")
def shared_docker_container(request):
    if not request.config.getoption("--docker", default=False):
        return None

    from phantom.modules.core.tests.helpers import WireGuardTestContainer

    logger.info("Creating shared Docker container for test session")
    container = WireGuardTestContainer()

    try:
        container.build_image(show_output=True)
        container.start_container(show_output=True)

        logger.info(f"Docker container ready: {container.container_name}")
        yield container

    finally:
        if not request.config.getoption("--no-docker-cleanup", default=False):
            logger.info("Cleaning up Docker container after test session")
            container.cleanup()
        else:
            logger.info(f"Keeping Docker container for debugging: {container.container_name}")
