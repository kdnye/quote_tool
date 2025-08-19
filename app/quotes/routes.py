# app/quotes/routes.py
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
import json
import pandas as pd
from . import quotes_bp
from ..models import db, Quote
from config import Config
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from quote.utils import normalize_workbook, calculate_accessorials

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

        workbook = normalize_workbook(
            pd.read_excel(Config.WORKBOOK_PATH, sheet_name=None)
        )
        selected = []
        if isinstance(accessorials_json, dict):
            selected = list(accessorials_json.keys())
        elif isinstance(accessorials_json, list):
            selected = accessorials_json

        accessorial_total = 0.0
        acc_df = workbook.get("Accessorials")
        if acc_df is not None:
            accessorial_total = calculate_accessorials(
                acc_df, selected, quote_type, weight_actual
            )

        if quote_type.lower() == "air":
            result = calculate_air_quote(
                origin_zip, dest_zip, weight_actual, accessorial_total, workbook
            )
        else:
            result = calculate_hotshot_quote(
                origin_zip,
                dest_zip,
                weight_actual,
                accessorial_total,
                workbook.get("Hotshot Rates"),
            )
        price = result.get("quote_total", 0.0)
        warnings = []

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
