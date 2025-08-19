import pytest
from flask_app import create_app
from app.models import db, User

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def seed_user(email='user@example.com', password='Password!123', is_admin=False):
    user = User(email=email, name='Test', is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def login(client, email='user@example.com', password='Password!123'):
    return client.post('/login', data={'email': email, 'password': password})

@pytest.mark.parametrize('endpoint', ['toggle', 'promote'])
def test_admin_requires_login_redirect(client, app, endpoint):
    with app.app_context():
        target = seed_user(email='target@example.com')
        target_id = target.id
    response = client.post(f'/admin/{endpoint}/{target_id}')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

@pytest.mark.parametrize('endpoint', ['toggle', 'promote'])
def test_admin_requires_admin_403(client, app, endpoint):
    with app.app_context():
        target = seed_user(email='target@example.com')
        target_id = target.id
        seed_user(email='regular@example.com')
    login(client, email='regular@example.com')
    response = client.post(f'/admin/{endpoint}/{target_id}')
    assert response.status_code == 403
