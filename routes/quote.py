from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services import quote as quote_service

quote_bp = Blueprint("quote", __name__)


@quote_bp.route("/")
def index():
    return redirect(url_for("quote.quote"))


@quote_bp.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    quote_obj = None
    if request.method == "POST":
        quote_type = request.form.get("quote_type") or "Hotshot"
        origin = request.form.get("origin")
        destination = request.form.get("destination")
        weight = float(request.form.get("weight", 0))
        quote_obj = quote_service.create_quote(
            current_user.id,
            current_user.email,
            quote_type,
            origin,
            destination,
            weight,
        )
        flash("Quote generated")
    return render_template("quote.html", quote=quote_obj)


@quote_bp.route("/email-request/<quote_id>", methods=["GET", "POST"])
@login_required
def email_request(quote_id):
    quote = quote_service.get_quote(quote_id)
    if not quote:
        flash("Quote not found")
        return redirect(url_for("quote.quote"))
    if request.method == "POST":
        quote_service.create_email_request(quote_id, request.form)
        flash("Request submitted")
        return redirect(url_for("quote.quote"))
    context = quote_service.build_email_context(quote)
    return render_template("email_request.html", quote=quote, **context)
