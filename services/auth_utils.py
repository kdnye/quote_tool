import re
import secrets
from datetime import datetime, timedelta
from typing import Tuple, Optional

from werkzeug.security import generate_password_hash, check_password_hash

from db import Session, User, PasswordResetToken


def is_valid_password(password: str) -> bool:
    """Validate password complexity or passphrase length."""
    if (
        len(password) >= 14
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[^a-zA-Z0-9]", password)
    ):
        return True
    if len(password) >= 24 and password.isalpha():
        return True
    return False


def authenticate(email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """Return user if credentials are valid, otherwise an error message."""
    db = Session()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user or not check_password_hash(getattr(user, "password_hash", ""), password):
            return None, "Invalid credentials"
        if not getattr(user, "is_approved", True):
            return None, "Account pending approval"
        return user, None
    finally:
        db.close()


def register_user(data: dict, auto_approve: bool = False) -> Optional[str]:
    """Register a new user. Returns error message on failure."""
    email = data.get("email")
    password = data.get("password")
    if not is_valid_password(password or ""):
        return "Password does not meet complexity requirements."
    db = Session()
    try:
        if db.query(User).filter_by(email=email).first():
            return "Email already registered."
        new_user = User(
            name=data.get("name", ""),
            email=email,
            phone=data.get("phone", ""),
            business_name=data.get("business_name", ""),
            business_phone=data.get("business_phone", ""),
            password_hash=generate_password_hash(password),
            role=data.get("role", "user"),
            is_approved=auto_approve,
        )
        db.add(new_user)
        db.commit()
        return None
    finally:
        db.close()


def list_users():
    db = Session()
    try:
        return db.query(User).all()
    finally:
        db.close()


def create_reset_token(email: str) -> Tuple[Optional[str], Optional[str]]:
    """Create a one-use reset token for the user with given email."""
    db = Session()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return None, "No user found with that email."
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        db.add(reset_token)
        db.commit()
        return token, None
    finally:
        db.close()


def reset_password_with_token(token: str, new_password: str) -> Optional[str]:
    """Reset user password using a valid token."""
    if not is_valid_password(new_password):
        return "Password does not meet complexity requirements."
    db = Session()
    try:
        reset = db.query(PasswordResetToken).filter_by(token=token, used=False).first()
        if not reset or reset.expires_at < datetime.utcnow():
            return "Invalid or expired token."
        user = db.query(User).filter_by(id=reset.user_id).first()
        if not user:
            return "Invalid token."
        user.password_hash = generate_password_hash(new_password)
        reset.used = True
        db.commit()
        return None
    finally:
        db.close()
