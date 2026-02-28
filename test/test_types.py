"""
Unit tests for wstunnel_bridge.types — pure Python, no native library needed.
"""

import pytest

from wstunnel_bridge.types import ErrorCode, LogLevel, WstunnelError, check_error


class TestErrorCode:
    """ErrorCode enum values match C header definitions."""

    def test_ok(self):
        assert ErrorCode.OK == 0

    def test_already_running(self):
        assert ErrorCode.ALREADY_RUNNING == -1

    def test_invalid_param(self):
        assert ErrorCode.INVALID_PARAM == -2

    def test_runtime(self):
        assert ErrorCode.RUNTIME == -3

    def test_start_failed(self):
        assert ErrorCode.START_FAILED == -4

    def test_not_running(self):
        assert ErrorCode.NOT_RUNNING == -5

    def test_config_null(self):
        assert ErrorCode.CONFIG_NULL == -6


class TestLogLevel:
    """LogLevel enum values match C header definitions."""

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


class TestCheckError:
    """check_error() raises WstunnelError for non-zero codes."""

    def test_ok_no_exception(self):
        check_error(0)

    def test_already_running(self):
        with pytest.raises(WstunnelError) as exc_info:
            check_error(-1)
        assert exc_info.value.code == ErrorCode.ALREADY_RUNNING

    def test_invalid_param(self):
        with pytest.raises(WstunnelError) as exc_info:
            check_error(-2)
        assert exc_info.value.code == ErrorCode.INVALID_PARAM

    def test_config_null(self):
        with pytest.raises(WstunnelError) as exc_info:
            check_error(-6)
        assert exc_info.value.code == ErrorCode.CONFIG_NULL

    def test_unknown_code(self):
        with pytest.raises(WstunnelError) as exc_info:
            check_error(-99)
        assert exc_info.value.code == -99
        assert "Unknown error" in str(exc_info.value)


class TestWstunnelError:
    """WstunnelError exception formatting."""

    def test_known_code_message(self):
        err = WstunnelError(-1)
        assert "already running" in str(err).lower()
        assert err.code == ErrorCode.ALREADY_RUNNING

    def test_with_detail(self):
        err = WstunnelError(-2, "bad port value")
        assert "bad port value" in str(err)
        assert err.detail == "bad port value"

    def test_unknown_code_message(self):
        err = WstunnelError(-99)
        assert "-99" in str(err)

    def test_code_stored_as_enum(self):
        err = WstunnelError(-3)
        assert err.code == ErrorCode.RUNTIME

    def test_unknown_code_stored_as_int(self):
        err = WstunnelError(-99)
        assert err.code == -99
