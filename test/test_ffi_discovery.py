"""
Unit tests for wstunnel_bridge._ffi library discovery — mock-based, no native library needed.
"""

import os
from unittest.mock import patch

import pytest

from wstunnel_bridge._ffi import _resolve_platform, _find_library


class TestResolvePlatform:
    """_resolve_platform() returns correct lib name and arch directory."""

    @patch("wstunnel_bridge._ffi.platform")
    def test_linux_x86_64(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name == "libwstunnel_bridge_linux.so"
        assert arch_dir == "linux-amd64"

    @patch("wstunnel_bridge._ffi.platform")
    def test_linux_aarch64(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "aarch64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name == "libwstunnel_bridge_linux.so"
        assert arch_dir == "linux-arm64"

    @patch("wstunnel_bridge._ffi.platform")
    def test_linux_arm64_alias(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "arm64"
        lib_name, arch_dir = _resolve_platform()
        assert arch_dir == "linux-arm64"

    @patch("wstunnel_bridge._ffi.platform")
    def test_darwin_uses_dylib(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        lib_name, arch_dir = _resolve_platform()
        assert lib_name.endswith(".dylib")

    @patch("wstunnel_bridge._ffi.platform")
    def test_unknown_platform_fallback(self, mock_platform):
        mock_platform.system.return_value = "FreeBSD"
        mock_platform.machine.return_value = "riscv64"
        lib_name, arch_dir = _resolve_platform()
        assert arch_dir == "freebsd-riscv64"


class TestFindLibrary:
    """_find_library() resolves library path via env var or system search."""

    @patch.dict(os.environ, {"WSTUNNEL_BRIDGE_LIB_PATH": "/opt/lib/libwstunnel_bridge_linux.so"})
    @patch("wstunnel_bridge._ffi.os.path.isfile", return_value=True)
    def test_env_var_path(self, _mock_isfile):
        result = _find_library()
        assert result == "/opt/lib/libwstunnel_bridge_linux.so"

    @patch.dict(os.environ, {"WSTUNNEL_BRIDGE_LIB_PATH": "/nonexistent/lib.so"})
    @patch("wstunnel_bridge._ffi.os.path.isfile", return_value=False)
    @patch("wstunnel_bridge._ffi.ctypes.util.find_library", return_value=None)
    def test_env_var_invalid_path_falls_through(self, _mock_find, _mock_isfile):
        with pytest.raises(FileNotFoundError):
            _find_library()

    @patch.dict(os.environ, {}, clear=True)
    @patch("wstunnel_bridge._ffi.ctypes.util.find_library", return_value="/usr/lib/libwstunnel_bridge_linux.so")
    def test_system_find_library(self, _mock_find):
        os.environ.pop("WSTUNNEL_BRIDGE_LIB_PATH", None)
        result = _find_library()
        assert result == "/usr/lib/libwstunnel_bridge_linux.so"

    @patch.dict(os.environ, {}, clear=True)
    @patch("wstunnel_bridge._ffi.ctypes.util.find_library", return_value=None)
    def test_not_found_raises(self, _mock_find):
        os.environ.pop("WSTUNNEL_BRIDGE_LIB_PATH", None)
        with pytest.raises(FileNotFoundError, match="WSTUNNEL_BRIDGE_LIB_PATH"):
            _find_library()
