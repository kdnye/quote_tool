from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from services import auth as auth_service
from services import quote as quote_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(func):
    from functools import wraps

    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if getattr(current_user, "role", "user") != "admin":
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return wrapper


@admin_bp.route("/")
@admin_required
def dashboard():
    users = auth_service.list_users()
    quotes = quote_service.list_quotes()
    return render_template("admin.html", users=users, quotes=quotes)
