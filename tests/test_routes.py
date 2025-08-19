import pytest
from werkzeug.security import generate_password_hash
import pandas as pd

from flask_app import create_app
from app.models import db, User, Quote
from app.quotes import routes as quote_routes


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_db(app):
    with app.app_context():
        db.session.query(Quote).delete()
        db.session.query(User).delete()
        db.session.commit()
    yield


def seed_user(app, email="test@example.com", password="Password!123"):
    with app.app_context():
        user = User(email=email, name="Test")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


def login(client, email="test@example.com", password="Password!123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
    )


def test_login_and_logout(app, client):
    seed_user(app)
    response = login(client)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is not None

    client.get("/logout")
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is None


def test_quote_requires_login(client):
    response = client.get("/quotes/new")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_quote_creation(app, client, monkeypatch):
    seed_user(app)
    login(client)

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

    monkeypatch.setattr(quote_routes, "_get_normalized_workbook", lambda: workbook)
    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    response = client.post(
        "/quotes/new",
        json={
            "quote_type": "Hotshot",
            "origin_zip": "12345",
            "dest_zip": "67890",
            "weight_actual": 120,
        },
    )

    assert response.status_code == 200

    with app.app_context():
        assert Quote.query.count() == 1
