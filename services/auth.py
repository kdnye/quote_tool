# auth_bp.py
# Flask blueprint implementing authentication & user management routes,
# built on top of the provided helper functions.

from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

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


@auth_bp.teardown_request
def remove_session(exception=None):
    """Ensure scoped sessions are removed after each request."""
    if hasattr(Session, "remove"):
        Session.remove()

# ---- Routes ----

@auth_bp.route('/auth', methods=['GET'])
def auth_page():
    return render_template('auth/auth.html', title='Auth')

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
    users = list_users()
    return render_template('auth/users.html', users=users, title='Users')

@auth_bp.route('/admin/users/approve', methods=['POST'])
def approve_user():
    if not _require_admin():
        return redirect(url_for('auth_bp.auth_page'))
    email = request.form.get('email','').strip().lower()
    with Session() as db:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            flash('User not found', 'warning')
            return redirect(url_for('auth_bp.users_page'))
        user.is_approved = True
        db.commit()
    flash(f'Approved {email}', 'info')
    return redirect(url_for('auth_bp.users_page'))

# ---- Usage ----
# from auth_bp import auth_bp
# app.register_blueprint(auth_bp)
# Ensure other blueprints are registered or adjust redirects accordingly.
