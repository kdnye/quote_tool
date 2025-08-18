from flask import Blueprint, render_template, session, redirect, url_for
from services import auth as auth_service
from services import quote as quote_service

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return wrapper


@admin_bp.route('/')
@admin_required
def dashboard():
    users = auth_service.list_users()
    quotes = quote_service.list_quotes()
    return render_template('admin.html', users=users, quotes=quotes)
