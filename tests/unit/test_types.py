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

Unit tests for error codes, log levels, and exception types.
"""

import pytest

from wireguard_go_bridge.types import ErrorCode, LogLevel, WireGuardError, check_error


class TestErrorCode:
    def test_ok_is_zero(self):
        assert ErrorCode.OK == 0

    def test_v1_error_codes(self):
        assert ErrorCode.INVALID_PARAM == -1
        assert ErrorCode.TUN_CREATE == -2
        assert ErrorCode.DEVICE_CREATE == -3
        assert ErrorCode.NOT_FOUND == -5
        assert ErrorCode.INTERNAL == -99

    def test_v2_error_codes(self):
        assert ErrorCode.DB_OPEN == -20
        assert ErrorCode.DB_QUERY == -21
        assert ErrorCode.DB_WRITE == -22
        assert ErrorCode.IP_EXHAUSTED == -23
        assert ErrorCode.NOT_INITIALIZED == -24
        assert ErrorCode.STATS_RUNNING == -25

    def test_all_codes_unique(self):
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestLogLevel:
    def test_levels(self):
        assert LogLevel.SILENT == 0
        assert LogLevel.ERROR == 1
        assert LogLevel.VERBOSE == 2


class TestWireGuardError:
    def test_known_code(self):
        err = WireGuardError(ErrorCode.DB_OPEN)
        assert err.code == ErrorCode.DB_OPEN
        assert "Database open" in str(err)

    def test_not_found(self):
        err = WireGuardError(ErrorCode.NOT_FOUND)
        assert err.code == ErrorCode.NOT_FOUND
        assert "not found" in str(err).lower()

    def test_not_initialized(self):
        err = WireGuardError(ErrorCode.NOT_INITIALIZED)
        assert "not initialized" in str(err).lower()

    def test_ip_exhausted(self):
        err = WireGuardError(ErrorCode.IP_EXHAUSTED)
        assert "exhausted" in str(err).lower()

    def test_unknown_code(self):
        err = WireGuardError(-999)
        assert "Unknown error" in str(err)

    def test_is_exception(self):
        assert issubclass(WireGuardError, Exception)


class TestCheckError:
    def test_ok_does_not_raise(self):
        check_error(0)

    def test_error_raises(self):
        with pytest.raises(WireGuardError) as exc_info:
            check_error(-20)
        assert exc_info.value.code == ErrorCode.DB_OPEN

    def test_internal_error(self):
        with pytest.raises(WireGuardError) as exc_info:
            check_error(-99)
        assert exc_info.value.code == ErrorCode.INTERNAL
