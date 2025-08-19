import pandas as pd
from db import Session, Quote, EmailQuoteRequest
from quote.utils import normalize_workbook
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote

BOOK_PATH = "HotShot Quote.xlsx"
BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"


def _first_numeric_in_column(series: pd.Series) -> float:
    """Return the first numeric value in a column; handle $, commas, and %."""
    for val in series.tolist():
        s = str(val).strip()
        if not s:
            continue
        if "multiply" in s.lower():
            # Skip instructional text like "multiply total by 1.25"
            continue
        s = s.replace("$", "").replace(",", "")
        if s.endswith("%"):
            # Percentage-based accessorials handled separately (e.g., Guarantee)
            continue
        try:
            return float(s)
        except Exception:
            continue
    return 0.0


def _headers_as_accessorials(df: pd.DataFrame) -> list[str]:
    """Use table headers as accessorial labels; skip blank/unnamed columns."""
    headers = []
    for c in df.columns:
        label = str(c).strip()
        if not label or label.lower().startswith("unnamed"):
            continue
        headers.append(label)
    return headers


def get_accessorial_options(quote_type: str) -> list[str]:
    """Return list of accessorial names from workbook headers."""
    wb = _load_workbook()
    df = wb.get("Accessorials")
    if df is None:
        return []
    options = _headers_as_accessorials(df)
    if quote_type == "Hotshot":
        options = [a for a in options if "guarantee" not in a.lower()]
    return options


def _load_workbook():
    wb = pd.read_excel(BOOK_PATH, sheet_name=None)
    return normalize_workbook(wb)


def create_quote(
    user_id,
    user_email,
    quote_type,
    origin,
    destination,
    weight,
    accessorial_total=0.0,
    pieces=1,
    length=0.0,
    width=0.0,
    height=0.0,
    accessorials=None,
):
    """Generate a quote and persist to the database."""
    workbook = _load_workbook()

    actual_weight = weight
    dim_weight = 0.0
    if all(v > 0 for v in [length, width, height]):
        dim_weight = (length * width * height / 166) * pieces
    billable_weight = max(actual_weight, dim_weight)
    weight_method = "Dimensional" if billable_weight == dim_weight and dim_weight > 0 else "Actual"

    subtotal = accessorial_total
    guarantee_selected = False
    if accessorials:
        df = workbook.get("Accessorials")
        for acc in accessorials:
            if "guarantee" in acc.lower():
                guarantee_selected = True
                continue
            if df is not None and acc in df.columns:
                subtotal += _first_numeric_in_column(df[acc])

    if quote_type == "Air":
        result = calculate_air_quote(origin, destination, billable_weight, subtotal, workbook)
    else:
        try:
            result = calculate_hotshot_quote(
                origin, destination, billable_weight, subtotal, workbook["Hotshot Rates"]
            )
        except ValueError as e:
            raise ValueError(f"Hotshot quote calculation failed: {e}")

    quote_total = result["quote_total"]
    if quote_type == "Air" and guarantee_selected:
        quote_total *= 1.25

    db = Session()
    q = Quote(
        user_id=user_id,
        user_email=user_email,
        quote_type=quote_type,
        origin=origin,
        destination=destination,
        weight=billable_weight,
        weight_method=weight_method,
        actual_weight=actual_weight,
        dim_weight=dim_weight,
        pieces=pieces,
        length=length,
        width=width,
        height=height,
        zone=str(result.get("zone", "")),
        total=quote_total,
        quote_metadata=", ".join(accessorials or []),
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
