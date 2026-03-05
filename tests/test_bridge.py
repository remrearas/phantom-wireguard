"""Integration tests for the compose bridge.

Requires:
  - compose_bridge.so built and discoverable
  - Docker daemon running
"""

from __future__ import annotations

import pytest

from compose_bridge import ComposeBridge, ExecResult


COMPOSE_FILE = "tests/docker-compose-test.yml"


@pytest.fixture(scope="module")
def bridge():
    """Create bridge, start services, yield, tear down."""
    with ComposeBridge(COMPOSE_FILE, project_name="cb-test") as b:
        b.up()
        yield b
        b.down()


class TestBridgeVersion:
    def test_version_string(self):
        with ComposeBridge(COMPOSE_FILE, project_name="cb-ver") as b:
            assert b.version() == "1.0.0"


class TestProjectLifecycle:
    def test_ps_returns_containers(self, bridge: ComposeBridge):
        containers = bridge.ps()
        assert isinstance(containers, list)
        assert len(containers) >= 1
        assert any(c["service"] == "alpine" for c in containers)

    def test_exec_echo(self, bridge: ComposeBridge):
        result = bridge.exec("alpine", ["echo", "hello"])
        assert isinstance(result, ExecResult)
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_exec_with_env(self, bridge: ComposeBridge):
        result = bridge.exec(
            "alpine",
            ["sh", "-c", "echo $MY_VAR"],
            env={"MY_VAR": "phantom"},
        )
        assert result.exit_code == 0
        assert "phantom" in result.stdout

    def test_logs(self, bridge: ComposeBridge):
        logs = bridge.logs("alpine")
        assert isinstance(logs, str)
