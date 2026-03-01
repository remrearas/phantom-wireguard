"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge.state — mock FFI, real SQLite.
"""

import pytest
from unittest.mock import patch, MagicMock

from wstunnel_bridge.state import WstunnelState
from wstunnel_bridge.types import WstunnelError, ErrorCode, LogLevel


@pytest.fixture
def state():
    s = WstunnelState()
    yield s
    if s.status not in ("uninitialized", "closed"):
        try:
            s.close()
        except (WstunnelError, OSError):
            pass


class TestLifecycle:
    """Full lifecycle: init → start → stop → close."""

    def test_initial_status(self, state):
        assert state.status == "uninitialized"

    def test_init(self, state):
        state.init(":memory:")
        assert state.status == "initialized"
        cfg = state.db().get_config()
        assert cfg["state"] == "initialized"
        assert cfg["mode"] == "client"

    def test_init_server_mode(self, state):
        state.init(":memory:", mode="server")
        assert state.db().get_config()["mode"] == "server"

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_start_client(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)

        state.start()

        assert state.status == "started"
        _mock_start.assert_called_once()

    @patch("wstunnel_bridge.state.WstunnelState._start_server")
    def test_start_server(self, _mock_start, state):
        state.init(":memory:", mode="server")
        state.db().set_server_config(bind_url="wss://0.0.0.0:443")

        state.start()

        assert state.status == "started"
        _mock_start.assert_called_once()

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_stop(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        # Mock the client that _start_client would have created
        mock_client = MagicMock()
        mock_client.is_running.return_value = True
        state._client = mock_client

        state.stop()

        assert state.status == "stopped"
        mock_client.stop.assert_called_once()
        mock_client.free.assert_called_once()
        assert state._client is None

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_close(self, _mock_start, state):
        state.init(":memory:")
        state.close()
        assert state.status == "closed"
        assert state._db is None

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_close_from_started(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        state._client = mock_client

        state.close()

        assert state.status == "closed"
        mock_client.free.assert_called()

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_restart_cycle(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)

        state.start()
        mock_client = MagicMock()
        state._client = mock_client
        state.stop()

        assert state.status == "stopped"

        state.start()
        assert state.status == "started"

    def test_reinit_from_initialized(self, state):
        state.init(":memory:")
        state.init(":memory:")  # re-init should close previous
        assert state.status == "initialized"


class TestStateTransitions:
    """Invalid state transitions raise INVALID_STATE."""

    def test_start_without_init(self, state):
        with pytest.raises(WstunnelError) as exc:
            state.start()
        assert exc.value.code == ErrorCode.INVALID_STATE

    def test_stop_without_start(self, state):
        state.init(":memory:")
        with pytest.raises(WstunnelError) as exc:
            state.stop()
        assert exc.value.code == ErrorCode.INVALID_STATE

    def test_stop_from_uninitialized(self, state):
        with pytest.raises(WstunnelError) as exc:
            state.stop()
        assert exc.value.code == ErrorCode.INVALID_STATE

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_double_start(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        with pytest.raises(WstunnelError) as exc:
            state.start()
        assert exc.value.code == ErrorCode.INVALID_STATE

    def test_db_access_without_init(self, state):
        with pytest.raises(WstunnelError) as exc:
            state.db()
        assert exc.value.code == ErrorCode.NOT_INITIALIZED


class TestClientStart:
    """_start_client reads DB config and creates WstunnelClient correctly."""

    @patch("wstunnel_bridge.client.WstunnelClient")
    @patch("wstunnel_bridge.client.get_lib")
    @patch("wstunnel_bridge.client._setup_log_callback")
    def test_client_receives_tunnel_config(self, _mock_setup, _mock_getlib, mock_client_cls, state):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        state.init(":memory:")
        db = state.db()
        db.set_client_config(
            remote_url="wss://vpn.example.com:443",
            http_upgrade_path_prefix="ghost-secret",
            tls_verify=0,
        )
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820, timeout_secs=30)
        db.add_tunnel("tcp", "127.0.0.1", 8080, "10.0.0.1", 80)

        state._start_client(db, LogLevel.INFO)

        mock_client_cls.assert_called_once_with("wss://vpn.example.com:443", log_level=LogLevel.INFO)
        mock_instance.set_http_upgrade_path_prefix.assert_called_once_with("ghost-secret")
        mock_instance.add_tunnel_udp.assert_called_once_with(
            "127.0.0.1", 51820, "127.0.0.1", 51820, timeout_secs=30,
        )
        mock_instance.add_tunnel_tcp.assert_called_once_with(
            "127.0.0.1", 8080, "10.0.0.1", 80,
        )
        mock_instance.start.assert_called_once()

    @patch("wstunnel_bridge.client.WstunnelClient")
    @patch("wstunnel_bridge.client.get_lib")
    @patch("wstunnel_bridge.client._setup_log_callback")
    def test_client_socks5_tunnel(self, _mock_setup, _mock_getlib, mock_client_cls, state):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        state.init(":memory:")
        db = state.db()
        db.set_client_config(remote_url="wss://vpn.example.com:443")
        db.add_tunnel("socks5", "127.0.0.1", 1080, timeout_secs=60)

        state._start_client(db, LogLevel.INFO)

        mock_instance.add_tunnel_socks5.assert_called_once_with(
            "127.0.0.1", 1080, timeout_secs=60,
        )

    @patch("wstunnel_bridge.client.WstunnelClient")
    @patch("wstunnel_bridge.client.get_lib")
    @patch("wstunnel_bridge.client._setup_log_callback")
    def test_client_http_headers(self, _mock_setup, _mock_getlib, mock_client_cls, state):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        state.init(":memory:")
        db = state.db()
        db.set_client_config(remote_url="wss://vpn.example.com:443")
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        db.add_http_header("X-Custom", "value1")
        db.add_http_header("Authorization", "Bearer token")

        state._start_client(db, LogLevel.INFO)

        assert mock_instance.add_http_header.call_count == 2

    def test_client_missing_remote_url(self, state):
        state.init(":memory:")
        db = state.db()
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)

        with pytest.raises(WstunnelError) as exc:
            state._start_client(db, LogLevel.INFO)
        assert exc.value.code == ErrorCode.INVALID_PARAM
        assert "remote_url" in str(exc.value)

    def test_client_missing_tunnels(self, state):
        state.init(":memory:")
        db = state.db()
        db.set_client_config(remote_url="wss://vpn.example.com:443")

        with pytest.raises(WstunnelError) as exc:
            state._start_client(db, LogLevel.INFO)
        assert exc.value.code == ErrorCode.INVALID_PARAM
        assert "tunnel" in str(exc.value).lower()


class TestServerStart:
    """_start_server reads DB config and creates WstunnelServer correctly."""

    @patch("wstunnel_bridge.server.WstunnelServer")
    @patch("wstunnel_bridge.server.get_lib")
    @patch("wstunnel_bridge.server._setup_log_callback")
    def test_server_receives_tls_config(self, _mock_setup, _mock_getlib, mock_server_cls, state):
        mock_instance = MagicMock()
        mock_server_cls.return_value = mock_instance

        state.init(":memory:", mode="server")
        db = state.db()
        db.set_server_config(
            bind_url="wss://0.0.0.0:443",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        db.add_restriction("target", "127.0.0.1:51820")
        db.add_restriction("path_prefix", "ghost-secret")

        state._start_server(db, LogLevel.INFO)

        mock_server_cls.assert_called_once_with("wss://0.0.0.0:443", log_level=LogLevel.INFO)
        mock_instance.set_tls_certificate.assert_called_once_with("/certs/cert.pem")
        mock_instance.set_tls_private_key.assert_called_once_with("/certs/key.pem")
        mock_instance.add_restrict_to.assert_called_once_with("127.0.0.1:51820")
        mock_instance.add_restrict_path_prefix.assert_called_once_with("ghost-secret")
        mock_instance.start.assert_called_once()

    def test_server_missing_bind_url(self, state):
        state.init(":memory:", mode="server")
        db = state.db()

        with pytest.raises(WstunnelError) as exc:
            state._start_server(db, LogLevel.INFO)
        assert exc.value.code == ErrorCode.INVALID_PARAM
        assert "bind_url" in str(exc.value)


class TestGetStatus:
    """get_status() returns correct data in each state."""

    def test_uninitialized(self, state):
        status = state.get_status()
        assert status["status"] == "uninitialized"
        assert status["last_error"] == ""

    def test_initialized(self, state):
        state.init(":memory:")
        status = state.get_status()
        assert status["status"] == "initialized"
        assert status["mode"] == "client"
        assert status["tunnels_count"] == 0

    def test_initialized_with_data(self, state):
        state.init(":memory:")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.db().add_restriction("target", "127.0.0.1:51820")
        status = state.get_status()
        assert status["tunnels_count"] == 1
        assert status["restrictions_count"] == 1

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_started_with_client(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        mock_client.is_running.return_value = True
        mock_client.get_last_error.return_value = None
        state._client = mock_client

        status = state.get_status()
        assert status["status"] == "started"
        assert status["is_running"] is True

    def test_closed(self, state):
        state.init(":memory:")
        state.close()
        status = state.get_status()
        assert status["status"] == "closed"

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_started_with_runtime_error(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        mock_client.is_running.return_value = True
        mock_client.get_last_error.return_value = "connection refused"
        state._client = mock_client

        status = state.get_status()
        assert status["runtime_error"] == "connection refused"

    @patch("wstunnel_bridge.state.WstunnelState._start_server")
    def test_started_with_server_runtime_error(self, _mock_start, state):
        state.init(":memory:", mode="server")
        state.db().set_server_config(bind_url="wss://0.0.0.0:443")
        state.start()

        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.get_last_error.return_value = "bind failed"
        state._server = mock_server

        status = state.get_status()
        assert status["runtime_error"] == "bind failed"
        assert status["is_running"] is False

    def test_get_status_db_error_graceful(self, state):
        state.init(":memory:")
        state._db._conn.close()  # sabotage DB
        status = state.get_status()
        assert status["status"] == "initialized"
        assert "mode" not in status  # DB error → field not added

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_get_status_client_error_graceful(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        mock_client.is_running.side_effect = OSError("segfault")
        state._client = mock_client

        status = state.get_status()
        assert "is_running" not in status


class TestStateEdgeCases:
    """Edge cases: DB open error, unknown mode, stop errors, close-stop."""

    def test_db_open_error(self, state):
        with pytest.raises(WstunnelError) as exc:
            state.init("/nonexistent/path/impossible.db")
        assert exc.value.code == ErrorCode.DB_OPEN

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_unknown_mode(self, _mock_start, state):
        state.init(":memory:")
        state.db()._conn.execute(
            "UPDATE config SET mode = 'unknown' WHERE id = 1"
        )
        state.db()._conn.commit()

        with pytest.raises(WstunnelError) as exc:
            state.start()
        assert exc.value.code == ErrorCode.INVALID_PARAM
        assert "Unknown mode" in str(exc.value)

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_start_runtime_error(self, mock_start, state):
        mock_start.side_effect = RuntimeError("tokio panic")
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)

        with pytest.raises(WstunnelError) as exc:
            state.start()
        assert exc.value.code == ErrorCode.START_FAILED
        assert "tokio panic" in str(exc.value)

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_stop_client_error_logged(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        mock_client.stop.side_effect = WstunnelError(ErrorCode.NOT_RUNNING)
        state._client = mock_client

        state.stop()  # should not raise
        assert state.status == "stopped"
        mock_client.free.assert_called_once()

    @patch("wstunnel_bridge.state.WstunnelState._start_server")
    def test_stop_server_error_logged(self, _mock_start, state):
        state.init(":memory:", mode="server")
        state.db().set_server_config(bind_url="wss://0.0.0.0:443")
        state.start()

        mock_server = MagicMock()
        mock_server.stop.side_effect = WstunnelError(ErrorCode.NOT_RUNNING)
        state._server = mock_server

        state.stop()
        assert state.status == "stopped"
        mock_server.free.assert_called_once()

    @patch("wstunnel_bridge.state.WstunnelState._start_client")
    def test_close_stop_error_graceful(self, _mock_start, state):
        state.init(":memory:")
        state.db().set_client_config(remote_url="wss://vpn.example.com:443")
        state.db().add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)
        state.start()

        mock_client = MagicMock()
        mock_client.stop.side_effect = WstunnelError(ErrorCode.NOT_RUNNING)
        state._client = mock_client

        state.close()  # should not raise
        assert state.status == "closed"


class TestStartClientAllBranches:
    """Cover all config branches in _start_client."""

    @patch("wstunnel_bridge.client.WstunnelClient")
    @patch("wstunnel_bridge.client.get_lib")
    @patch("wstunnel_bridge.client._setup_log_callback")
    def test_all_client_options(self, _s, _g, mock_cls, state):
        mock_inst = MagicMock()
        mock_cls.return_value = mock_inst

        state.init(":memory:")
        db = state.db()
        db.set_client_config(
            remote_url="wss://vpn.example.com:443",
            http_upgrade_path_prefix="ghost",
            http_upgrade_credentials="user:pass",
            tls_verify=1,
            tls_sni_override="sni.example.com",
            tls_sni_disable=1,
            websocket_ping_frequency=10,
            websocket_mask_frame=1,
            connection_min_idle=2,
            connection_retry_max_backoff=60,
            http_proxy="proxy.example.com:8080",
            worker_threads=4,
        )
        db.add_tunnel("udp", "127.0.0.1", 51820, "127.0.0.1", 51820)

        state._start_client(db, LogLevel.INFO)

        mock_inst.set_http_upgrade_path_prefix.assert_called_once_with("ghost")
        mock_inst.set_http_upgrade_credentials.assert_called_once_with("user:pass")
        mock_inst.set_tls_verify.assert_called_once_with(True)
        mock_inst.set_tls_sni_override.assert_called_once_with("sni.example.com")
        mock_inst.set_tls_sni_disable.assert_called_once_with(True)
        mock_inst.set_websocket_ping_frequency.assert_called_once_with(10)
        mock_inst.set_websocket_mask_frame.assert_called_once_with(True)
        mock_inst.set_connection_min_idle.assert_called_once_with(2)
        mock_inst.set_connection_retry_max_backoff.assert_called_once_with(60)
        mock_inst.set_http_proxy.assert_called_once_with("proxy.example.com:8080")
        mock_inst.set_worker_threads.assert_called_once_with(4)


class TestStartServerAllBranches:
    """Cover all config branches in _start_server."""

    @patch("wstunnel_bridge.server.WstunnelServer")
    @patch("wstunnel_bridge.server.get_lib")
    @patch("wstunnel_bridge.server._setup_log_callback")
    def test_all_server_options(self, _s, _g, mock_cls, state):
        mock_inst = MagicMock()
        mock_cls.return_value = mock_inst

        state.init(":memory:", mode="server")
        db = state.db()
        db.set_server_config(
            bind_url="wss://0.0.0.0:443",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
            tls_client_ca_certs="/certs/ca.pem",
            websocket_ping_frequency=10,
            websocket_mask_frame=1,
            worker_threads=4,
        )
        db.add_restriction("target", "127.0.0.1:51820")
        db.add_restriction("path_prefix", "secret")

        state._start_server(db, LogLevel.INFO)

        mock_inst.set_tls_certificate.assert_called_once_with("/certs/cert.pem")
        mock_inst.set_tls_private_key.assert_called_once_with("/certs/key.pem")
        mock_inst.set_tls_client_ca_certs.assert_called_once_with("/certs/ca.pem")
        mock_inst.set_websocket_ping_frequency.assert_called_once_with(10)
        mock_inst.set_websocket_mask_frame.assert_called_once_with(True)
        mock_inst.set_worker_threads.assert_called_once_with(4)
        mock_inst.add_restrict_to.assert_called_once_with("127.0.0.1:51820")
        mock_inst.add_restrict_path_prefix.assert_called_once_with("secret")
