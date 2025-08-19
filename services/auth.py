# auth_bp.py
# Flask blueprint implementing authentication & user management routes,
# built on top of the provided helper functions.

from __future__ import annotations

from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash
from jinja2 import DictLoader

from werkzeug.security import generate_password_hash

# Import your existing helpers and models
from db import Session, User, PasswordResetToken
from werkzeug.security import check_password_hash

# ---- Reuse/keep your helper functions (optional import from a helpers module) ----
import re
import secrets
from datetime import datetime, timedelta

def is_valid_password(password: str) -> bool:
    if len(password) >= 14 and re.search(r"[A-Z]", password) and re.search(r"[a-z]", password) and re.search(r"[0-9]", password) and re.search(r"[^a-zA-Z0-9]", password):
        return True
    if len(password) >= 24 and password.isalpha():
        return True
    return False


def authenticate(email: str, password: str):
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    if not user or not check_password_hash(user.password_hash, password):
        return None, "Invalid credentials"
    if not getattr(user, "is_approved", True):
        return None, "Account pending approval"
    return user, None


def register_user(data: dict) -> str | None:
    email = data.get("email")
    password = data.get("password")
    if not is_valid_password(password or ""):
        return "Password does not meet complexity requirements."
    db = Session()
    if db.query(User).filter_by(email=email).first():
        db.close()
        return "Email already registered."
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
    db = Session()
    users = db.query(User).all()
    db.close()
    return users


def create_reset_token(email: str) -> tuple[str | None, str | None]:
    """Create a one-use reset token for the user with given email."""
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    if not user:
        db.close()
        return None, "No user found with that email."
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset_token)
    db.commit()
    db.close()
    return token, None


def reset_password_with_token(token: str, new_password: str) -> str | None:
    if not is_valid_password(new_password):
        return "Password does not meet complexity requirements."
    db = Session()
    reset = db.query(PasswordResetToken).filter_by(token=token, used=False).first()
    if not reset or reset.expires_at < datetime.utcnow():
        db.close()
        return "Invalid or expired token."
    user = db.query(User).filter_by(id=reset.user_id).first()
    if not user:
        db.close()
        return "Invalid token."
    user.password_hash = generate_password_hash(new_password)
    reset.used = True
    db.commit()
    db.close()
    return None

# ---- Blueprint ----
auth_bp = Blueprint("auth_bp", __name__)

# ---- Inline templates ----
BASE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or 'Auth' }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css" />
    <style>
      body, .container { background:#a0a0a0; color:#fff; }
      .btn { background:#005B99; color:#fff; border-radius:6px; font-weight:600; }
      .btn:hover { background:#003366; }
      table th, table td { color:#fff; }
    </style>
  </head>
  <body>
    <main class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for cat, msg in messages %}
            <article class="{{ 'secondary' if cat=='info' else '' }}">{{ msg }}</article>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
"""

AUTH = """
{% extends 'base.html' %}
{% block content %}
  <h2>Authentication</h2>
  <div class="grid">
    <article>
      <h3>Login</h3>
      <form method="post" action="{{ url_for('auth_bp.login') }}">
        <label>Email <input type="email" name="email" required></label>
        <label>Password <input type="password" name="password" required></label>
        <button class="btn" type="submit">Login</button>
      </form>
    </article>
    <article>
      <h3>Register</h3>
      <form method="post" action="{{ url_for('auth_bp.register') }}">
        <label>Name <input name="name" required></label>
        <label>Email <input type="email" name="email" required></label>
        <label>Phone <input name="phone"></label>
        <label>Business Name <input name="business_name"></label>
        <label>Business Phone <input name="business_phone"></label>
        <label>Password <input type="password" name="password" required></label>
        <small>Min 14 chars w/ upper, lower, number, symbol; or 24+ letters only.</small>
        <button class="btn" type="submit">Create Account</button>
      </form>
    </article>
  </div>
{% endblock %}
"""

USERS = """
{% extends 'base.html' %}
{% block content %}
  <h2>Manage Users</h2>
  <table>
    <thead>
      <tr><th>Name</th><th>Email</th><th>Role</th><th>Approved</th><th>Actions</th></tr>
    </thead>
    <tbody>
      {% for u in users %}
        <tr>
          <td>{{ u.name }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.role }}</td>
          <td>{{ 'Yes' if u.is_approved else 'No' }}</td>
          <td>
            {% if not u.is_approved %}
              <form method="post" action="{{ url_for('auth_bp.approve_user') }}" style="display:inline;">
                <input type="hidden" name="email" value="{{ u.email }}" />
                <button class="btn" type="submit">Approve</button>
              </form>
            {% endif %}
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
"""

from flask import current_app

def _ensure_templates():
    if not isinstance(current_app.jinja_loader, DictLoader):
        current_app.jinja_loader = DictLoader({})
    current_app.jinja_loader.mapping.setdefault('base.html', BASE)
    current_app.jinja_loader.mapping.setdefault('auth.html', AUTH)
    current_app.jinja_loader.mapping.setdefault('users.html', USERS)

# ---- Routes ----

@auth_bp.route('/auth', methods=['GET'])
def auth_page():
    _ensure_templates()
    return render_template_string(AUTH, title='Auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email','').strip().lower()
    password = request.form.get('password','')
    user, err = authenticate(email, password)
    if err:
        flash(err, 'warning')
        return redirect(url_for('auth_bp.auth_page'))
    session.update({
        'user': user.id if hasattr(user, 'id') else user.email,
        'name': user.name,
        'email': user.email,
        'role': user.role or 'user',
    })
    flash('Logged in successfully', 'info')
    # Redirect admins to user list, others to quote page if present
    dest = url_for('admin_bp.quotes_html') if session.get('role') == 'admin' else url_for('quote_bp.quote')
    return redirect(dest)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = {
        'name': request.form.get('name','').strip(),
        'email': request.form.get('email','').strip().lower(),
        'phone': request.form.get('phone','').strip(),
        'business_name': request.form.get('business_name','').strip(),
        'business_phone': request.form.get('business_phone','').strip(),
        'password': request.form.get('password',''),
        'role': 'user',
    }
    err = register_user(data)
    if err:
        flash(err, 'warning')
        return redirect(url_for('auth_bp.auth_page'))
    flash('Registered. An admin will review your account shortly.', 'info')
    return redirect(url_for('auth_bp.auth_page'))

@auth_bp.route('/logout')
def logout():
    for k in ('user','name','email','role'):
        session.pop(k, None)
    flash('Logged out', 'info')
    return redirect(url_for('auth_bp.auth_page'))

# --- Admin-only user list & approval ---

def _require_admin():
    if session.get('role') != 'admin':
        flash('Admin login required.', 'warning')
        return False
    return True

@auth_bp.route('/admin/users')
def users_page():
    if not _require_admin():
        return redirect(url_for('auth_bp.auth_page'))
    _ensure_templates()
    users = list_users()
    return render_template_string(USERS, users=users, title='Users')

@auth_bp.route('/admin/users/approve', methods=['POST'])
def approve_user():
    if not _require_admin():
        return redirect(url_for('auth_bp.auth_page'))
    email = request.form.get('email','').strip().lower()
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    if not user:
        db.close()
        flash('User not found', 'warning')
        return redirect(url_for('auth_bp.users_page'))
    user.is_approved = True
    db.commit()
    db.close()
    flash(f'Approved {email}', 'info')
    return redirect(url_for('auth_bp.users_page'))

# ---- Usage ----
# from auth_bp import auth_bp
# app.register_blueprint(auth_bp)
# Ensure other blueprints are registered or adjust redirects accordingly.
