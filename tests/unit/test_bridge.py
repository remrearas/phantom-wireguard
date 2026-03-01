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

Unit tests for WireGuardBridge — mocked FFI.
"""

from unittest.mock import MagicMock, patch

import pytest

from wireguard_go_bridge.bridge import WireGuardBridge
from wireguard_go_bridge.types import (
    DeviceCreateError,
    IpcError,
    DeviceUpError,
    DeviceDownError,
    DeviceNotFoundError,
)


@pytest.fixture
def mock_lib():
    lib = MagicMock()
    lib.NewPersistentDevice.return_value = 1
    lib.DeviceIpcSet.return_value = 0
    lib.DeviceIpcGet.return_value = None
    lib.DeviceUp.return_value = 0
    lib.DeviceDown.return_value = 0
    lib.DeviceClose.return_value = 0
    lib.FreeString.return_value = None
    return lib


@pytest.fixture
def bridge(mock_lib, tmp_path):
    db_file = tmp_path / "device.db"
    db_file.touch()
    with patch("wireguard_go_bridge.bridge.get_lib", return_value=mock_lib):
        return WireGuardBridge(ifname="wg0", mtu=1420, db_path=str(db_file))


class TestInit:
    def test_db_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="device.db not found"):
            WireGuardBridge(ifname="wg0", mtu=1420, db_path="/nonexistent/device.db")

    def test_ffi_failure_raises(self, mock_lib, tmp_path):
        db_file = tmp_path / "device.db"
        db_file.touch()
        mock_lib.NewPersistentDevice.return_value = -3
        with patch("wireguard_go_bridge.bridge.get_lib", return_value=mock_lib):
            with pytest.raises(DeviceCreateError):
                WireGuardBridge(ifname="wg0", mtu=1420, db_path=str(db_file))

    def test_successful_init(self, bridge, mock_lib):
        assert bridge.handle == 1
        mock_lib.NewPersistentDevice.assert_called_once()


class TestIpcSet:
    def test_success(self, bridge, mock_lib):
        bridge.ipc_set("private_key=abc\n")
        mock_lib.DeviceIpcSet.assert_called_once_with(1, b"private_key=abc\n")

    def test_failure_raises(self, bridge, mock_lib):
        mock_lib.DeviceIpcSet.return_value = -4
        with pytest.raises(IpcError):
            bridge.ipc_set("invalid")


class TestIpcGet:
    def test_returns_string(self, bridge, mock_lib):
        mock_lib.DeviceIpcGet.return_value = None
        result = bridge.ipc_get()
        assert result == ""

    def test_delegates_to_ffi(self, bridge, mock_lib):
        bridge.ipc_get()
        mock_lib.DeviceIpcGet.assert_called_once_with(1)


class TestUpDown:
    def test_up_success(self, bridge, mock_lib):
        bridge.up()
        mock_lib.DeviceUp.assert_called_once_with(1)

    def test_up_failure(self, bridge, mock_lib):
        mock_lib.DeviceUp.return_value = -7
        with pytest.raises(DeviceUpError):
            bridge.up()

    def test_down_success(self, bridge, mock_lib):
        bridge.down()
        mock_lib.DeviceDown.assert_called_once_with(1)

    def test_down_failure(self, bridge, mock_lib):
        mock_lib.DeviceDown.return_value = -8
        with pytest.raises(DeviceDownError):
            bridge.down()


class TestClose:
    def test_close_delegates(self, bridge, mock_lib):
        bridge.close()
        mock_lib.DeviceClose.assert_called_once_with(1)

    def test_close_zeroes_handle(self, bridge):
        bridge.close()
        assert bridge.handle == 0

    def test_close_idempotent(self, bridge, mock_lib):
        bridge.close()
        bridge.close()
        mock_lib.DeviceClose.assert_called_once()

    def test_close_failure_raises(self, bridge, mock_lib):
        mock_lib.DeviceClose.return_value = -5
        with pytest.raises(DeviceNotFoundError):
            bridge.close()


class TestContextManager:
    def test_enter_returns_self(self, bridge):
        assert bridge.__enter__() is bridge

    def test_exit_closes(self, bridge, mock_lib):
        bridge.__exit__(None, None, None)
        mock_lib.DeviceClose.assert_called_once()

    def test_with_block(self, mock_lib, tmp_path):
        db_file = tmp_path / "device.db"
        db_file.touch()
        with patch("wireguard_go_bridge.bridge.get_lib", return_value=mock_lib):
            with WireGuardBridge("wg0", 1420, str(db_file)) as b:
                assert b.handle == 1
        mock_lib.DeviceClose.assert_called_once()