# app/quotes/routes.py
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
import json
import os
import pandas as pd
from . import quotes_bp
from ..models import db, Quote
from config import Config
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from quote.utils import normalize_workbook, calculate_accessorials


# Cache for the normalized workbook to avoid reloading on every request
_workbook_cache = None
_workbook_mtime = None


def _get_normalized_workbook():
    """Return a cached normalized workbook, reloading if the file changed."""
    global _workbook_cache, _workbook_mtime
    workbook_path = Config.WORKBOOK_PATH
    try:
        mtime = os.path.getmtime(workbook_path)
    except OSError:
        mtime = None

    if _workbook_cache is None or _workbook_mtime != mtime:
        _workbook_cache = normalize_workbook(
            pd.read_excel(workbook_path, sheet_name=None)
        )
        _workbook_mtime = mtime

    return _workbook_cache

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

        workbook = _get_normalized_workbook()
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

        warnings = []

        if quote_type.lower() == "air":
            result = calculate_air_quote(
                origin_zip, dest_zip, weight_actual, accessorial_total, workbook
            )
        else:
            try:
                result = calculate_hotshot_quote(
                    origin_zip,
                    dest_zip,
                    weight_actual,
                    accessorial_total,
                    workbook.get("Hotshot Rates"),
                )
            except ValueError as e:
                warnings.append(str(e))
                result = {"quote_total": 0.0}

        price = result.get("quote_total", 0.0)

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
