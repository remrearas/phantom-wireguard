from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time

from auth_service.crypto.totp import (
    build_totp_uri,
    generate_backup_codes,
    generate_secret,
    hash_backup_code,
    verify_totp,
)


def test_generate_secret():
    secret = generate_secret()
    raw = base64.b32decode(secret)
    assert len(raw) == 20  # 160-bit


def test_generate_secret_unique():
    s1 = generate_secret()
    s2 = generate_secret()
    assert s1 != s2


def test_build_totp_uri():
    uri = build_totp_uri("JBSWY3DPEHPK3PXP", "admin")
    assert uri.startswith("otpauth://totp/Phantom:admin")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=Phantom" in uri


def test_verify_totp_valid():
    secret = generate_secret()
    # Generate current code manually
    key = base64.b32decode(secret)
    counter = struct.pack(">Q", int(time.time()) // 30)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    truncated = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    code = str(truncated % 1000000).zfill(6)
    assert verify_totp(secret, code) is True


def test_verify_totp_wrong_code():
    secret = generate_secret()
    assert verify_totp(secret, "000000") is False or verify_totp(secret, "999999") is False


def test_verify_totp_bad_format():
    secret = generate_secret()
    assert verify_totp(secret, "12345") is False    # too short
    assert verify_totp(secret, "1234567") is False   # too long
    assert verify_totp(secret, "abcdef") is False    # not digits


def test_generate_backup_codes():
    codes = generate_backup_codes()
    assert len(codes) == 8
    for code in codes:
        assert len(code) == 8
        assert code.isalnum()


def test_backup_codes_unique():
    codes = generate_backup_codes()
    assert len(set(codes)) == len(codes)


def test_hash_backup_code():
    h = hash_backup_code("testcode")
    assert len(h) == 64  # SHA-256 hex
    assert h == hash_backup_code("testcode")  # deterministic
    assert h != hash_backup_code("other")
