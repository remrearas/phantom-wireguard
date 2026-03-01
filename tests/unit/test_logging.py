"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge logging — Rust→Python log bridge.
Mock-based, no native library needed.
"""

import logging
from unittest.mock import patch, MagicMock

import pytest

import wstunnel_bridge._ffi as _ffi_mod


@pytest.fixture(autouse=True)
def _reset_log_state():
    """Reset module-level logging state between tests."""
    orig_registered = _ffi_mod._log_callback_registered
    orig_callback = _ffi_mod._active_log_callback
    _ffi_mod._log_callback_registered = False
    _ffi_mod._active_log_callback = None
    yield
    _ffi_mod._log_callback_registered = orig_registered
    _ffi_mod._active_log_callback = orig_callback


class TestLevelMap:
    """Rust log levels map to correct Python logging levels."""

    def test_error_maps(self):
        assert _ffi_mod._LEVEL_MAP[0] == logging.ERROR

    def test_warn_maps(self):
        assert _ffi_mod._LEVEL_MAP[1] == logging.WARNING

    def test_info_maps(self):
        assert _ffi_mod._LEVEL_MAP[2] == logging.INFO

    def test_debug_maps(self):
        assert _ffi_mod._LEVEL_MAP[3] == logging.DEBUG

    def test_trace_maps_to_debug(self):
        assert _ffi_mod._LEVEL_MAP[4] == logging.DEBUG

    def test_all_five_levels_covered(self):
        assert len(_ffi_mod._LEVEL_MAP) == 5


class TestSetupLogCallback:
    """_setup_log_callback() registers Rust→Python bridge once."""

    @patch.object(_ffi_mod, "get_lib")
    def test_registers_callback(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod._setup_log_callback()

        mock_lib.wstunnel_set_log_callback.assert_called_once()
        assert _ffi_mod._log_callback_registered is True
        assert _ffi_mod._active_log_callback is not None

    @patch.object(_ffi_mod, "get_lib")
    def test_idempotent(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod._setup_log_callback()
        _ffi_mod._setup_log_callback()
        _ffi_mod._setup_log_callback()

        mock_lib.wstunnel_set_log_callback.assert_called_once()

    @patch.object(_ffi_mod, "get_lib")
    def test_callback_routes_to_python_logging(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod._setup_log_callback()

        # Extract the C callback that was registered
        c_callback = mock_lib.wstunnel_set_log_callback.call_args[0][0]

        with patch.object(_ffi_mod._log, "log") as mock_log:
            # Simulate Rust calling the callback
            c_callback(2, b"tunnel connected", None)
            mock_log.assert_called_once_with(logging.INFO, "tunnel connected")

    @patch.object(_ffi_mod, "get_lib")
    def test_callback_handles_empty_message(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod._setup_log_callback()
        c_callback = mock_lib.wstunnel_set_log_callback.call_args[0][0]

        with patch.object(_ffi_mod._log, "log") as mock_log:
            c_callback(0, None, None)
            mock_log.assert_called_once_with(logging.ERROR, "")

    @patch.object(_ffi_mod, "get_lib")
    def test_callback_unknown_level_defaults_to_debug(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod._setup_log_callback()
        c_callback = mock_lib.wstunnel_set_log_callback.call_args[0][0]

        with patch.object(_ffi_mod._log, "log") as mock_log:
            c_callback(99, b"unknown level", None)
            mock_log.assert_called_once_with(logging.DEBUG, "unknown level")


class TestSetLogCallback:
    """set_log_callback() allows custom callback override."""

    @patch.object(_ffi_mod, "get_lib")
    def test_custom_callback_registered(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        messages = []
        _ffi_mod.set_log_callback(lambda lvl, msg: messages.append((lvl, msg)))

        assert _ffi_mod._log_callback_registered is True
        mock_lib.wstunnel_set_log_callback.assert_called_once()

    @patch.object(_ffi_mod, "get_lib")
    def test_custom_callback_receives_messages(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        messages = []
        _ffi_mod.set_log_callback(lambda lvl, msg: messages.append((lvl, msg)))

        c_callback = mock_lib.wstunnel_set_log_callback.call_args[0][0]
        c_callback(1, b"warning message", None)

        assert messages == [(1, "warning message")]

    @patch.object(_ffi_mod, "get_lib")
    def test_custom_prevents_auto_setup(self, mock_get_lib):
        mock_lib = MagicMock()
        mock_get_lib.return_value = mock_lib

        _ffi_mod.set_log_callback(lambda lvl, msg: None)
        _ffi_mod._setup_log_callback()  # should be no-op

        # Only the custom callback call, not the auto one
        mock_lib.wstunnel_set_log_callback.assert_called_once()


class TestLoggerName:
    """Logger uses correct name for module identification."""

    def test_logger_name(self):
        assert _ffi_mod._log.name == "wstunnel_bridge"