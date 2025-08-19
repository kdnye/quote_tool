import pandas as pd
from db import Session, Quote, EmailQuoteRequest
from quote.utils import normalize_workbook
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from config import Config


BOOK_PATH = Config.WORKBOOK_PATH
ADMIN_FEE = 15.00


def _load_workbook():
    wb = pd.read_excel(BOOK_PATH, sheet_name=None)
    return normalize_workbook(wb)


def _first_numeric(series: pd.Series) -> float:
    """Return the first numeric-looking value in a column."""
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


def accessorial_prices(selected_names):
    """Return [(name, price), ...] and subtotal for accessorials."""
    names = [n for n in (selected_names or []) if "guarantee" not in str(n).lower()]
    try:
        wb = _load_workbook()
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


def build_email_context(quote: Quote):
    """Assemble accessorial pricing and totals for the email request UI."""
    selected_accessorials = []
    if quote.quote_metadata:
        selected_accessorials = [
            s.strip() for s in str(quote.quote_metadata).split(",") if s and s.strip()
        ]

    acc_rows, acc_subtotal = accessorial_prices(selected_accessorials)
    guarantee_selected = any("guarantee" in s.lower() for s in selected_accessorials)

    guarantee_amount = 0.0
    if guarantee_selected and str(quote.quote_type).lower() == "air":
        pre_air_total = None
        try:
            wb = _load_workbook()
            pre = calculate_air_quote(
                origin=quote.origin,
                destination=quote.destination,
                weight=float(quote.weight or 0.0),
                accessorial_total=float(acc_subtotal or 0.0),
                workbook=wb,
            )
            pre_air_total = float(pre.get("quote_total", 0.0) or 0.0)
        except Exception:
            pre_air_total = None

        if pre_air_total is not None and pre_air_total > 0:
            guarantee_amount = round(pre_air_total * 0.25, 2)
        else:
            base_total = float(quote.total or 0.0)
            guarantee_amount = round(base_total * 0.20, 2) if base_total > 0 else 0.0

    acc_plus_guarantee_subtotal = round(float(acc_subtotal or 0.0) + float(guarantee_amount or 0.0), 2)
    base_total = float(quote.total or 0.0)
    email_total = base_total + ADMIN_FEE

    return {
        "selected_accessorials": selected_accessorials,
        "acc_rows": acc_rows,
        "acc_subtotal": acc_subtotal,
        "guarantee_selected": guarantee_selected,
        "guarantee_amount": guarantee_amount,
        "acc_plus_guarantee_subtotal": acc_plus_guarantee_subtotal,
        "base_total": base_total,
        "email_total": email_total,
        "admin_fee": ADMIN_FEE,
    }


def create_quote(user_id, user_email, quote_type, origin, destination, weight,
                  accessorial_total=0.0):
    """Generate a quote and persist to the database."""
    workbook = _load_workbook()
    if quote_type == "Air":
        result = calculate_air_quote(origin, destination, weight, accessorial_total, workbook)
    else:
        result = calculate_hotshot_quote(origin, destination, weight, accessorial_total, workbook["Hotshot Rates"])
    quote_total = result["quote_total"]
    db = Session()
    q = Quote(
        user_id=user_id,
        user_email=user_email,
        quote_type=quote_type,
        origin=origin,
        destination=destination,
        weight=weight,
        weight_method="Actual",
        zone=str(result.get("zone", "")),
        total=quote_total,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    db.close()
    return q


def get_quote(quote_id: str):
    db = Session()
    q = db.query(Quote).filter_by(quote_id=quote_id).first()
    db.close()
    return q


def list_quotes():
    db = Session()
    quotes = db.query(Quote).all()
    db.close()
    return quotes


def create_email_request(quote_id: str, data: dict):
    db = Session()
    req = EmailQuoteRequest(
        quote_id=quote_id,
        shipper_name=data.get("shipper_name"),
        shipper_address=data.get("shipper_address"),
        shipper_contact=data.get("shipper_contact"),
        shipper_phone=data.get("shipper_phone"),
        consignee_name=data.get("consignee_name"),
        consignee_address=data.get("consignee_address"),
        consignee_contact=data.get("consignee_contact"),
        consignee_phone=data.get("consignee_phone"),
        total_weight=data.get("total_weight"),
        special_instructions=data.get("special_instructions"),
    )
    db.add(req)
    db.commit()
    db.close()
    return req
