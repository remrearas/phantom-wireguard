"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details

Unit tests for wstunnel_bridge.types — exception hierarchy, check_error, LogLevel.
"""

import pytest

from wstunnel_bridge.types import (
    BridgeError,
    ServerStartError,
    ServerNotRunningError,
    AlreadyRunningError,
    ConfigError,
    LogLevel,
    check_error,
    _ERROR_MAP,
)


class TestExceptionHierarchy:
    """All exception types inherit from BridgeError."""

    def test_bridge_error_is_exception(self):
        assert issubclass(BridgeError, Exception)

    def test_server_start_error(self):
        assert issubclass(ServerStartError, BridgeError)

    def test_server_not_running_error(self):
        assert issubclass(ServerNotRunningError, BridgeError)

    def test_already_running_error(self):
        assert issubclass(AlreadyRunningError, BridgeError)

    def test_config_error(self):
        assert issubclass(ConfigError, BridgeError)

    def test_raise_bridge_error(self):
        with pytest.raises(BridgeError, match="test"):
            raise BridgeError("test")

    def test_raise_server_start_error(self):
        with pytest.raises(ServerStartError):
            raise ServerStartError("start failed")

    def test_catch_subclass_as_bridge_error(self):
        with pytest.raises(BridgeError):
            raise ConfigError("bad config")


class TestErrorMap:
    """_ERROR_MAP maps FFI error codes to exception classes."""

    def test_already_running(self):
        assert _ERROR_MAP[-1] is AlreadyRunningError

    def test_invalid_param(self):
        assert _ERROR_MAP[-2] is ConfigError

    def test_runtime(self):
        assert _ERROR_MAP[-3] is BridgeError

    def test_start_failed(self):
        assert _ERROR_MAP[-4] is ServerStartError

    def test_not_running(self):
        assert _ERROR_MAP[-5] is ServerNotRunningError

    def test_config_null(self):
        assert _ERROR_MAP[-6] is ConfigError

    def test_all_codes_covered(self):
        expected_codes = {-1, -2, -3, -4, -5, -6}
        assert set(_ERROR_MAP.keys()) == expected_codes


class TestCheckError:
    """check_error() raises mapped exception on non-zero codes."""

    def test_zero_returns_none(self):
        assert check_error(0) is None

    def test_already_running(self):
        with pytest.raises(AlreadyRunningError, match="-1"):
            check_error(-1)

    def test_invalid_param(self):
        with pytest.raises(ConfigError, match="-2"):
            check_error(-2)

    def test_runtime_error(self):
        with pytest.raises(BridgeError, match="-3"):
            check_error(-3)

    def test_start_failed(self):
        with pytest.raises(ServerStartError, match="-4"):
            check_error(-4)

    def test_not_running(self):
        with pytest.raises(ServerNotRunningError, match="-5"):
            check_error(-5)

    def test_config_null(self):
        with pytest.raises(ConfigError, match="-6"):
            check_error(-6)

    def test_unknown_code_raises_bridge_error(self):
        with pytest.raises(BridgeError, match="-99"):
            check_error(-99)


class TestLogLevel:
    """LogLevel enum values match Rust C definitions."""

    def test_error(self):
        assert LogLevel.ERROR == 0

    def test_warn(self):
        assert LogLevel.WARN == 1

    def test_info(self):
        assert LogLevel.INFO == 2

    def test_debug(self):
        assert LogLevel.DEBUG == 3

    def test_trace(self):
        assert LogLevel.TRACE == 4

    def test_castable_to_int(self):
        assert int(LogLevel.INFO) == 2
