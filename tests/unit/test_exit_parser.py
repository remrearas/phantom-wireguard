"""Tests for phantom_daemon.base.exit_store.parser — WireGuard config parser."""

from __future__ import annotations

import base64
import os

import pytest

# noinspection PyProtectedMember
from phantom_daemon.base.exit_store.parser import (
    ParsedWireGuardConfig,
    _base64_to_hex,
    parse_wireguard_config,
)


# ── Helper ──────────────────────────────────────────────────────

def _make_key_b64() -> str:
    """Generate a random 32-byte key as base64."""
    return base64.b64encode(os.urandom(32)).decode()


def _make_conf(
    private_key: str | None = None,
    address: str = "10.0.0.2/32",
    public_key: str | None = None,
    preshared_key: str | None = None,
    endpoint: str = "vpn.example.com:51820",
    allowed_ips: str = "0.0.0.0/0, ::/0",
    keepalive: int | None = 25,
) -> str:
    """Build a minimal WireGuard .conf string."""
    priv = private_key or _make_key_b64()
    pub = public_key or _make_key_b64()

    lines = [
        "[Interface]",
        f"PrivateKey = {priv}",
        f"Address = {address}",
        "",
        "[Peer]",
        f"PublicKey = {pub}",
    ]
    if preshared_key:
        lines.append(f"PresharedKey = {preshared_key}")
    lines.append(f"Endpoint = {endpoint}")
    lines.append(f"AllowedIPs = {allowed_ips}")
    if keepalive is not None:
        lines.append(f"PersistentKeepalive = {keepalive}")
    return "\n".join(lines)


# ── TestBase64ToHex ──────────────────────────────────────────────


class TestBase64ToHex:
    def test_valid_key(self):
        raw = os.urandom(32)
        b64 = base64.b64encode(raw).decode()
        assert _base64_to_hex(b64) == raw.hex()

    def test_length_32(self):
        b64 = _make_key_b64()
        hex_str = _base64_to_hex(b64)
        assert len(bytes.fromhex(hex_str)) == 32

    def test_short_key_raises(self):
        b64 = base64.b64encode(b"short").decode()
        with pytest.raises(ValueError, match="32 bytes"):
            _base64_to_hex(b64)

    def test_long_key_raises(self):
        b64 = base64.b64encode(os.urandom(64)).decode()
        with pytest.raises(ValueError, match="32 bytes"):
            _base64_to_hex(b64)


# ── TestParseWireGuardConfig ─────────────────────────────────────


class TestParseWireGuardConfig:
    def test_minimal_config(self):
        conf = _make_conf()
        result = parse_wireguard_config(conf)
        assert isinstance(result, ParsedWireGuardConfig)
        assert result.address == "10.0.0.2/32"
        assert result.endpoint == "vpn.example.com:51820"

    def test_private_key_hex(self):
        raw = os.urandom(32)
        priv_b64 = base64.b64encode(raw).decode()
        conf = _make_conf(private_key=priv_b64)
        result = parse_wireguard_config(conf)
        assert result.private_key_hex == raw.hex()

    def test_public_key_hex(self):
        raw = os.urandom(32)
        pub_b64 = base64.b64encode(raw).decode()
        conf = _make_conf(public_key=pub_b64)
        result = parse_wireguard_config(conf)
        assert result.public_key_hex == raw.hex()

    def test_preshared_key(self):
        raw = os.urandom(32)
        psk_b64 = base64.b64encode(raw).decode()
        conf = _make_conf(preshared_key=psk_b64)
        result = parse_wireguard_config(conf)
        assert result.preshared_key_hex == raw.hex()

    def test_no_preshared_key(self):
        conf = _make_conf()
        result = parse_wireguard_config(conf)
        assert result.preshared_key_hex == ""

    def test_allowed_ips(self):
        conf = _make_conf(allowed_ips="10.0.0.0/8, 192.168.0.0/16")
        result = parse_wireguard_config(conf)
        assert result.allowed_ips == "10.0.0.0/8, 192.168.0.0/16"

    def test_default_allowed_ips(self):
        """When AllowedIPs not in config, default to full tunnel."""
        priv = _make_key_b64()
        pub = _make_key_b64()
        conf = (
            "[Interface]\n"
            f"PrivateKey = {priv}\n"
            "Address = 10.0.0.2/32\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        result = parse_wireguard_config(conf)
        assert result.allowed_ips == "0.0.0.0/0, ::/0"

    def test_keepalive(self):
        conf = _make_conf(keepalive=15)
        result = parse_wireguard_config(conf)
        assert result.keepalive == 15

    def test_default_keepalive(self):
        conf = _make_conf(keepalive=None)
        result = parse_wireguard_config(conf)
        assert result.keepalive == 5

    def test_comments_ignored(self):
        priv = _make_key_b64()
        pub = _make_key_b64()
        conf = (
            "# This is a comment\n"
            "[Interface]\n"
            f"PrivateKey = {priv}\n"
            "Address = 10.0.0.2/32\n"
            "# Another comment\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        result = parse_wireguard_config(conf)
        assert result.address == "10.0.0.2/32"

    def test_frozen_dataclass(self):
        conf = _make_conf()
        result = parse_wireguard_config(conf)
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            result.address = "changed"


class TestParseWireGuardConfigErrors:
    def test_missing_private_key(self):
        pub = _make_key_b64()
        conf = (
            "[Interface]\n"
            "Address = 10.0.0.2/32\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        with pytest.raises(ValueError, match="PrivateKey"):
            parse_wireguard_config(conf)

    def test_missing_address(self):
        priv = _make_key_b64()
        pub = _make_key_b64()
        conf = (
            "[Interface]\n"
            f"PrivateKey = {priv}\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        with pytest.raises(ValueError, match="Address"):
            parse_wireguard_config(conf)

    def test_missing_public_key(self):
        priv = _make_key_b64()
        conf = (
            "[Interface]\n"
            f"PrivateKey = {priv}\n"
            "Address = 10.0.0.2/32\n\n"
            "[Peer]\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        with pytest.raises(ValueError, match="PublicKey"):
            parse_wireguard_config(conf)

    def test_missing_endpoint(self):
        priv = _make_key_b64()
        pub = _make_key_b64()
        conf = (
            "[Interface]\n"
            f"PrivateKey = {priv}\n"
            "Address = 10.0.0.2/32\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
        )
        with pytest.raises(ValueError, match="Endpoint"):
            parse_wireguard_config(conf)

    def test_invalid_key(self):
        pub = _make_key_b64()
        conf = (
            "[Interface]\n"
            "PrivateKey = not-valid-base64!!!\n"
            "Address = 10.0.0.2/32\n\n"
            "[Peer]\n"
            f"PublicKey = {pub}\n"
            "Endpoint = 1.2.3.4:51820\n"
        )
        with pytest.raises((ValueError, UnicodeDecodeError)):
            parse_wireguard_config(conf)
