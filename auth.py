# auth.py (Flask version)
from flask import Blueprint, request, jsonify, session, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import re
import secrets
from datetime import datetime, timedelta
import time
from collections import defaultdict
import smtplib
from email.message import EmailMessage

from db import Session, User, PasswordResetToken  # assumes your existing Session factory and User model

bp = Blueprint("auth", __name__, url_prefix="/auth")
reset_attempts = defaultdict(list)
RESET_LIMIT = 5
RESET_WINDOW = 3600


def _send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@example.com")
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP("localhost") as smtp:
            smtp.send_message(msg)
    except Exception:
        print(f"EMAIL to {to}: {body}")

# -----------------------
# Helpers
# -----------------------
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def is_valid_password(password: str) -> bool:
    """≥14 chars with upper/lower/number/symbol OR ≥24 chars letters-only (passphrase)."""
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


def _json_required(keys):
    data = request.get_json(silent=True) or {}
    missing = [
        k
        for k in keys
        if k not in data or (isinstance(data[k], str) and not data[k].strip())
    ]
    return data, missing


# -----------------------
# Routes
# -----------------------


@bp.post("/login")
def login():
    """POST /auth/login  -> {email, password}"""
    data, missing = _json_required(["email", "password"])
    if missing:
        return (
            jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}),
            400,
        )

    email = data["email"].strip().lower()
    password = data["password"]

    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Invalid email format."}), 400

    with Session() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user or not check_password_hash(
            getattr(user, "password_hash", ""), password
        ):
            return jsonify({"ok": False, "error": "Invalid credentials."}), 401

        if not getattr(user, "is_approved", True):
            return jsonify({"ok": False, "error": "Account pending approval."}), 403

        # Minimal session (Flask signed cookie)
        session.permanent = True  # respect app.permanent_session_lifetime
        session["user_id"] = user.id
        session["name"] = user.name
        session["email"] = user.email
        session["role"] = getattr(user, "role", "user")

        # mimic your Streamlit redirect rule
        landing = "admin" if session["role"] == "admin" else "quote"
        return jsonify(
            {"ok": True, "message": f"Welcome {user.name}!", "landing": landing}
        )


@bp.post("/register")
def register():
    """POST /auth/register -> {name, email, phone, business_name, business_phone, password, confirm}"""
    req_fields = ["name", "email", "password", "confirm"]
    data, missing = _json_required(req_fields)
    if missing:
        return (
            jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}),
            400,
        )

    name = data["name"].strip()
    email = data["email"].strip().lower()
    phone = (data.get("phone") or "").strip()
    business_name = (data.get("business_name") or "").strip()
    business_phone = (data.get("business_phone") or "").strip()
    password = data["password"]
    confirm = data["confirm"]

    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Invalid email format."}), 400
    if password != confirm:
        return jsonify({"ok": False, "error": "Passwords do not match."}), 400
    if not is_valid_password(password):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Password must be ≥14 chars with upper/lower/number/symbol OR a 24+ char passphrase (letters only).",
                }
            ),
            400,
        )

    with Session() as db:
        if db.query(User).filter_by(email=email).first():
            return jsonify({"ok": False, "error": "Email already registered."}), 409

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            business_name=business_name,
            business_phone=business_phone,
            password_hash=generate_password_hash(password),
            is_approved=True,  # preserve your current behavior
        )
        db.add(new_user)
        db.commit()
        return (
            jsonify(
                {"ok": True, "message": "Registration successful. You can now log in."}
            ),
            201,
        )


@bp.post("/request-reset")
def request_reset():
    """POST /auth/request-reset -> {email}"""
    data, missing = _json_required(["email"])
    if missing:
        return (
            jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}),
            400,
        )
    email = data["email"].strip().lower()
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Invalid email format."}), 400

    ip = request.remote_addr or "anon"
    now = time.time()
    attempts = reset_attempts[ip]
    reset_attempts[ip] = [t for t in attempts if now - t < RESET_WINDOW]
    if len(reset_attempts[ip]) >= RESET_LIMIT:
        return jsonify({"ok": False, "error": "Too many reset requests. Try again later."}), 429

    reset_attempts[ip].append(now)

    with Session() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return (
                jsonify({"ok": False, "error": "No user found with that email."}),
                404,
            )
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(hours=1)
        db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
        db.commit()

    _send_email(email, "Password Reset", f"Use this token to reset your password: {token}")
    return jsonify({"ok": True, "message": "Password reset token sent."})


@bp.post("/reset-password")
def reset_password():
    """POST /auth/reset-password -> {token, new_password, confirm_password}"""
    data, missing = _json_required(["token", "new_password", "confirm_password"])
    if missing:
        return (
            jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}),
            400,
        )

    token = data["token"]
    new_password = data["new_password"]
    confirm_password = data["confirm_password"]

    if new_password != confirm_password:
        return jsonify({"ok": False, "error": "Passwords do not match."}), 400
    if not is_valid_password(new_password):
        return (
            jsonify(
                {"ok": False, "error": "Password must meet complexity requirements."}
            ),
            400,
        )

    with Session() as db:
        reset = (
            db.query(PasswordResetToken)
            .filter_by(token=token, used=False)
            .first()
        )
        if not reset or reset.expires_at < datetime.utcnow():
            return jsonify({"ok": False, "error": "Invalid or expired token."}), 400
        user = db.query(User).filter_by(id=reset.user_id).first()
        if not user:
            return jsonify({"ok": False, "error": "Invalid token."}), 400
        user.password_hash = generate_password_hash(new_password)
        reset.used = True
        db.commit()
        return jsonify({"ok": True, "message": "Password updated successfully."})


@bp.post("/logout")
def logout():
    """POST /auth/logout"""
    session.clear()
    return jsonify({"ok": True, "message": "Logged out."})


# -----------------------
# (Optional) Guard decorator you can use on protected routes
# -----------------------
from functools import wraps


def login_required_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"ok": False, "error": "Authentication required."}), 401
        return f(*args, **kwargs)

    return wrapper
