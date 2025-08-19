"""Authentication and user management services."""

from werkzeug.security import generate_password_hash, check_password_hash
from db import Session, User


def is_valid_password(password: str) -> bool:
    """Validate password complexity similar to Streamlit version."""
    import re
    if len(password) >= 14 and re.search(r'[A-Z]', password) and re.search(r'[a-z]', password) and re.search(r'[0-9]', password) and re.search(r'[^a-zA-Z0-9]', password):
        return True
    if len(password) >= 24 and password.isalpha():
        return True
    return False


def authenticate(email: str, password: str):
    """Return user if credentials are valid and account approved."""
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    if user and check_password_hash(user.password_hash, password) and getattr(user, 'is_approved', True):
        return user
    return None


def register_user(data: dict) -> str | None:
    """Create a new user. Returns error message or None on success."""
    email = data.get('email')
    password = data.get('password')
    if not is_valid_password(password):
        return 'Password does not meet complexity requirements.'
    db = Session()
    if db.query(User).filter_by(email=email).first():
        db.close()
        return 'Email already registered.'
    new_user = User(
        name=data.get('name', ''),
        email=email,
        phone=data.get('phone', ''),
        business_name=data.get('business_name', ''),
        business_phone=data.get('business_phone', ''),
        password_hash=generate_password_hash(password),
        is_approved=True,
    )
    db.add(new_user)
    db.commit()
    db.close()
    return None


def list_users():
    """Return all users for admin view."""
    db = Session()
    users = db.query(User).all()
    db.close()
    return users


def approve_user(user_id: int) -> bool:
    """Mark a user account as approved.

    Returns True if the user was found and updated, False otherwise.
    """
    db = Session()
    user = db.get(User, user_id)
    if not user:
        db.close()
        return False
    user.is_approved = True
    db.commit()
    db.close()
    return True


def delete_user(user_id: int) -> bool:
    """Remove a user account from the database.

    Returns True if the user existed and was deleted, False otherwise.
    """
    db = Session()
    user = db.get(User, user_id)
    if not user:
        db.close()
        return False
    db.delete(user)
    db.commit()
    db.close()
    return True
