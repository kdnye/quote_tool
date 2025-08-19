# quote/email_api.py  (Flask refactor of email_form.py)
from flask import Blueprint, request, jsonify, Response
from db import Session, EmailQuoteRequest, Quote
from config import Config
from werkzeug.exceptions import BadRequest
from io import StringIO
import urllib.parse
import pandas as pd
import csv
import re

# Optional helpers preserved from your package
try:
    from quote.utils import normalize_workbook  # read/normalize workbook sheets
except Exception:
    normalize_workbook = None

try:
    from quote.logic_air import calculate_air_quote  # recompute pre-guarantee Air total
except Exception:
    calculate_air_quote = None

bp = Blueprint("email_api", __name__, url_prefix="/email")

BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"
ADMIN_FEE = 15.00  # Email-only processing fee
EMAIL_TO = "operations@freightservices.net"

# ----------------- DB & workbook helpers -----------------
def _load_quote_from_db(quote_id: str):
    if not quote_id:
        return None
    db = Session()
    try:
        q = db.query(Quote).filter(Quote.quote_id == quote_id).first()
        if not q:
            return None
        accessorials = []
        if q.quote_metadata:
            accessorials = [s.strip() for s in str(q.quote_metadata).split(",") if s and s.strip()]
        guarantee_selected = any("guarantee" in s.lower() for s in accessorials)
        return {
            "origin": q.origin or "",
            "destination": q.destination or "",
            "weight": float(q.weight or 0.0),
            "quote_type": q.quote_type or "",
            "accessorials": accessorials,
            "guarantee_selected": guarantee_selected,
            "quote_total": float(q.total or 0.0),
        }
    finally:
        db.close()

def _first_numeric(series: pd.Series) -> float:
    """Return the first numeric-looking value; handle $, commas, %, skip 'multiply' notes."""
    for val in series.tolist():
        s = str(val).strip()
        if not s:
            continue
        if "multiply" in s.lower():
            continue
        s = s.replace("$", "").replace(",", "")
        if s.endswith("%"):
            continue
        try:
            return float(s)
        except Exception:
            continue
    return 0.0

def _accessorial_prices(selected_names):
    """Return ([(name, price), ...], subtotal). Excludes 'guarantee' (percent-based)."""
    names = [n for n in (selected_names or []) if "guarantee" not in str(n).lower()]

    try:
        wb = pd.read_excel(Config.WORKBOOK_PATH, sheet_name=None)
        if normalize_workbook:
            wb = normalize_workbook(wb)
        df = wb["Accessorials"]
    except Exception:
        return [(name, 0.0) for name in names], 0.0

    rows, subtotal = [], 0.0
    for name in names:
        price = _first_numeric(df[name]) if name in df.columns else 0.0
        price = float(price or 0.0)
        rows.append((name, price))
        subtotal += price
    return rows, round(subtotal, 2)

# ----------------- core computation -----------------
def _compute_email_payload(quote_details: dict,
                           shipper: dict,
                           consignee: dict,
                           special_instructions: str,
                           total_weight: float):
    """Compute accessorials, guarantee, totals, email body and mailto link."""
    selected_accessorials = quote_details.get("accessorials", [])
    guarantee_selected = bool(
        quote_details.get("guarantee_selected")
        or any("guarantee" in str(s).lower() for s in selected_accessorials)
    )
    base_total = float(quote_details.get("quote_total", 0.0) or 0.0)
    email_total = base_total + ADMIN_FEE

    # Accessorial rows & subtotal from workbook
    acc_rows, acc_subtotal = _accessorial_prices(selected_accessorials)

    # Guarantee amount: prefer 25% of pre-guarantee Air total; fallback to 20% of stored total
    guarantee_amount = 0.0
    if guarantee_selected and str(quote_details.get("quote_type", "")).lower() == "air":
        pre_air_total = None
        try:
            if calculate_air_quote is not None:
                wb = pd.read_excel(Config.WORKBOOK_PATH, sheet_name=None)
                if normalize_workbook:
                    wb = normalize_workbook(wb)
                pre = calculate_air_quote(
                    origin=quote_details.get("origin", ""),
                    destination=quote_details.get("destination", ""),
                    weight=float(quote_details.get("weight", 0.0) or 0.0),
                    accessorial_total=float(acc_subtotal or 0.0),  # $-only accessorials
                    workbook=wb,
                )
                pre_air_total = float(pre.get("quote_total", 0.0) or 0.0)
        except Exception:
            pre_air_total = None

        if pre_air_total and pre_air_total > 0:
            guarantee_amount = round(pre_air_total * 0.25, 2)
        else:
            guarantee_amount = round(base_total * 0.20, 2) if base_total > 0 else 0.0

    acc_plus_guarantee_subtotal = round(float(acc_subtotal or 0.0) + float(guarantee_amount or 0.0), 2)

    def _fmt_money(x: float) -> str:
        return f"${x:,.2f}"

    NAME_COL = 28
    AMT_COL = 12
    SEP = "-" * 12

    def _line(name: str, amount: float) -> str:
        return f"{name:<{NAME_COL}}{_fmt_money(amount):>{AMT_COL}}"

    # Build email body
    lines = []
    lines.append("I'd like to go ahead and book the following quote")
    lines.append("")
    lines.append(f"Origin: {quote_details.get('origin','')}")
    lines.append(f"Destination: {quote_details.get('destination','')}")
    lines.append(f"Weight: {total_weight}")
    lines.append("")
    lines.append("Accessorials")
    lines.append(SEP)
    for name, price in acc_rows:
        lines.append(_line(name, price))
    lines.append(SEP)
    lines.append(_line("Subtotal:", acc_subtotal))
    lines.append(SEP)
    if guarantee_selected:
        lines.append(f"{'Guarantee (25%)':<{NAME_COL}}{_fmt_money(guarantee_amount):>{AMT_COL}}")
        lines.append(SEP)
        lines.append(_line("Accessorials + Guarantee Subtotal:", acc_plus_guarantee_subtotal))
        lines.append(SEP)
    lines.append("")
    lines.append(f"Quote Total: {_fmt_money(email_total)} (includes {_fmt_money(ADMIN_FEE)} email admin fee)")
    lines.append("")
    lines.append("Shipper info:")
    lines.append(f"Name: {shipper.get('name','')}")
    lines.append(f"Address: {shipper.get('address','')}")
    lines.append(f"Contact: {shipper.get('contact','')}")
    lines.append(f"Phone: {shipper.get('phone','')}")
    lines.append("")
    lines.append("Consignee info:")
    lines.append(f"Name: {consignee.get('name','')}")
    lines.append(f"Address: {consignee.get('address','')}")
    lines.append(f"Contact: {consignee.get('contact','')}")
    lines.append(f"Phone: {consignee.get('phone','')}")
    lines.append("")
    lines.append(f"Accessorials Selected: {', '.join(selected_accessorials) if selected_accessorials else 'None'}")
    lines.append(f"Quote ID: {quote_details.get('quote_id','') or ''}")

    email_body = "\n".join(lines) + "\n"

    subject_text = f"Quote Request for ID: {quote_details.get('quote_id') or '(no id)'}"
    subject_enc = urllib.parse.quote(subject_text, safe="")
    body_enc = urllib.parse.quote(email_body.replace("\n", "\r\n"), safe="")
    mailto_link = f"mailto:{EMAIL_TO}?subject={subject_enc}&body={body_enc}"

    return {
        "base_total": round(base_total, 2),
        "admin_fee": round(ADMIN_FEE, 2),
        "email_total": round(email_total, 2),
        "acc_subtotal": round(acc_subtotal, 2),
        "guarantee_amount": round(guarantee_amount, 2),
        "acc_rows": [{"name": n, "price": float(p)} for n, p in acc_rows],
        "email": {
            "to": EMAIL_TO,
            "subject": subject_text,
            "body": email_body,
            "mailto": mailto_link,
        },
    }

def _build_csv(quote_id, shipper, consignee, total_weight, special_instructions, base_total, email_total):
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow([
        "Quote ID","Shipper Name","Shipper Address","Shipper Contact","Shipper Phone",
        "Consignee Name","Consignee Address","Consignee Contact","Consignee Phone",
        "Total Weight","Special Instructions","Base Total","Email Total (incl. $15)"
    ])
    writer.writerow([
        quote_id or "", shipper.get("name",""), shipper.get("address",""), shipper.get("contact",""), shipper.get("phone",""),
        consignee.get("name",""), consignee.get("address",""), consignee.get("contact",""), consignee.get("phone",""),
        total_weight, special_instructions or "", f"{base_total:.2f}", f"{email_total:.2f}"
    ])
    return csv_data.getvalue()

# ----------------- Endpoints -----------------
@bp.post("/quote")
def create_email_quote():
    """
    POST /email/quote
    Body (JSON):
    {
      "quote_id": "...",                      # preferred (will load from DB)
      # Optional overrides if quote_id isn't present or you want to override DB
      "quote_details": {
        "origin": "", "destination": "", "weight": 0, "quote_type": "Air|LTL|...", 
        "accessorials": ["Liftgate", "Guarantee"], "quote_total": 0
      },

      "shipper": { "name":"", "address":"", "contact":"", "phone":"" },
      "consignee": { "name":"", "address":"", "contact":"", "phone":"" },
      "special_instructions": "text",
      "total_weight": 0,
      "preview_only": false                   # if true, compute but don't save
    }
    """
    data = request.get_json(silent=True) or {}
    shipper = data.get("shipper") or {}
    consignee = data.get("consignee") or {}
    special_instructions = data.get("special_instructions") or ""
    total_weight = float(data.get("total_weight") or 0.0)
    preview_only = bool(data.get("preview_only") or False)

    # Resolve quote_details
    quote_id = (data.get("quote_id") or "").strip()
    quote_details = data.get("quote_details") or _load_quote_from_db(quote_id)
    if not quote_details:
        raise BadRequest("No quote details found. Provide a valid quote_id or quote_details.")
    if quote_id and not quote_details.get("quote_id"):
        quote_details["quote_id"] = quote_id  # carry into email/csv

    # Compute payload
    payload = _compute_email_payload(
        quote_details=quote_details,
        shipper=shipper,
        consignee=consignee,
        special_instructions=special_instructions,
        total_weight=total_weight if total_weight else float(quote_details.get("weight", 0.0)),
    )

    # Persist EmailQuoteRequest unless preview_only
    if not preview_only:
        db = Session()
        try:
            new_request = EmailQuoteRequest(
                quote_id=quote_id or "",
                shipper_name=shipper.get("name",""),
                shipper_address=shipper.get("address",""),
                shipper_contact=shipper.get("contact",""),
                shipper_phone=shipper.get("phone",""),
                consignee_name=consignee.get("name",""),
                consignee_address=consignee.get("address",""),
                consignee_contact=consignee.get("contact",""),
                consignee_phone=consignee.get("phone",""),
                total_weight=float(total_weight or quote_details.get("weight") or 0.0),
                special_instructions=special_instructions,
            )
            db.add(new_request)
            db.commit()
        finally:
            db.close()

    # CSV content (frontend can trigger a download)
    csv_text = _build_csv(
        quote_id=quote_id,
        shipper=shipper,
        consignee=consignee,
        total_weight=float(total_weight or quote_details.get("weight") or 0.0),
        special_instructions=special_instructions,
        base_total=payload["base_total"],
        email_total=payload["email_total"],
    )

    return jsonify({
        "ok": True,
        "message": "Quote request computed and saved." if not preview_only else "Preview computed.",
        "book_url": BOOK_URL,
        "totals": {
            "base_total": payload["base_total"],
            "admin_fee": payload["admin_fee"],
            "email_total": payload["email_total"],
            "accessoria
