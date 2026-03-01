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

Unit tests for firewall_bridge.types — pure Python, no .so required.
"""

import pytest
from firewall_bridge.types import ErrorCode, AddressFamily, FirewallBridgeError, check_error


class TestErrorCode:
    def test_ok_is_zero(self):
        assert ErrorCode.OK == 0

    def test_error_codes_are_negative(self):
        for code in ErrorCode:
            if code != ErrorCode.OK:
                assert code < 0

    def test_all_codes_present(self):
        # v1 codes
        v1 = {"OK", "ALREADY_INITIALIZED", "NOT_INITIALIZED",
              "NFT_FAILED", "NETLINK_FAILED", "INVALID_PARAM",
              "IO_ERROR", "PERMISSION_DENIED"}
        # v2 codes
        v2 = {"DB_OPEN", "DB_QUERY", "DB_WRITE", "GROUP_NOT_FOUND",
              "RULE_NOT_FOUND", "INVALID_STATE", "ALREADY_STARTED",
              "NOT_STARTED", "PRESET_FAILED", "VERIFY_FAILED"}
        expected = v1 | v2
        actual = {c.name for c in ErrorCode}
        assert actual == expected

    def test_specific_values(self):
        assert ErrorCode.ALREADY_INITIALIZED == -1
        assert ErrorCode.NOT_INITIALIZED == -2
        assert ErrorCode.NFT_FAILED == -3
        assert ErrorCode.NETLINK_FAILED == -4
        assert ErrorCode.INVALID_PARAM == -5
        assert ErrorCode.IO_ERROR == -6
        assert ErrorCode.PERMISSION_DENIED == -7


class TestAddressFamily:
    def test_inet_value(self):
        assert AddressFamily.INET == 2

    def test_inet6_value(self):
        assert AddressFamily.INET6 == 10


class TestFirewallBridgeError:
    def test_known_code(self):
        err = FirewallBridgeError(-3)
        assert err.code == ErrorCode.NFT_FAILED
        assert "NFT_FAILED" in str(err)

    def test_known_code_with_detail(self):
        err = FirewallBridgeError(-4, "socket failed")
        assert err.code == ErrorCode.NETLINK_FAILED
        assert "socket failed" in str(err)

    def test_unknown_code(self):
        err = FirewallBridgeError(-99)
        assert err.code == -99
        assert "FirewallBridgeError" in str(err)

    def test_is_exception(self):
        assert issubclass(FirewallBridgeError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(FirewallBridgeError) as exc_info:
            raise FirewallBridgeError(-7, "need CAP_NET_ADMIN")
        assert exc_info.value.code == ErrorCode.PERMISSION_DENIED


class TestCheckError:
    def test_ok_passes(self):
        check_error(0)  # Should not raise

    def test_error_raises(self):
        from unittest.mock import patch, MagicMock

        mock_lib = MagicMock()
        mock_lib.firewall_bridge_get_last_error.return_value = b"test error"

        with patch("firewall_bridge._ffi.get_lib", return_value=mock_lib):
            with pytest.raises(FirewallBridgeError) as exc_info:
                check_error(-3)
            assert exc_info.value.code == ErrorCode.NFT_FAILED
            assert "test error" in exc_info.value.detail

    def test_error_no_detail(self):
        from unittest.mock import patch, MagicMock

        mock_lib = MagicMock()
        mock_lib.firewall_bridge_get_last_error.return_value = None

        with patch("firewall_bridge._ffi.get_lib", return_value=mock_lib):
            with pytest.raises(FirewallBridgeError) as exc_info:
                check_error(-1)
            assert exc_info.value.code == ErrorCode.ALREADY_INITIALIZED
            assert exc_info.value.detail == ""