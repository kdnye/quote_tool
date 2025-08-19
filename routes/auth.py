"""Authentication routes for Flask application."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user
from services import auth as auth_service
import time
from collections import defaultdict
import smtplib
from email.message import EmailMessage

auth_bp = Blueprint("auth", __name__)
_reset_attempts = defaultdict(list)
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
        # Fallback: print to console in environments without SMTP server
        print(f"EMAIL to {to}: {body}")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user, error = auth_service.authenticate(email, password)
        if user:
            login_user(user)
            session["role"] = getattr(user, "role", "user")
            session["name"] = getattr(user, "name", "")
            session["email"] = getattr(user, "email", "")
            target = "admin.dashboard" if session["role"] == "admin" else "quote.quote"
            return redirect(url_for(target))
        flash(error)
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")
        if password != confirm:
            flash("Passwords do not match")
        else:
            data = {
                "name": request.form.get("name"),
                "email": request.form.get("email"),
                "phone": request.form.get("phone"),
                "business_name": request.form.get("business_name"),
                "business_phone": request.form.get("business_phone"),
                "password": password,
            }
            error = auth_service.register_user(data)
            if not error:
                flash("Registration successful. Please log in.")
                return redirect(url_for("auth.login"))
            flash(error)
    return render_template("register.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Request a password reset token."""
    if request.method == "POST":
        email = request.form.get("email")
        ip = request.remote_addr or "anon"
        now = time.time()
        attempts = _reset_attempts[ip]
        _reset_attempts[ip] = [t for t in attempts if now - t < RESET_WINDOW]
        if len(_reset_attempts[ip]) >= RESET_LIMIT:
            flash("Too many reset requests. Try again later.")
        else:
            _reset_attempts[ip].append(now)
            token, error = auth_service.create_reset_token(email)
            if not error:
                link = url_for("auth.reset_password_token", token=token, _external=True)
                _send_email(email, "Password Reset", f"Reset your password: {link}")
                flash("Password reset link sent to your email.")
                return redirect(url_for("auth.login"))
            flash(error)
    return render_template("reset_request.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_token(token):
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm = request.form.get("confirm_password")
        if new_password != confirm:
            flash("Passwords do not match")
        else:
            error = auth_service.reset_password_with_token(token, new_password)
            if not error:
                flash("Password updated. Please log in.")
                return redirect(url_for("auth.login"))
            flash(error)
    return render_template("reset_password.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.pop("role", None)
    session.pop("name", None)
    session.pop("email", None)
    return redirect(url_for("auth.login"))
