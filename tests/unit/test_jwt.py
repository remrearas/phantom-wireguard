from __future__ import annotations

import pytest
from nacl.signing import SigningKey

from auth_service.crypto.jwt import TokenPayload, decode_token, encode_token, token_hash
from auth_service.errors import AuthTokenError


@pytest.fixture()
def keypair():
    sk = SigningKey.generate()
    vk = sk.verify_key
    return sk, vk


def test_encode_decode(keypair):
    sk, vk = keypair
    token = encode_token(sk, sub="admin", jti="abc123", lifetime=3600)
    payload = decode_token(vk, token)
    assert payload.sub == "admin"
    assert payload.jti == "abc123"
    assert payload.typ == "access"
    assert payload.exp > payload.iat


def test_mfa_pending_type(keypair):
    sk, vk = keypair
    token = encode_token(sk, sub="user", jti="mfa1", lifetime=300, typ="mfa_pending")
    payload = decode_token(vk, token)
    assert payload.typ == "mfa_pending"


def test_expired_token(keypair):
    sk, vk = keypair
    token = encode_token(sk, sub="user", jti="exp1", lifetime=-1)
    with pytest.raises(AuthTokenError, match="expired"):
        decode_token(vk, token)


def test_invalid_signature(keypair):
    sk, vk = keypair
    token = encode_token(sk, sub="user", jti="sig1", lifetime=3600)
    parts = token.split(".")
    parts[2] = parts[2][:5] + ("A" if parts[2][5] != "A" else "B") + parts[2][6:]
    tampered = ".".join(parts)
    with pytest.raises(AuthTokenError, match="Signature verification failed"):
        decode_token(vk, tampered)


def test_wrong_key():
    sk1 = SigningKey.generate()
    sk2 = SigningKey.generate()
    token = encode_token(sk1, sub="user", jti="wk1", lifetime=3600)
    with pytest.raises(AuthTokenError, match="Signature verification failed"):
        decode_token(sk2.verify_key, token)


def test_invalid_format():
    vk = SigningKey.generate().verify_key
    with pytest.raises(AuthTokenError, match="Invalid token format"):
        decode_token(vk, "not.a.valid.token")
    with pytest.raises(AuthTokenError, match="Invalid token format"):
        decode_token(vk, "single")


def test_payload_claims(keypair):
    sk, vk = keypair
    token = encode_token(sk, sub="testuser", jti="claims1", lifetime=7200)
    payload = decode_token(vk, token)
    assert isinstance(payload, TokenPayload)
    assert payload.sub == "testuser"
    assert payload.jti == "claims1"
    assert payload.exp - payload.iat == 7200


def test_token_hash_deterministic():
    h1 = token_hash("some.jwt.token")
    h2 = token_hash("some.jwt.token")
    assert h1 == h2
    assert len(h1) == 64


def test_token_hash_different():
    h1 = token_hash("token.a")
    h2 = token_hash("token.b")
    assert h1 != h2
