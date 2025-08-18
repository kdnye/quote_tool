import pytest
from werkzeug.security import generate_password_hash
import pandas as pd

from flask_app import create_app
from db import Base, engine, Session, User, Quote
from services import quote as quote_service

Base.metadata.create_all(engine)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_db():
    with Session() as session:
        session.query(Quote).delete()
        session.query(User).delete()
        session.commit()
    yield


def seed_user(email="test@example.com", password="Password!123"):
    with Session() as session:
        user = User(
            name="Test", email=email, password_hash=generate_password_hash(password), is_approved=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def login(client, email="test@example.com", password="Password!123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_login_and_logout(client):
    seed_user()
    response = login(client)
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is not None

    client.get("/logout", follow_redirects=True)
    with client.session_transaction() as sess:
        assert sess.get("_user_id") is None


def test_quote_requires_login(client):
    response = client.get("/quote")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_quote_creation(client, monkeypatch):
    seed_user()
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

    monkeypatch.setattr(quote_service, "_load_workbook", lambda: workbook)
    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    response = client.post(
        "/quote",
        data={
            "quote_type": "Hotshot",
            "origin": "12345",
            "destination": "67890",
            "weight": "120",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Quote generated" in response.data

    with Session() as session:
        assert session.query(Quote).count() == 1
