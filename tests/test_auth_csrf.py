import pytest
import re
from flask_app import create_app
from app.models import db, User


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client, path):
    resp = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else None


def test_register_csrf(app, client):
    # Without CSRF token the request should be rejected
    resp = client.post(
        "/register",
        data={
            "name": "New",
            "email": "new@example.com",
            "password": "StrongPass!1234",
            "confirm_password": "StrongPass!1234",
        },
    )
    assert resp.status_code == 400

    token = get_csrf_token(client, "/register")
    resp = client.post(
        "/register",
        data={
            "name": "New",
            "email": "new@example.com",
            "password": "StrongPass!1234",
            "confirm_password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="new@example.com").count() == 1
