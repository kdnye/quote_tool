"""Simple Flask app providing authentication routes."""

from flask import Flask, render_template_string, redirect, url_for, request
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import Session, User
import re


def is_valid_password(password: str) -> bool:
    """Validate password complexity.

    Accepts passwords >=14 chars with upper/lower/number/symbol or
    passphrases >=24 letters only.
    """

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


app = Flask(__name__)
import os

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "a-more-secure-development-key")

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id: str):
    db = Session()
    user = db.get(User, int(user_id))
    db.close()
    return user


LOGIN_TEMPLATE = """
<h2>Login</h2>
<form method="post">
  <input type="email" name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <input type="submit" value="Login">
  {% if error %}<p style='color:red;'>{{ error }}</p>{% endif %}
</form>
<a href="{{ url_for('register') }}">Register</a> |
<a href="{{ url_for('reset_password') }}">Reset Password</a>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        db = Session()
        user = db.query(User).filter_by(email=email).first()
        db.close()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        error = "Invalid credentials"
    return render_template_string(LOGIN_TEMPLATE, error=error)


REGISTER_TEMPLATE = """
<h2>Register</h2>
<form method="post">
  <input type="text" name="name" placeholder="Full Name" required><br>
  <input type="email" name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <input type="password" name="confirm" placeholder="Confirm Password" required><br>
  <input type="submit" value="Register">
  {% if error %}<p style='color:red;'>{{ error }}</p>{% endif %}
</form>
"""


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            error = "Passwords do not match"
        elif not is_valid_password(password):
            error = "Password does not meet requirements"
        else:
            db = Session()
            if db.query(User).filter_by(email=email).first():
                error = "Email already registered"
            else:
                user = User(
                    name=name,
                    email=email,
                    password_hash=generate_password_hash(password),
                    is_approved=True,
                )
                db.add(user)
                db.commit()
                db.close()
                return redirect(url_for("login"))
            db.close()
    return render_template_string(REGISTER_TEMPLATE, error=error)


RESET_TEMPLATE = """
<h2>Reset Password</h2>
<form method="post">
  <input type="email" name="email" placeholder="Email" required><br>
  <input type="password" name="password" placeholder="New Password" required><br>
  <input type="password" name="confirm" placeholder="Confirm Password" required><br>
  <input type="submit" value="Reset">
  {% if message %}<p>{{ message }}</p>{% endif %}
</form>
"""


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            message = "Passwords do not match"
        elif not is_valid_password(password):
            message = "Password does not meet requirements"
        else:
            db = Session()
            user = db.query(User).filter_by(email=email).first()
            if user:
                user.password_hash = generate_password_hash(password)
                db.commit()
                message = "Password updated"
            else:
                message = "User not found"
            db.close()
    return render_template_string(RESET_TEMPLATE, message=message)


@app.route("/dashboard")
@login_required
def dashboard():
    return f"Hello, {current_user.name}!"


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run()

