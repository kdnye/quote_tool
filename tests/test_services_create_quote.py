import pandas as pd
import pytest
from werkzeug.security import generate_password_hash

from services import quote as quote_service
from db import Base, engine, Session, User, Quote

# Create tables once for the test database
Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clear_db():
    """Ensure a clean database for each test."""
    with Session() as session:
        session.query(Quote).delete()
        session.query(User).delete()
        session.commit()
    yield


@pytest.fixture
def user():
    with Session() as session:
        u = User(
            name="Test User",
            email="user@example.com",
            password_hash=generate_password_hash("Password!123"),
            is_approved=True,
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        yield u


def test_create_quote_hotshot(monkeypatch, user):
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

    monkeypatch.setattr(quote_service, "_load_workbook", lambda path=None: workbook)
    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    q = quote_service.create_quote(
        user.id,
        user.email,
        "Hotshot",
        "12345",
        "67890",
        120,
        accessorial_total=10,
    )

    assert q.total == pytest.approx(280.0)
    assert q.zone == "X"


def test_create_quote_air(monkeypatch, user):
    workbook = {
        "ZIP CODE ZONES": pd.DataFrame(
            {
                "ZIPCODE": ["12345", "67890"],
                "DEST ZONE": [1, 2],
                "BEYOND": ["NO", "B1"],
            }
        ),
        "COST ZONE TABLE": pd.DataFrame(
            {
                "CONCATENATE": ["12"],
                "COST ZONE": ["C1"],
            }
        ),
        "Air Cost Zone": pd.DataFrame(
            {
                "ZONE": ["C1"],
                "MIN": [100],
                "PER LB": ["$1.00"],
                "WEIGHT BREAK": [50],
            }
        ),
        "Beyond Price": pd.DataFrame(
            {
                "ZONE": ["B1"],
                "RATE": ["$20"],
            }
        ),
    }

    monkeypatch.setattr(quote_service, "_load_workbook", lambda path=None: workbook)

    q = quote_service.create_quote(
        user.id,
        user.email,
        "Air",
        "12345",
        "67890",
        60,
        accessorial_total=10,
    )

    assert q.total == pytest.approx(140.0)
    assert q.zone == "12"
