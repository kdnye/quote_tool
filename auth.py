# auth.py (Flask version)
from flask import Blueprint, request, jsonify, session, current_app
import re
import time
from collections import defaultdict
import smtplib
from email.message import EmailMessage

from services.auth_utils import (
    is_valid_password,
    authenticate,
    register_user,
    create_reset_token,
    reset_password_with_token,
)

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

    user, err = authenticate(email, password)
    if err:
        status = 403 if "pending" in err.lower() else 401
        return jsonify({"ok": False, "error": err}), status

    # Minimal session (Flask signed cookie)
    session.permanent = True  # respect app.permanent_session_lifetime
    session["user_id"] = user.id
    session["name"] = user.name
    session["email"] = user.email
    session["role"] = getattr(user, "role", "user")

    # mimic your Streamlit redirect rule
    landing = "admin" if session["role"] == "admin" else "quote"
    return jsonify({"ok": True, "message": f"Welcome {user.name}!", "landing": landing})


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

    err = register_user(
        {
            "name": name,
            "email": email,
            "phone": phone,
            "business_name": business_name,
            "business_phone": business_phone,
            "password": password,
        },
        auto_approve=True,
    )
    if err:
        status = 409 if "already" in err.lower() else 400
        return jsonify({"ok": False, "error": err}), status

    return (
        jsonify({"ok": True, "message": "Registration successful. You can now log in."}),
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

    token, err = create_reset_token(email)
    if err:
        status = 404 if "no user" in err.lower() else 400
        return jsonify({"ok": False, "error": err}), status

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

    err = reset_password_with_token(token, new_password)
    if err:
        return jsonify({"ok": False, "error": err}), 400
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
