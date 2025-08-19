"""Authentication and user-management helpers."""

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
    """Validate credentials and return (user, error)."""
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    if not user or not check_password_hash(user.password_hash, password):
        return None, "Invalid credentials"
    if not getattr(user, "is_approved", True):
        return None, "Account pending approval"
    return user, None


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
        name=data.get("name", ""),
        email=email,
        phone=data.get("phone", ""),
        business_name=data.get("business_name", ""),
        business_phone=data.get("business_phone", ""),
        password_hash=generate_password_hash(password),
        role=data.get("role", "user"),
        is_approved=False,
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


def reset_password(email: str, new_password: str) -> str | None:
    """Update a user's password. Returns error message or None."""
    if not is_valid_password(new_password):
        return "Password does not meet complexity requirements."
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    if not user:
        db.close()
        return "No user found with that email."
    user.password_hash = generate_password_hash(new_password)
    db.commit()
    db.close()
    return None
