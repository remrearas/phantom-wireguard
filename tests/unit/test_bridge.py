"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge.bridge — WstunnelBridge with mock FFI.
"""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from wstunnel_bridge.types import (
    BridgeError,
    AlreadyRunningError,
    ConfigError,
    ServerNotRunningError,
    ServerStartError,
)


def _make_mock_lib():
    """Create a mock FFI library with all required methods."""
    lib = MagicMock()
    lib.wstunnel_init_logging = MagicMock()
    lib.wstunnel_server_config_new = MagicMock(return_value=0xDEAD)
    lib.wstunnel_server_config_free = MagicMock()
    lib.wstunnel_server_config_set_bind_url = MagicMock(return_value=0)
    lib.wstunnel_server_config_set_tls_certificate = MagicMock(return_value=0)
    lib.wstunnel_server_config_set_tls_private_key = MagicMock(return_value=0)
    lib.wstunnel_server_config_add_restrict_to = MagicMock(return_value=0)
    lib.wstunnel_server_config_add_restrict_path_prefix = MagicMock(return_value=0)
    lib.wstunnel_server_start = MagicMock(return_value=0)
    lib.wstunnel_server_stop = MagicMock(return_value=0)
    lib.wstunnel_server_is_running = MagicMock(return_value=0)
    lib.wstunnel_set_log_callback = MagicMock()
    return lib


@pytest.fixture
def mock_lib():
    return _make_mock_lib()


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    for ext in ("", "-wal", "-shm"):
        p = path + ext
        if os.path.exists(p):
            os.remove(p)


@pytest.fixture
def bridge(mock_lib, db_path):
    with patch("wstunnel_bridge.bridge.get_lib", return_value=mock_lib), \
         patch("wstunnel_bridge.bridge._setup_log_callback"):
        from wstunnel_bridge.bridge import WstunnelBridge
        b = WstunnelBridge(db_path)
        yield b
        try:
            b.close()
        except (BridgeError, OSError, sqlite3.ProgrammingError):
            pass


class TestInit:
    """WstunnelBridge initialization."""

    def test_creates_db(self, bridge):
        cfg = bridge._db.get_config()
        assert cfg.state == "stopped"

    def test_not_started(self, bridge):
        assert bridge._started is False
        assert bridge._config is None


class TestConfigure:
    """configure() saves config to DB."""

    def test_configure_all_fields(self, bridge):
        bridge.configure(
            bind_url="wss://[::]:443",
            restrict_to="127.0.0.1:51820",
            restrict_path_prefix="secret",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        cfg = bridge._db.get_config()
        assert cfg.bind_url == "wss://[::]:443"
        assert cfg.restrict_to == "127.0.0.1:51820"
        assert cfg.restrict_path_prefix == "secret"
        assert cfg.tls_certificate == "/certs/cert.pem"
        assert cfg.tls_private_key == "/certs/key.pem"

    def test_configure_minimal(self, bridge):
        bridge.configure(bind_url="wss://0.0.0.0:8443")
        cfg = bridge._db.get_config()
        assert cfg.bind_url == "wss://0.0.0.0:8443"
        assert cfg.restrict_to == ""

    def test_configure_updates_existing(self, bridge):
        bridge.configure(bind_url="wss://first")
        bridge.configure(bind_url="wss://second")
        cfg = bridge._db.get_config()
        assert cfg.bind_url == "wss://second"


class TestStart:
    """start() reads DB config, creates FFI config, starts server."""

    def test_start_calls_ffi(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        mock_lib.wstunnel_server_config_new.assert_called_once()
        mock_lib.wstunnel_server_config_set_bind_url.assert_called_once()
        mock_lib.wstunnel_server_start.assert_called_once()
        assert bridge._started is True

    def test_start_sets_state(self, bridge):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        assert bridge._db.get_state() == "started"

    def test_start_with_all_options(self, bridge, mock_lib):
        bridge.configure(
            bind_url="wss://[::]:443",
            restrict_to="127.0.0.1:51820",
            restrict_path_prefix="secret",
            tls_certificate="/certs/cert.pem",
            tls_private_key="/certs/key.pem",
        )
        bridge.start()
        mock_lib.wstunnel_server_config_add_restrict_to.assert_called_once()
        mock_lib.wstunnel_server_config_add_restrict_path_prefix.assert_called_once()
        mock_lib.wstunnel_server_config_set_tls_certificate.assert_called_once()
        mock_lib.wstunnel_server_config_set_tls_private_key.assert_called_once()

    def test_start_skips_empty_optionals(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        mock_lib.wstunnel_server_config_add_restrict_to.assert_not_called()
        mock_lib.wstunnel_server_config_add_restrict_path_prefix.assert_not_called()
        mock_lib.wstunnel_server_config_set_tls_certificate.assert_not_called()
        mock_lib.wstunnel_server_config_set_tls_private_key.assert_not_called()

    def test_start_without_bind_url_raises(self, bridge):
        with pytest.raises(ConfigError, match="bind_url"):
            bridge.start()

    def test_start_twice_raises(self, bridge):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        with pytest.raises(AlreadyRunningError, match="already running"):
            bridge.start()

    def test_start_config_new_fails(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        mock_lib.wstunnel_server_config_new.return_value = None
        with pytest.raises(ServerStartError, match="Failed"):
            bridge.start()

    def test_start_ffi_error_frees_config(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        mock_lib.wstunnel_server_start.return_value = -4  # START_FAILED
        with pytest.raises(ServerStartError):
            bridge.start()
        mock_lib.wstunnel_server_config_free.assert_called_once()
        assert bridge._started is False


class TestStop:
    """stop() calls FFI stop, updates state."""

    def test_stop(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        bridge.stop()
        mock_lib.wstunnel_server_stop.assert_called_once()
        assert bridge._started is False
        assert bridge._db.get_state() == "stopped"

    def test_stop_not_running_raises(self, bridge):
        with pytest.raises(ServerNotRunningError, match="not running"):
            bridge.stop()


class TestIsRunning:
    """is_running() delegates to FFI."""

    def test_not_running(self, bridge, mock_lib):
        mock_lib.wstunnel_server_is_running.return_value = 0
        assert bridge.is_running() is False

    def test_running(self, bridge, mock_lib):
        mock_lib.wstunnel_server_is_running.return_value = 1
        assert bridge.is_running() is True


class TestClose:
    """close() stops, frees, closes DB."""

    def test_close_when_running(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        bridge.close()
        mock_lib.wstunnel_server_stop.assert_called()
        mock_lib.wstunnel_server_config_free.assert_called()

    def test_close_when_not_started(self, bridge, mock_lib):
        bridge.close()
        mock_lib.wstunnel_server_stop.assert_not_called()

    def test_close_tolerates_stop_error(self, bridge, mock_lib):
        bridge.configure(bind_url="wss://[::]:443")
        bridge.start()
        mock_lib.wstunnel_server_stop.return_value = -3  # RUNTIME
        bridge.close()  # should not raise


class TestCrashRecovery:
    """New instance with same DB can restart."""

    def test_crash_recovery(self, mock_lib, db_path):
        with patch("wstunnel_bridge.bridge.get_lib", return_value=mock_lib), \
             patch("wstunnel_bridge.bridge._setup_log_callback"):
            from wstunnel_bridge.bridge import WstunnelBridge

            b1 = WstunnelBridge(db_path)
            b1.configure(
                bind_url="wss://[::]:443",
                restrict_to="127.0.0.1:51820",
                restrict_path_prefix="secret",
            )
            b1.start()
            # Simulate crash: close DB without stopping
            b1._started = False
            b1._config = None
            b1._db.close()

            # New instance, same DB
            b2 = WstunnelBridge(db_path)
            cfg = b2._db.get_config()
            assert cfg.bind_url == "wss://[::]:443"
            assert cfg.restrict_to == "127.0.0.1:51820"

            # Restart from DB
            mock_lib.wstunnel_server_config_new.return_value = 0xBEEF
            mock_lib.wstunnel_server_start.return_value = 0
            b2.start()
            assert b2._started is True
            b2.close()


class TestContextManager:
    """with WstunnelBridge(...) as b: ..."""

    def test_context_manager(self, mock_lib, db_path):
        with patch("wstunnel_bridge.bridge.get_lib", return_value=mock_lib), \
             patch("wstunnel_bridge.bridge._setup_log_callback"):
            from wstunnel_bridge.bridge import WstunnelBridge

            with WstunnelBridge(db_path) as b:
                b.configure(bind_url="wss://[::]:443")
                b.start()
                assert b._started is True
            # close() called on exit
            mock_lib.wstunnel_server_stop.assert_called()
