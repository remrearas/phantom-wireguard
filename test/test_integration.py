"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""
"""
wireguard-go-bridge integration tests.

Runs tests inside a Docker container validating that the Python FFI
bridge correctly loads the .so, generates keys, and creates real
WireGuard tunnels via network namespaces.
"""

import logging

import pytest

logger = logging.getLogger("wireguard-go-bridge-test")


def _log_result(result: dict) -> None:
    """Log command output to pytest live log."""
    for line in result["output"].splitlines():
        logger.info(line)


@pytest.mark.docker
class TestBridgeIntegration:
    """End-to-end tests using real network namespaces and TUN devices."""

    def test_library_loads(self, bridge_container):
        """Bridge .so loads and returns version info."""
        result = bridge_container.exec_command(
            "python3 -c '"
            "from wireguard_go_bridge import get_bridge_version, get_wireguard_go_version; "
            "print(get_bridge_version()); "
            "print(get_wireguard_go_version())'"
        )
        _log_result(result)
        assert result["success"], f"Library load failed: {result['output']}"
        lines = result["output"].strip().split("\n")
        assert len(lines) == 2
        assert len(lines[0]) > 0
        assert len(lines[1]) > 0

    def test_key_generation(self, bridge_container):
        """Key generation works through FFI bridge."""
        result = bridge_container.exec_command(
            "python3 -c '"
            "from wireguard_go_bridge import WireGuardKeys; "
            "priv, pub = WireGuardKeys.generate_keypair(); "
            "assert len(priv) == 64; "
            "assert len(pub) == 64; "
            "print(\"OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Key generation failed: {result['output']}"
        assert "OK" in result["output"]

    def test_key_deterministic(self, bridge_container):
        """Same private key always derives same public key."""
        result = bridge_container.exec_command(
            "python3 -c '"
            "from wireguard_go_bridge import WireGuardKeys; "
            "priv = WireGuardKeys.generate_private(); "
            "pub1 = WireGuardKeys.derive_public(priv); "
            "pub2 = WireGuardKeys.derive_public(priv); "
            "assert pub1 == pub2; "
            "print(\"OK\")'"
        )
        _log_result(result)
        assert result["success"], f"Deterministic test failed: {result['output']}"
        assert "OK" in result["output"]

    def test_netns_tunnel(self, bridge_container):
        """
        Full tunnel test: create WireGuard interfaces via FFI bridge,
        configure peers, pass traffic through network namespaces.
        """
        result = bridge_container.run_test_sh()
        assert result["success"], f"Integration test failed (exit={result['exit_code']})"
        assert "ALL TESTS PASSED" in result["output"]