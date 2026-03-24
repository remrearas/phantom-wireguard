"""
Firewall Bridge E2E test fixtures.

Runs INSIDE the bridge container. IPs are known from compose env vars.
Docker socket mounted for cross-container exec (client).
"""

from __future__ import annotations

import os
import subprocess

import docker
import pytest


# ── Known IPs from compose ────────────────────────────────────────

BRIDGE_IP = os.environ.get("BRIDGE_IP", "172.30.0.10")
BRIDGE_IP6 = os.environ.get("BRIDGE_IP6", "fd00:30::10")
EXIT_IP = os.environ.get("EXIT_IP", "172.30.0.20")
EXIT_IP6 = os.environ.get("EXIT_IP6", "fd00:30::20")


# ── Shell helper ──────────────────────────────────────────────────

def sh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    if r.stdout and r.stdout.strip():
        for line in r.stdout.strip().splitlines():
            print(f"    > {line}", flush=True)
    if r.stderr and r.stderr.strip():
        for line in r.stderr.strip().splitlines():
            print(f"    > {line}", flush=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed (rc={r.returncode}): {cmd}\n{r.stderr}")
    return r


# ── Docker client fixtures ────────────────────────────────────────

@pytest.fixture(scope="session")
def docker_client():
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(scope="session")
def project_name() -> str:
    return os.environ.get("COMPOSE_PROJECT_NAME", "fw-e2e")


def _find_container(client: docker.DockerClient, project: str, service: str):
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
def client_exec(docker_client, project_name):
    """Execute command in the client container."""

    def _exec(cmd: str, check: bool = True) -> tuple[int, str]:
        container = _find_container(docker_client, project_name, "client")
        exit_code, output = container.exec_run(
            ["sh", "-c", cmd], demux=True,
        )
        stdout = (output[0] or b"").decode("utf-8", errors="replace")
        stderr = (output[1] or b"").decode("utf-8", errors="replace")
        if stdout.strip():
            for line in stdout.strip().splitlines():
                print(f"    CLIENT > {line}", flush=True)
        if stderr.strip():
            for line in stderr.strip().splitlines():
                print(f"    CLIENT > {line}", flush=True)
        if check and exit_code != 0:
            raise RuntimeError(f"client exec failed (rc={exit_code}): {cmd}\n{stdout}\n{stderr}")
        return exit_code, stdout

    return _exec


@pytest.fixture(scope="session")
def client_write_file(client_exec):
    """Write file into the client container."""
    import base64

    def _write(path: str, content: str) -> None:
        encoded = base64.b64encode(content.encode()).decode()
        client_exec(f"echo '{encoded}' | base64 -d > {path}")

    return _write


# ── Exit server config readers ────────────────────────────────────

def _read_exit_config(docker_client, project_name, config_path: str) -> str:
    """Read a config file from exit-server container."""
    container = _find_container(docker_client, project_name, "exit-server")
    r = container.exec_run(["cat", config_path])
    return r.output.decode()


@pytest.fixture(scope="session")
def exit_conf_v4(docker_client, project_name) -> str:
    """Exit server IPv4 client config with resolved IP."""
    raw = _read_exit_config(docker_client, project_name, "/config/client.conf")
    return raw.replace("__EXIT_SERVER_IP__", EXIT_IP)


@pytest.fixture(scope="session")
def exit_conf_v6(docker_client, project_name) -> str:
    """Exit server IPv6 client config with resolved IP."""
    raw = _read_exit_config(docker_client, project_name, "/config/client-v6.conf")
    return raw.replace("__EXIT_SERVER_IP6__", EXIT_IP6)
