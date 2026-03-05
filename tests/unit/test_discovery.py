"""Unit tests for the auto-discovery engine."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.routing import Route

# noinspection PyProtectedMember
from phantom_daemon.modules import _module_to_prefix, setup_routers


class TestModuleToPrefix:
    def test_core_hello(self) -> None:
        assert _module_to_prefix("phantom_daemon.modules.core.hello.api") == "/api/core/hello"

    def test_nested_deep(self) -> None:
        assert _module_to_prefix("phantom_daemon.modules.net.vpn.status.api") == "/api/net/vpn/status"

    def test_single_category(self) -> None:
        assert _module_to_prefix("phantom_daemon.modules.health.api") == "/api/health"

    def test_bare_api(self) -> None:
        assert _module_to_prefix("phantom_daemon.modules.api") == "/api"


class TestSetupRouters:
    def test_discovers_routers(self) -> None:
        app = FastAPI()
        count = setup_routers(app)
        assert count >= 1

    def test_clients_route_registered(self) -> None:
        app = FastAPI()
        setup_routers(app)
        paths = [r.path for r in app.routes if isinstance(r, Route)]
        assert any(p.startswith("/api/core/clients/") for p in paths)

    def test_returns_router_count(self) -> None:
        app = FastAPI()
        count = setup_routers(app)
        assert isinstance(count, int)
        assert count > 0
