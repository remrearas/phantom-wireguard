from auth_service.crypto.password import hash_password, verify_password


def test_hash_and_verify():
    pw = "securepassword123"
    hashed = hash_password(pw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(pw, hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_hash_unique():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts


def test_verify_empty_password():
    hashed = hash_password("something")
    assert verify_password("", hashed) is False
