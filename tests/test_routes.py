import pytest
from werkzeug.security import generate_password_hash
import pandas as pd
import re

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
def get_csrf_token(client, path):
    """Fetch CSRF token by visiting the given path."""
    resp = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else None


def login(client, email="test@example.com", password="Password!123"):
    token = get_csrf_token(client, "/login")
    data = {"email": email, "password": password, "csrf_token": token}
    return client.post("/login", data=data, follow_redirects=False)


def test_login_and_logout(app, client):
    seed_user(app)
    # Missing CSRF token should be rejected
    bad = client.post(
        "/login",
        data={"email": "test@example.com", "password": "Password!123"},
        follow_redirects=False,
    )
    assert bad.status_code == 400

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
    csrf_token = get_csrf_token(client, "/login")

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

    headers = {"X-CSRFToken": csrf_token} if csrf_token else {}
    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": 120,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["price"] == pytest.approx(270.0)

    with app.app_context():
        assert Quote.query.count() == 1


def test_new_quote_invalid_weight_non_numeric(app, client):
    """Submitting non-numeric weight should return 400."""
    seed_user(app)
    login(client)
    csrf_token = get_csrf_token(client, "/login")

    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": "abc",
        },
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "Actual weight is required and must be a number." in data["errors"]


def test_new_quote_invalid_weight_negative(app, client):
    seed_user(app)
    login(client)
    csrf_token = get_csrf_token(client, "/login")

    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": -5,
        },
        headers={"X-CSRFToken": csrf_token},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "Actual weight must be non-negative." in data["errors"]
