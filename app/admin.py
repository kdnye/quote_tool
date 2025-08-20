# app/admin.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from .models import db, User

admin_bp = Blueprint("admin", __name__, template_folder="templates")

def admin_required():
    return current_user.is_authenticated and current_user.is_admin

@admin_bp.before_request
def guard_admin():
    # allow login page redirect without flicker
    from flask import abort
    if request.endpoint and request.endpoint.startswith("admin.") and not admin_required():
        abort(403)

@admin_bp.route("/")
def dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin.html", users=users)

@admin_bp.route("/toggle/<int:user_id>", methods=["POST"])
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/promote/<int:user_id>", methods=["POST"])
def promote(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash("User promoted to admin.", "success")
    return redirect(url_for("admin.dashboard"))
