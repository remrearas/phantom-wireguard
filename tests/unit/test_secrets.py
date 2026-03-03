"""Tests for phantom_daemon.base.secrets — key loading and derivation."""

from __future__ import annotations

import pytest

from phantom_daemon.base.errors import SecretsError
from phantom_daemon.base.secrets import ServerKeys, load_secrets

# Valid 64-char hex keys for testing
PRIV_KEY = "a" * 64
PUB_KEY = "b" * 64


def _write_keys(tmp_path, priv=PRIV_KEY, pub=PUB_KEY):
    """Helper: write key files to tmp_path and return dir string."""
    (tmp_path / "wg_private_key").write_text(priv)
    (tmp_path / "wg_public_key").write_text(pub)
    return str(tmp_path) + "/"


# ── load_secrets ─────────────────────────────────────────────────


class TestLoadSecrets:
    def test_valid_keys(self, tmp_path):
        d = _write_keys(tmp_path)
        keys = load_secrets(secrets_dir=d)
        assert isinstance(keys, ServerKeys)
        assert keys.private_key_hex == PRIV_KEY
        assert keys.public_key_hex == PUB_KEY

    def test_missing_private_key(self, tmp_path):
        (tmp_path / "wg_public_key").write_text(PUB_KEY)
        with pytest.raises(SecretsError, match="wg_private_key"):
            load_secrets(secrets_dir=str(tmp_path) + "/")

    def test_missing_public_key(self, tmp_path):
        (tmp_path / "wg_private_key").write_text(PRIV_KEY)
        with pytest.raises(SecretsError, match="wg_public_key"):
            load_secrets(secrets_dir=str(tmp_path) + "/")

    def test_short_key(self, tmp_path):
        _write_keys(tmp_path, priv="abcd1234")
        with pytest.raises(SecretsError, match="64 hex"):
            load_secrets(secrets_dir=str(tmp_path) + "/")

    def test_non_hex_key(self, tmp_path):
        _write_keys(tmp_path, pub="g" * 64)
        with pytest.raises(SecretsError, match="64 hex"):
            load_secrets(secrets_dir=str(tmp_path) + "/")

    def test_whitespace_stripped(self, tmp_path):
        _write_keys(tmp_path, priv=f"  {PRIV_KEY}\n")
        keys = load_secrets(secrets_dir=str(tmp_path) + "/")
        assert keys.private_key_hex == PRIV_KEY
