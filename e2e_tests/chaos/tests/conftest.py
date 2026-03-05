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

Fixtures for chaos E2E tests.

Runs INSIDE the master container. Provides:
- Docker client for exec into service containers
- Gateway URL for daemon API access
- Container interaction helpers
- restart_daemon: kill + restart daemon and wait for ready
- wait_for_api: poll gateway until daemon API responds
"""

from __future__ import annotations

import base64
import os
import time

import docker
import pytest
import requests


@pytest.fixture(scope="session")
def docker_client():
    """Docker client via mounted socket."""
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(scope="session")
def gateway_url() -> str:
    """Daemon API base URL via gateway service."""
    return os.environ.get("GATEWAY_URL", "http://gateway:9080")


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


@pytest.fixture(scope="session")
def restart_daemon(docker_client, project_name, gateway_url):
    """Factory fixture: restart daemon container and wait for API ready.

    Uses docker restart (SIGTERM → SIGKILL after timeout).
    Waits for gateway to respond with 200 on /api/core/firewall/groups/list.
    Returns the time (seconds) it took for the daemon to become ready.
    """

    def _restart(timeout: int = 60) -> float:
        daemon = _find_container(docker_client, project_name, "daemon")
        gateway = _find_container(docker_client, project_name, "gateway")
        t0 = time.monotonic()

        # Restart daemon — SIGTERM then SIGKILL after 10s
        daemon.restart(timeout=10)

        # Gateway (socat) holds stale UDS handle — must restart too
        gateway.restart(timeout=5)

        # Poll gateway until daemon API responds
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = requests.get(
                    f"{gateway_url}/api/core/firewall/groups/list",
                    timeout=2,
                )
                if resp.status_code == 200:
                    return time.monotonic() - t0
            except (requests.ConnectionError, requests.Timeout):
                pass
            time.sleep(1)
        raise TimeoutError(f"Daemon not ready after {timeout}s restart")

    return _restart


@pytest.fixture(scope="session")
def wait_for_api(gateway_url):
    """Factory fixture: poll daemon API until it responds."""

    def _wait(path: str = "/api/core/firewall/groups/list", timeout: int = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = requests.get(f"{gateway_url}{path}", timeout=2)
                if resp.status_code == 200:
                    return
            except (requests.ConnectionError, requests.Timeout):
                pass
            time.sleep(1)
        raise TimeoutError(f"API not ready after {timeout}s at {path}")

    return _wait
