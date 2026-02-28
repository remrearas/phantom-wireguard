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

Unit tests for FFI library discovery.
Platform resolution, environment variable paths, system library fallback.
"""

from unittest.mock import patch

import pytest

from wireguard_go_bridge._ffi import _resolve_platform, _find_library


class TestResolvePlatform:
    @patch("wireguard_go_bridge._ffi.platform")
    def test_linux_amd64(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name == "wireguard_go_bridge.so"
        assert arch_dir == "linux-amd64"

    @patch("wireguard_go_bridge._ffi.platform")
    def test_linux_arm64(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "aarch64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name == "wireguard_go_bridge.so"
        assert arch_dir == "linux-arm64"

    @patch("wireguard_go_bridge._ffi.platform")
    def test_darwin_arm64(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name == "wireguard_go_bridge.dylib"
        assert arch_dir == "darwin-arm64"

    @patch("wireguard_go_bridge._ffi.platform")
    def test_unknown_platform(self, mock_platform):
        mock_platform.system.return_value = "FreeBSD"
        mock_platform.machine.return_value = "riscv64"
        lib_name, arch_dir = _resolve_platform()
        assert arch_dir == "freebsd-riscv64"


class TestFindLibrary:
    def test_env_var_path(self, tmp_path):
        lib_file = tmp_path / "wireguard_go_bridge.so"
        lib_file.touch()
        with patch.dict("os.environ", {"WIREGUARD_GO_BRIDGE_LIB_PATH": str(lib_file)}):
            assert _find_library() == str(lib_file)

    @patch("wireguard_go_bridge._ffi._resolve_platform", return_value=("wireguard_go_bridge.so", "linux-nonexistent"))
    @patch("wireguard_go_bridge._ffi.ctypes.util.find_library", return_value=None)
    def test_not_found_raises(self, _mock_find, _mock_resolve):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(FileNotFoundError, match="not found"):
                _find_library()

    @patch("wireguard_go_bridge._ffi._resolve_platform", return_value=("wireguard_go_bridge.so", "linux-nonexistent"))
    @patch("wireguard_go_bridge._ffi.ctypes.util.find_library", return_value="/usr/lib/wireguard_go_bridge.so")
    def test_system_find_library(self, _mock_find, _mock_resolve):
        with patch.dict("os.environ", {}, clear=True):
            result = _find_library()
            assert result == "/usr/lib/wireguard_go_bridge.so"
