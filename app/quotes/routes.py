# app/quotes/routes.py
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from . import quotes_bp
from ..models import db, Quote
from . import logic_hotshot, logic_air
from .. import create_app
import json

@quotes_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_quote():
    if request.method == "POST":
        data = request.form or request.json or {}
        quote_type = data.get("quote_type", "Hotshot")
        origin_zip = data.get("origin_zip", "")
        dest_zip = data.get("dest_zip", "")
        weight_actual = float(data.get("weight_actual") or 0)
        weight_dim = float(data.get("weight_dim") or 0)
        accessorials = data.get("accessorials") or "{}"
        try:
            accessorials_json = json.loads(accessorials) if isinstance(accessorials, str) else accessorials
        except Exception:
            accessorials_json = {}

        if quote_type.lower() == "air":
            price, warnings = logic_air.calculate(
                origin_zip, dest_zip, weight_actual, weight_dim, accessorials_json
            )
        else:
            price, warnings = logic_hotshot.calculate(
                origin_zip, dest_zip, weight_actual, weight_dim, accessorials_json
            )

        q = Quote(
            quote_type=quote_type.title(),
            origin_zip=origin_zip,
            dest_zip=dest_zip,
            weight_actual=weight_actual,
            weight_dim=weight_dim,
            accessorials=json.dumps(accessorials_json),
            price=price,
            warnings="\n".join(warnings) if warnings else "",
            created_by=current_user,
        )
        db.session.add(q)
        db.session.commit()

        if request.is_json:
            return jsonify({"id": q.id, "price": q.price, "warnings": q.warnings})
        return render_template("quote_result.html", quote=q)

    return render_template("new_quote.html")
