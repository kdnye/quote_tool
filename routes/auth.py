from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from services import auth as auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = auth_service.authenticate(email, password)
        if user:
            login_user(user)
            return redirect(url_for("quote.quote"))
        flash("Invalid credentials")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "business_name": request.form.get("business_name"),
            "business_phone": request.form.get("business_phone"),
            "password": request.form.get("password"),
        }
        error = auth_service.register_user(data)
        if not error:
            flash("Registration successful. Please log in.")
            return redirect(url_for("auth.login"))
        flash(error)
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
