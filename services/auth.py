# auth_bp.py
# Flask blueprint implementing authentication & user management routes,
# built on top of the provided helper functions.

from __future__ import annotations

from flask import (
    Blueprint,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from jinja2 import DictLoader

from db import Session, User
from services.auth_utils import (
    is_valid_password,
    authenticate,
    register_user,
    list_users,
    create_reset_token,
    reset_password_with_token,
)

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
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
        <label>Email <input type="email" name="email" required></label>
        <label>Password <input type="password" name="password" required></label>
        <button class="btn" type="submit">Login</button>
      </form>
    </article>
    <article>
      <h3>Register</h3>
      <form method="post" action="{{ url_for('auth_bp.register') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
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
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
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
