import pytest
from flask import Flask
import admin
import db
from db import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def app(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    # Patch Session used by admin blueprint and db module
    monkeypatch.setattr(db, 'Session', TestingSession)
    monkeypatch.setattr(admin, 'Session', TestingSession)
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test'
    app.register_blueprint(admin.bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()


def seed_users():
    session = admin.Session()
    target = User(name='Target', email='target@example.com', password_hash='x', role='user', is_approved=False)
    admin_user = User(name='Admin', email='admin@example.com', password_hash='x', role='admin', is_approved=True)
    session.add_all([target, admin_user])
    session.commit()
    return target.id, admin_user.id


def login(client, admin_id):
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'


def test_approve_user_requires_csrf(client):
    target_id, admin_id = seed_users()
    login(client, admin_id)
    resp = client.post('/admin/users/approve', json={'id': target_id})
    assert resp.status_code == 400


def test_change_role_requires_csrf(client):
    target_id, admin_id = seed_users()
    login(client, admin_id)
    resp = client.post('/admin/users/role', json={'id': target_id, 'role': 'admin'})
    assert resp.status_code == 400


def test_delete_user_requires_csrf(client):
    target_id, admin_id = seed_users()
    login(client, admin_id)
    resp = client.delete(f'/admin/users/{target_id}')
    assert resp.status_code == 400
