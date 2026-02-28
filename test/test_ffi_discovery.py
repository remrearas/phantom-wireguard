"""
Unit tests for firewall_bridge._ffi library discovery — mock-based, no .so required.
"""

import os
import pytest
from unittest.mock import patch


class TestResolvePlatform:
    def test_x86_64(self):
        with patch("firewall_bridge._ffi.platform") as mock_platform:
            mock_platform.machine.return_value = "x86_64"
            from firewall_bridge._ffi import _resolve_platform
            lib_name, arch_dir = _resolve_platform()
            assert lib_name == "libfirewall_bridge_linux.so"
            assert arch_dir == "linux-amd64"

    def test_aarch64(self):
        with patch("firewall_bridge._ffi.platform") as mock_platform:
            mock_platform.machine.return_value = "aarch64"
            from firewall_bridge._ffi import _resolve_platform
            lib_name, arch_dir = _resolve_platform()
            assert lib_name == "libfirewall_bridge_linux.so"
            assert arch_dir == "linux-arm64"

    def test_arm64(self):
        with patch("firewall_bridge._ffi.platform") as mock_platform:
            mock_platform.machine.return_value = "arm64"
            from firewall_bridge._ffi import _resolve_platform
            lib_name, arch_dir = _resolve_platform()
            assert lib_name == "libfirewall_bridge_linux.so"
            assert arch_dir == "linux-arm64"


class TestFindLibrary:
    def setup_method(self):
        """Reset cached lib before each test."""
        import firewall_bridge._ffi as ffi
        ffi._lib = None
        os.environ.pop("FIREWALL_BRIDGE_LIB_PATH", None)

    def test_env_var_path(self):
        import firewall_bridge._ffi as ffi
        os.environ["FIREWALL_BRIDGE_LIB_PATH"] = "/custom/lib.so"
        try:
            path = ffi._find_library()
            assert path == "/custom/lib.so"
        finally:
            os.environ.pop("FIREWALL_BRIDGE_LIB_PATH", None)

    def test_system_find_library(self):
        """When dist/ has no .so and find_library succeeds, return system path."""
        import firewall_bridge._ffi as ffi

        # dist/ exists but has no .so file — _find_library falls through to ctypes
        with patch("firewall_bridge._ffi.ctypes.util.find_library",
                    return_value="/usr/lib/libfirewall_bridge_linux.so"):
            path = ffi._find_library()
            assert path == "/usr/lib/libfirewall_bridge_linux.so"

    def test_not_found_raises(self):
        """When nothing is found, raise FileNotFoundError."""
        import firewall_bridge._ffi as ffi

        with patch("firewall_bridge._ffi.ctypes.util.find_library", return_value=None):
            with pytest.raises(FileNotFoundError, match="Cannot find"):
                ffi._find_library()