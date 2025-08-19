"""Authentication routes for Flask application."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user
from services import auth as auth_service

auth_bp = Blueprint("auth", __name__)


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
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        confirm = request.form.get("confirm_password")
        if new_password != confirm:
            flash("Passwords do not match")
        else:
            error = auth_service.reset_password(email, new_password)
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
