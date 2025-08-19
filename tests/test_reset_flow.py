from db import Base, engine, Session, User, PasswordResetToken
from services import auth as auth_service
from werkzeug.security import generate_password_hash, check_password_hash


def setup_module(module):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = Session()
    user = User(name="Reset", email="reset@example.com", password_hash=generate_password_hash("OldPass!1234"))
    db.add(user)
    db.commit()
    db.close()


def test_token_reset_flow():
    token, error = auth_service.create_reset_token("reset@example.com")
    assert error is None and token
    err = auth_service.reset_password_with_token(token, "NewStrongPass!1234")
    assert err is None
    db = Session()
    user = db.query(User).filter_by(email="reset@example.com").first()
    assert check_password_hash(user.password_hash, "NewStrongPass!1234")
    db.close()
    # token cannot be reused
    err2 = auth_service.reset_password_with_token(token, "AnotherStrongPass!1234")
    assert err2 is not None
