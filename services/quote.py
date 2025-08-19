import pandas as pd
from db import Session, Quote, EmailQuoteRequest
from quote.utils import normalize_workbook
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote

BOOK_PATH = "HotShot Quote.xlsx"


def _load_workbook():
    wb = pd.read_excel(BOOK_PATH, sheet_name=None)
    return normalize_workbook(wb)


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
    """Return all quotes ordered from newest to oldest."""
    db = Session()
    quotes = db.query(Quote).order_by(Quote.created_at.desc()).all()
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
