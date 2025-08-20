import re
import pytest
from werkzeug.security import generate_password_hash
import pandas as pd

from flask_app import create_app
from app.models import db, User, Quote


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


@pytest.fixture(autouse=True)
def clear_db(app):
    with app.app_context():
        Quote.query.delete()
        User.query.delete()
        db.session.commit()
    yield


def seed_user(app, email="test@example.com", password="Password!123"):
    with app.app_context():
        user = User(name="Test", email=email, is_active=True)
        user.password_hash = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
        return user


def login(client, email="test@example.com", password="Password!123"):
    token = get_csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


def get_csrf_token(client, url):
    response = client.get(url)
    html = response.data.decode()
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token not found"
    return match.group(1)


def test_login_and_logout(app, client):
    seed_user(app)
    response = login(client)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is not None

    client.get("/logout", follow_redirects=False)
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is None


def test_quote_requires_login(client):
    response = client.get("/quotes/new")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_quote_creation(app, client, monkeypatch):
    seed_user(app)
    login(client)
    token = get_csrf_token(client, "/login")

    workbook = {
        "Hotshot Rates": pd.DataFrame(
            {
                "MILES": [100, 200],
                "ZONE": ["A", "X"],
                "PER LB": [2.0, 0.0],
                "FUEL": [0.1, 0.2],
                "MIN": [50, 1.5],
                "WEIGHT BREAK": [100, 200],
            }
        )
    }

    monkeypatch.setattr(
        "app.quotes.routes._get_normalized_workbook", lambda: workbook
    )
    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": 120,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["price"] == pytest.approx(270.0)

    with app.app_context():
        assert Quote.query.count() == 1


def test_login_requires_csrf_token(app, client):
    seed_user(app)
    client.get("/login")
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "Password!123"},
    )
    assert response.status_code == 400


def test_quote_creation_requires_csrf_token(app, client):
    seed_user(app)
    login(client)
    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": 120,
        },
    )
    assert response.status_code == 400


def test_register_requires_csrf_token(app, client):
    response = client.post(
        "/register",
        data={
            "name": "New",
            "email": "new@example.com",
            "password": "Password!123",
            "confirm_password": "Password!123",
        },
    )
    assert response.status_code == 400


def test_reset_password_requires_csrf_token(app, client):
    seed_user(app)
    response = client.post(
        "/reset-password",
        data={
            "email": "test@example.com",
            "new_password": "NewPassword!123",
            "confirm_password": "NewPassword!123",
        },
    )
    assert response.status_code == 400
