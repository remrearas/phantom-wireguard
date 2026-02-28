"""
wstunnel-bridge test configuration.

Uses Docker SDK via docker_test_helper to run wstunnel server + bridge
client integration tests inside a container.
"""

import logging

import pytest

logger = logging.getLogger("wstunnel-bridge-test")


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
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        pytest.skip("Docker not available")


@pytest.fixture(scope="session")
def wstunnel_container(request, docker_available):
    """Session-scoped container for all integration tests."""
    from docker_test_helper import WstunnelTestContainer

    container = WstunnelTestContainer()
    container.build_image()
    container.start_container()

    yield container

    if not request.config.getoption("--no-docker-cleanup"):
        container.cleanup()
    else:
        logger.info(f"Container preserved: {container.container_name}")
