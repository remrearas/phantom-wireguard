"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Integration: lifecycle, config setters, get_last_error, free() branches,
__repr__, socks5 tunnel — everything that needs a real .so to exercise.
"""

import time

import pytest

from wstunnel_bridge import get_version, WstunnelState, LogLevel


@pytest.mark.docker
class TestLibraryLoad:
    """Bridge .so loads correctly."""

    def test_version(self):
        v = get_version()
        assert len(v) > 0
        assert "." in v

    def test_log_callback_sets(self):
        from wstunnel_bridge import set_log_callback
        logs = []
        set_log_callback(lambda level, msg: logs.append((level, msg)))


@pytest.mark.docker
class TestStateLifecycle:
    """WstunnelState init/start/stop/close with real .so."""

    def test_init_creates_db(self, wstunnel_state):
        status = wstunnel_state.get_status()
        assert status["status"] == "initialized"
        assert status["mode"] == "client"

    def test_server_mode_init(self, uid):
        import os, tempfile
        db_path = os.path.join(tempfile.gettempdir(), f"ws_srv_{uid}.db")
        state = WstunnelState()
        state.init(db_path, mode="server")
        assert state.get_status()["mode"] == "server"
        state.close()
        for ext in ("", "-wal", "-shm"):
            p = db_path + ext
            if os.path.exists(p):
                os.remove(p)


@pytest.mark.docker
class TestClientAllSetters:
    """Exercise every WstunnelClient config setter with real .so."""

    def test_all_config_methods(self, certs):
        from wstunnel_bridge import WstunnelClient

        c = WstunnelClient("wss://127.0.0.1:8443")
        c.set_http_upgrade_path_prefix("ghost-secret")
        c.set_http_upgrade_credentials("user:pass")
        c.set_tls_verify(False)
        c.set_tls_sni_override("sni.example.com")
        c.set_tls_sni_disable(True)
        c.set_websocket_ping_frequency(10)
        c.set_websocket_mask_frame(True)
        c.set_connection_min_idle(2)
        c.set_connection_retry_max_backoff(60)
        c.set_http_proxy("proxy.example.com:8080")
        c.add_http_header("X-Custom", "value")
        c.set_worker_threads(4)
        c.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 9999)
        c.add_tunnel_tcp("127.0.0.1", 51821, "127.0.0.1", 9998)
        c.add_tunnel_socks5("127.0.0.1", 1080, timeout_secs=60)
        c.free()

    def test_get_last_error_none(self):
        from wstunnel_bridge import WstunnelClient

        c = WstunnelClient("wss://127.0.0.1:8443")
        c.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 9999)
        err = c.get_last_error()
        assert err is None
        c.free()

    def test_repr_idle(self):
        from wstunnel_bridge import WstunnelClient

        c = WstunnelClient("wss://127.0.0.1:8443")
        r = repr(c)
        assert "idle" in r
        c.free()

    def test_repr_freed(self):
        from wstunnel_bridge import WstunnelClient

        c = WstunnelClient("wss://127.0.0.1:8443")
        c.free()
        r = repr(c)
        assert "freed" in r

    def test_free_while_running(self, certs):
        """free() on running client calls stop() first."""
        from wstunnel_bridge import WstunnelClient
        from .conftest import (
            start_echo_server, start_wstunnel_server,
            wait_for_port, cleanup_processes,
        )

        echo = start_echo_server("udp", 9999)
        time.sleep(0.5)
        server = start_wstunnel_server(
            "wss://0.0.0.0:8443", certs["cert"], certs["key"],
            restrict_to="127.0.0.1:9999",
        )
        assert wait_for_port(8443)

        c = WstunnelClient("wss://127.0.0.1:8443", LogLevel.INFO)
        c.set_tls_verify(False)
        c.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 9999)
        c.start()
        time.sleep(1)
        assert c.is_running()

        c.free()  # should call stop() internally
        assert c._freed

        cleanup_processes(server, echo)

    def test_get_last_error_after_bad_start(self):
        """get_last_error exercises decode path after failed connect."""
        from wstunnel_bridge import WstunnelClient

        c = WstunnelClient("wss://127.0.0.1:9999", LogLevel.ERROR)
        c.set_tls_verify(False)
        c.add_tunnel_udp("127.0.0.1", 51820, "127.0.0.1", 9999)
        c.start()
        time.sleep(2)

        # Exercise get_last_error — may return None or string
        _ = c.get_last_error()
        c.stop()
        c.free()


@pytest.mark.docker
class TestServerAllSetters:
    """Exercise every WstunnelServer config setter with real .so."""

    def test_all_config_methods(self, certs):
        from wstunnel_bridge import WstunnelServer

        s = WstunnelServer("wss://0.0.0.0:8444")
        s.set_tls_certificate(certs["cert"])
        s.set_tls_private_key(certs["key"])
        s.set_tls_client_ca_certs(certs["cert"])  # use same cert as CA for test
        s.add_restrict_to("127.0.0.1:9997")
        s.add_restrict_path_prefix("v1")
        s.set_websocket_ping_frequency(10)
        s.set_websocket_mask_frame(True)
        s.set_worker_threads(4)
        s.free()

    def test_get_last_error_none(self, certs):
        from wstunnel_bridge import WstunnelServer

        s = WstunnelServer("wss://0.0.0.0:8444")
        s.set_tls_certificate(certs["cert"])
        s.set_tls_private_key(certs["key"])
        err = s.get_last_error()
        assert err is None
        s.free()

    def test_repr_idle(self):
        from wstunnel_bridge import WstunnelServer

        s = WstunnelServer("wss://0.0.0.0:8444")
        r = repr(s)
        assert "idle" in r
        s.free()

    def test_repr_freed(self):
        from wstunnel_bridge import WstunnelServer

        s = WstunnelServer("wss://0.0.0.0:8444")
        s.free()
        r = repr(s)
        assert "freed" in r

    def test_free_while_running(self, certs):
        """free() on running server calls stop() first."""
        from wstunnel_bridge import WstunnelServer

        s = WstunnelServer("wss://0.0.0.0:8444", LogLevel.INFO)
        s.set_tls_certificate(certs["cert"])
        s.set_tls_private_key(certs["key"])
        s.add_restrict_to("127.0.0.1:9997")
        s.start()
        time.sleep(1)
        assert s.is_running()

        s.free()  # should call stop() internally
        assert s._freed

    def test_context_manager(self, certs):
        from wstunnel_bridge import WstunnelServer

        with WstunnelServer("wss://0.0.0.0:8444") as s:
            s.set_tls_certificate(certs["cert"])
            s.set_tls_private_key(certs["key"])
