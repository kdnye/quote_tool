from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from services import quote as quote_service


BOOK_URL = quote_service.BOOK_URL

quote_bp = Blueprint("quote", __name__)


@quote_bp.route("/")
def index():
    return redirect(url_for("quote.quote"))


@quote_bp.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    quote_obj = None
    quote_type = request.form.get("quote_type") if request.method == "POST" else "Hotshot"
    accessorial_options = quote_service.get_accessorial_options(quote_type)

    if request.method == "POST":
        origin = request.form.get("origin")
        destination = request.form.get("destination")
        pieces = int(request.form.get("pieces", 1) or 1)
        length = float(request.form.get("length", 0) or 0)
        width = float(request.form.get("width", 0) or 0)
        height = float(request.form.get("height", 0) or 0)
        weight = float(request.form.get("weight", 0) or 0)
        selected_accessorials = request.form.getlist("accessorials")

        quote_obj = quote_service.create_quote(
            current_user.id,
            current_user.email,
            quote_type,
            origin,
            destination,
            weight,
            pieces=pieces,
            length=length,
            width=width,
            height=height,
            accessorials=selected_accessorials,
        )
        flash("Quote generated")

    return render_template(
        "quote.html",
        quote=quote_obj,
        accessorial_options=accessorial_options,
        book_url=BOOK_URL,
    )


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
    return render_template("email_request.html", quote=quote)
