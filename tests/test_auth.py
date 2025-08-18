from auth import is_valid_password
from werkzeug.security import generate_password_hash, check_password_hash


def test_is_valid_password_rules():
    assert is_valid_password('StrongPass!1234')
    assert is_valid_password('averylongpassphrasewithonlylettersandmore')
    assert not is_valid_password('weakpass')


def test_password_hash_roundtrip():
    password = 'StrongPass!1234'
    hashed = generate_password_hash(password)
    assert check_password_hash(hashed, password)
    assert not check_password_hash(hashed, 'wrongpassword')
