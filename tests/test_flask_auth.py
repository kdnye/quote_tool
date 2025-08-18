import os
import pytest
from werkzeug.security import generate_password_hash

# Ensure tests use a dedicated database
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from flask_app import create_app
from db import Base, engine, Session, User

# Create tables for the test database
Base.metadata.create_all(engine)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(autouse=True)
def seed_user():
    """Ensure a known user exists for authentication tests."""
    with Session() as session:
        session.query(User).delete()
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=generate_password_hash("Password!123"),
            role="user",
            is_approved=True,
        )
        session.add(user)
        session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_creates_session(client):
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "Password!123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is not None


def test_logout_clears_session(client):
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "Password!123"},
        follow_redirects=True,
    )
    client.get("/logout", follow_redirects=True)
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is None
