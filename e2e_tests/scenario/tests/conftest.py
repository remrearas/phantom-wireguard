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

Fixtures for scenario E2E tests.

Runs INSIDE the master container. Provides:
- Docker client for exec into exit-server/client containers
- Auth URL for auth-service API access (JWT proxy)
- Admin password from bootstrap
- Helper functions for container interaction
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import docker
import pytest


@pytest.fixture(scope="session")
def docker_client():
    """Docker client via mounted socket."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(scope="session")
def auth_url() -> str:
    """Auth-service base URL."""
    return os.environ.get("PHANTOM_AUTH_URL", "http://auth-service:8443")


@pytest.fixture(scope="session")
def admin_password() -> str:
    """Bootstrap admin password from mounted secret."""
    pw_path = Path("/run/secrets/admin_password")
    if pw_path.exists():
        return pw_path.read_text().strip()
    raise RuntimeError("Admin password not found at /run/secrets/admin_password")


@pytest.fixture(scope="session")
def project_name() -> str:
    """Compose project name (set by runner)."""
    return os.environ["COMPOSE_PROJECT_NAME"]


def _find_container(client: docker.DockerClient, project: str, service: str):
    """Find a running container by compose project + service label."""
    containers = client.containers.list(
        filters={
            "label": [
                f"com.docker.compose.project={project}",
                f"com.docker.compose.service={service}",
            ],
        },
    )
    if not containers:
        raise RuntimeError(f"Container not found: {service} (project={project})")
    return containers[0]


@pytest.fixture(scope="session")
def container_exec(docker_client, project_name):
    """Factory fixture: execute command in a compose service container."""

    def _exec(
        service: str,
        cmd: str | list[str],
        check: bool = True,
        environment: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        container = _find_container(docker_client, project_name, service)
        if isinstance(cmd, list):
            cmd = ["sh", "-c", " ".join(cmd)] if len(cmd) > 1 else cmd
        else:
            cmd = ["sh", "-c", cmd]
        exit_code, output = container.exec_run(
            cmd, environment=environment, demux=True,
        )
        stdout = (output[0] or b"").decode("utf-8", errors="replace")
        stderr = (output[1] or b"").decode("utf-8", errors="replace")
        if check and exit_code != 0:
            raise RuntimeError(
                f"exec in {service} failed (rc={exit_code}): {cmd}\n"
                f"stdout: {stdout}\nstderr: {stderr}"
            )
        return exit_code, stdout

    return _exec


@pytest.fixture(scope="session")
def container_write_file(container_exec):
    """Factory fixture: write file into a compose service container."""

    def _write(service: str, path: str, content: str) -> None:
        encoded = base64.b64encode(content.encode()).decode()
        container_exec(service, f"echo '{encoded}' | base64 -d > {path}")

    return _write


@pytest.fixture(scope="session")
def container_ip(docker_client, project_name):
    """Factory fixture: get container IP on compose default network."""

    def _ip(service: str) -> str:
        container = _find_container(docker_client, project_name, service)
        container.reload()
        networks = container.attrs["NetworkSettings"]["Networks"]
        for net_info in networks.values():
            ip = net_info.get("IPAddress")
            if ip:
                return ip
        raise RuntimeError(f"No IP found for {service}")

    return _ip
