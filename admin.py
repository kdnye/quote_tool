# admin_api.py  (Flask refactor of admin.py)
from flask import Blueprint, request, jsonify, session, render_template
from sqlalchemy import text
from db import Session, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def _csrf_protect():
    """Reject mutating requests missing the ``X-CSRFToken`` header.

    The JavaScript frontend is expected to include this header for
    POST/DELETE requests.  The admin API historically did not enforce
    the header which left the endpoints unprotected from cross-site
    request forgery.  Adding the check here keeps the routes lightweight
    while allowing the tests to verify that a 400 response is returned
    when the header is absent.
    """
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not request.headers.get("X-CSRFToken"):
            return (
                jsonify({"ok": False, "error": "Missing CSRF token."}),
                400,
            )

# ---- Auth guards (reuse your own if you already have them) ----
from functools import wraps

def login_required_json(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"ok": False, "error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return wrap

def admin_required_json(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"ok": False, "error": "Authentication required."}), 401
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "Admin role required."}), 403
        return f(*args, **kwargs)
    return wrap


# ---- Helpers ----
def _user_to_dict(u: User):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "business": u.business_name,
        "role": u.role,
        "approved": bool(u.is_approved),
        "created": u.created_at.strftime("%Y-%m-%d") if getattr(u, "created_at", None) else None,
    }


# ---- Endpoints ----

@bp.get("/users")
@admin_required_json
def list_users():
    """GET /admin/users  -> all users"""
    db = Session()
    try:
        users = db.query(User).all()
        return jsonify({"ok": True, "users": [_user_to_dict(u) for u in users]})
    finally:
        db.close()


@bp.get("/users/pending")
@admin_required_json
def list_pending_users():
    """GET /admin/users/pending  -> users where is_approved = 0/False"""
    db = Session()
    try:
        pending = db.query(User).filter(User.is_approved == False).all()  # noqa: E712
        return jsonify({"ok": True, "users": [_user_to_dict(u) for u in pending]})
    finally:
        db.close()


@bp.post("/users/approve")
@admin_required_json
def approve_user():
    """POST /admin/users/approve  { "id": 123 }"""
    data = request.get_json(silent=True) or {}
    uid = data.get("id")
    if not uid:
        return jsonify({"ok": False, "error": "Missing 'id'."}), 400

    db = Session()
    try:
        # ORM update (prefer over raw SQL)
        user = db.query(User).get(uid)
        if not user:
            return jsonify({"ok": False, "error": "User not found."}), 404
        user.is_approved = True
        db.commit()
        return jsonify({"ok": True, "message": f"User {uid} approved."})
    finally:
        db.close()


@bp.post("/users/role")
@admin_required_json
def change_role():
    """POST /admin/users/role  { "id": 123, "role": "user|admin" }"""
    data = request.get_json(silent=True) or {}
    uid = data.get("id")
    new_role = (data.get("role") or "").strip().lower()
    if not uid or new_role not in {"user", "admin"}:
        return jsonify({"ok": False, "error": "Provide valid 'id' and 'role' (user|admin)."}), 400

    db = Session()
    try:
        user = db.query(User).get(uid)
        if not user:
            return jsonify({"ok": False, "error": "User not found."}), 404
        user.role = new_role
        db.commit()
        return jsonify({"ok": True, "message": f"User {uid} role set to {new_role}."})
    finally:
        db.close()


@bp.delete("/users/<int:uid>")
@admin_required_json
def delete_user(uid: int):
    """DELETE /admin/users/<uid>"""
    db = Session()
    try:
        user = db.query(User).get(uid)
        if not user:
            return jsonify({"ok": False, "error": "User not found."}), 404
        db.delete(user)
        db.commit()
        return jsonify({"ok": True, "message": f"User {uid} deleted."})
    finally:
        db.close()


# ---- Optional: minimal HTML admin page (table + fetch actions) ----
@bp.get("/")
@admin_required_json
def admin_page():
    """
    Simple server-rendered view.
    Replace/extend with your frontend or an SPA as needed.
    """
    return render_template("admin.html")  # see example template below
