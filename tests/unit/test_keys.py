from __future__ import annotations

import pytest
from nacl.signing import SigningKey

from auth_service.crypto.keys import (
    AuthSigningKeys,
    _read_key,
    build_signing_key,
    build_verify_key,
    load_auth_keys,
)
from auth_service.errors import AuthSecretsError


def test_read_key_valid(tmp_path):
    key_hex = "a" * 64
    path = tmp_path / "test_key"
    path.write_text(key_hex)
    assert _read_key(path, "test") == key_hex


def test_read_key_missing(tmp_path):
    with pytest.raises(AuthSecretsError, match="not found"):
        _read_key(tmp_path / "missing", "test")


def test_read_key_invalid_length(tmp_path):
    path = tmp_path / "bad"
    path.write_text("abc")
    with pytest.raises(AuthSecretsError, match="expected 64 hex"):
        _read_key(path, "test")


def test_read_key_invalid_chars(tmp_path):
    path = tmp_path / "bad"
    path.write_text("g" * 64)
    with pytest.raises(AuthSecretsError, match="expected 64 hex"):
        _read_key(path, "test")


def test_load_auth_keys(tmp_path):
    sk = SigningKey.generate()
    vk = sk.verify_key
    (tmp_path / "auth_signing_key").write_text(sk.encode().hex())
    (tmp_path / "auth_verify_key").write_text(vk.encode().hex())
    keys = load_auth_keys(str(tmp_path))
    assert len(keys.signing_key_hex) == 64
    assert len(keys.verify_key_hex) == 64


def test_build_signing_key():
    sk = SigningKey.generate()
    keys = AuthSigningKeys(
        signing_key_hex=sk.encode().hex(),
        verify_key_hex=sk.verify_key.encode().hex(),
    )
    built = build_signing_key(keys)
    assert built.encode() == sk.encode()


def test_build_verify_key():
    sk = SigningKey.generate()
    keys = AuthSigningKeys(
        signing_key_hex=sk.encode().hex(),
        verify_key_hex=sk.verify_key.encode().hex(),
    )
    built = build_verify_key(keys)
    assert built.encode() == sk.verify_key.encode()


def test_keys_frozen():
    keys = AuthSigningKeys(signing_key_hex="a" * 64, verify_key_hex="b" * 64)
    with pytest.raises(AttributeError):
        # noinspection PyDataclass
        keys.signing_key_hex = "c" * 64
