# Directory: quote/
# File: email_form.py
import streamlit as st
from db import Session, EmailQuoteRequest, Quote
import urllib.parse
import csv
from io import StringIO
import pandas as pd

# If your package is "quote", utils lives there
try:
    from quote.utils import normalize_workbook  # to read accessorial prices from the workbook
except Exception:
    normalize_workbook = None

BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"
ADMIN_FEE = 15.00  # Email-only processing fee


# ---------- helpers ----------
def _load_quote_from_db(quote_id: str):
    """Fetch a quote by UUID and map to the dict shape this UI expects."""
    if not quote_id:
        return None
    db = Session()
    q = db.query(Quote).filter(Quote.quote_id == quote_id).first()
    db.close()
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
        "quote_total": float(q.total or 0.0),  # base total from DB (no $15 fee)
    }


def _first_numeric_in_column(series: pd.Series) -> float:
    """Return the first numeric-looking value in a column; handle $, commas, %, and skip instructions."""
    for val in series.tolist():
        s = str(val).strip()
        if not s:
            continue
        if "multiply" in s.lower():
            continue
        s = s.replace("$", "").replace(",", "")
        if s.endswith("%"):  # percentage-type (e.g., Guarantee) not part of fixed-$ subtotal
            continue
        try:
            return float(s)
        except Exception:
            continue
    return 0.0


def _accessorial_prices(selected_names):
    """
    Return ([(name, price), ...], subtotal) using the 'Accessorials' sheet headers.
    Guarantee is excluded here and handled as a separate line item.
    """
    try:
        wb = pd.read_excel("HotShot Quote.xlsx", sheet_name=None)
        if normalize_workbook:
            wb = normalize_workbook(wb)
        df = wb["Accessorials"]
    except Exception:
        # On workbook read issues, fall back to $0 rows so email still formats
        clean = [n for n in (selected_names or []) if "guarantee" not in str(n).lower()]
        return [(name, 0.0) for name in clean], 0.0

    rows = []
    subtotal = 0.0
    for name in (selected_names or []):
        if "guarantee" in str(name).lower():
            continue
        price = _first_numeric_in_column(df[name]) if name in df.columns else 0.0
        price = float(price or 0.0)
        rows.append((name, price))
        subtotal += price
    return rows, round(float(subtotal), 2)


def _hydrate_query_params():
    """Support both modern and legacy Streamlit query params APIs."""
    try:
        qp = st.query_params
        if qp:
            return dict(qp)
    except Exception:
        pass
    try:
        return st.experimental_get_query_params()
    except Exception:
        return {}


def _coalesce_session_and_db():
    """
    Assemble quote_id and quote_details from:
      1) st.session_state,
      2) URL ?quote_id=,
      3) DB lookup,
      4) reconstruction from common loose session keys (best-effort).
    Persist any recovered values back to st.session_state.
    """
    ss = st.session_state
    quote_id = ss.get("quote_id")
    quote_details = ss.get("quote_details")

    # 2) URL param
    if not quote_id:
        qp = _hydrate_query_params()
        if "quote_id" in qp:
            qv = qp["quote_id"]
            quote_id = qv[0] if isinstance(qv, list) else qv

    # 3) DB
    if not quote_details and quote_id:
        quote_details = _load_quote_from_db(quote_id)

    # 4) Reconstruct from loose session keys if needed
    if not quote_details:
        origin = ss.get("origin") or ss.get("origin_zip") or ss.get("pickup_zip") or ""
        destination = ss.get("destination") or ss.get("destination_zip") or ss.get("deliver_zip") or ""
        weight = float(ss.get("weight") or ss.get("total_weight") or 0.0)
        quote_type = ss.get("quote_type") or ss.get("mode") or ss.get("selected_mode") or ""
        accessorials = list(ss.get("accessorials") or ss.get("selected_accessorials") or [])
        base_total = float(ss.get("quote_total") or ss.get("base_total") or 0.0)
        if origin or destination or base_total > 0:
            quote_details = {
                "origin": origin,
                "destination": destination,
                "weight": weight,
                "quote_type": quote_type,
                "accessorials": accessorials,
                "guarantee_selected": any("guarantee" in str(a).lower() for a in accessorials),
                "quote_total": base_total,
            }

    # Persist back
    if quote_id and "quote_id" not in ss:
        ss.quote_id = quote_id
    if quote_details and "quote_details" not in ss:
        ss.quote_details = quote_details

    return ss.get("quote_id"), ss.get("quote_details")


# ---------- main UI ----------
def email_form_ui():
    st.subheader("Email Quote Request ($15 Admin Fee)")
    st.markdown(
        "Please fill out the form below to request a booking for this quote. "
        "The information will be sent to the FSI Operations Team."
    )

    quote_id, quote_details = _coalesce_session_and_db()
    if not quote_details:
        st.warning("No active quote found in session.")
        return

    # Compute totals/flags (base_total is the quote's stored total; email adds $15 admin fee)
    base_total = float(quote_details.get("quote_total", 0.0) or 0.0)
    email_total = base_total + ADMIN_FEE

    selected_accessorials = quote_details.get("accessorials", [])
    guarantee_selected = bool(
        quote_details.get("guarantee_selected")
        or any("guarantee" in str(s).lower() for s in selected_accessorials)
    )

    st.info(
        f"Email processing adds a ${ADMIN_FEE:.2f} admin fee. "
        f"The 'Book Quote' button does not include this fee."
    )

    # -------------------- Form --------------------
    with st.form("email_quote_form"):
        st.subheader("Shipper Information")
        shipper_name = st.text_input("Shipper Name")
        shipper_address = st.text_input("Shipper Address", value=quote_details.get("origin", ""))
        shipper_contact = st.text_input("Shipper Contact Person")
        shipper_phone = st.text_input("Shipper Phone Number")

        st.subheader("Consignee Information")
        consignee_name = st.text_input("Consignee Name")
        consignee_address = st.text_input("Consignee Address", value=quote_details.get("destination", ""))
        consignee_contact = st.text_input("Consignee Contact Person")
        consignee_phone = st.text_input("Consignee Phone Number")

        st.subheader("Shipment Details")
        total_weight = st.number_input(
            "Total Weight (lbs)",
            value=float(quote_details.get("weight", 0.0)),
            disabled=True
        )
        special_instructions = st.text_area(
            "Special Instructions",
            value=", ".join(selected_accessorials)
        )

        submitted = st.form_submit_button("Submit & Launch Email")

    if not submitted:
        return

    # -------------------- Save request --------------------
    db = Session()
    new_request = EmailQuoteRequest(
        quote_id=quote_id or "",
        shipper_name=shipper_name,
        shipper_address=shipper_address,
        shipper_contact=shipper_contact,
        shipper_phone=shipper_phone,
        consignee_name=consignee_name,
        consignee_address=consignee_address,
        consignee_contact=consignee_contact,
        consignee_phone=consignee_phone,
        total_weight=float(total_weight),
        special_instructions=special_instructions
    )
    db.add(new_request)
    db.commit()
    db.close()
    st.success("Quote request saved!")

    # -------------------- CSV export --------------------
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow([
        "Quote ID","Shipper Name","Shipper Address","Shipper Contact","Shipper Phone",
        "Consignee Name","Consignee Address","Consignee Contact","Consignee Phone",
        "Total Weight","Special Instructions","Base Total","Email Total (incl. $15)"
    ])
    writer.writerow([
        quote_id or "", shipper_name, shipper_address, shipper_contact, shipper_phone,
        consignee_name, consignee_address, consignee_contact, consignee_phone,
        total_weight, special_instructions, f"{base_total:.2f}", f"{email_total:.2f}"
    ])

    # -------------------- Email body (established fixed-width formatting) --------------------
    def _fmt_money(x: float) -> str:
        return f"${x:,.2f}"

    NAME_COL = 28  # label width
    AMT_COL = 12   # right-justified money width
    SEP = "-" * 12

    def _line(name: str, amount: float) -> str:
        return f"{name:<{NAME_COL}}{_fmt_money(amount):>{AMT_COL}}"

    # Accessorial rows & subtotal from workbook headers
    acc_rows, acc_subtotal = _accessorial_prices(selected_accessorials)

    # Presentational Guarantee amount:
    # If final = base * 1.25, then guarantee = final * 0.20
    guarantee_amount = 0.0
    if guarantee_selected and (quote_details.get("quote_type", "") == "Air") and base_total > 0:
        guarantee_amount = round(base_total * 0.20, 2)

    acc_plus_guarantee_subtotal = round(acc_subtotal + guarantee_amount, 2)

    lines = []
    # Header triplet
    lines.append(f"Origin: {quote_details.get('origin','')}")
    lines.append(f"Destination: {quote_details.get('destination','')}")
    lines.append(f"Weight: {total_weight}")
    lines.append("")  # blank

    # Accessorials block
    lines.append("Accessorials")
    lines.append(SEP)
    for name, price in acc_rows:
        lines.append(_line(name, price))
    lines.append(SEP)
    lines.append(_line("Subtotal:", acc_subtotal))
    lines.append(SEP)

    # Guarantee on a single aligned line
    if guarantee_selected:
        lines.append(f"{'Guarantee (25%)':<{NAME_COL}}{_fmt_money(guarantee_amount):>{AMT_COL}}")
        lines.append(SEP)
        lines.append(_line("Accessorials + Guarantee Subtotal:", acc_plus_guarantee_subtotal))
        lines.append(SEP)

    lines.append("")  # blank
    lines.append(f"Quote Total: {_fmt_money(email_total)} (includes {_fmt_money(ADMIN_FEE)} email admin fee)")
    lines.append("")  # blank

    # Footer block (restored)
    lines.append("Shipper info:")
    lines.append(f"Name: {shipper_name}")
    lines.append(f"Address: {shipper_address}")
    lines.append(f"Contact: {shipper_contact}")
    lines.append(f"Phone: {shipper_phone}")
    lines.append("")
    lines.append("Consignee info:")
    lines.append(f"Name: {consignee_name}")
    lines.append(f"Address: {consignee_address}")
    lines.append(f"Contact: {consignee_contact}")
    lines.append(f"Phone: {consignee_phone}")
    lines.append("")
    lines.append(f"Accessorials Selected: {', '.join(selected_accessorials) if selected_accessorials else 'None'}")
    lines.append(f"Quote ID: {quote_id or ''}")

    email_body = "\n".join(lines) + "\n"

    mailto_link = (
        "mailto:operations@fsi.com"
        f"?subject={urllib.parse.quote(f'Quote Request for ID: {quote_id or \"(no id)\"}')}"
        f"&body={urllib.parse.quote(email_body)}"
    )

    # Launch email client button
    st.markdown(
        f"""
        <a href="{mailto_link}" target="_blank" rel="noopener noreferrer">
            <button style="background-color:#005B99;color:white;border:none;padding:10px 20px;border-radius:5px;font-size:16px;">
                Launch Email Client
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    # CSV Download
    st.download_button(
        label="Download CSV",
        data=csv_data.getvalue(),
        file_name="quote_request.csv",
        mime="text/csv"
    )

    # Quick Book button
    st.markdown(
        f"""
        <a href="{BOOK_URL}" target="_blank" rel="noopener noreferrer">
            <button style="margin-top:8px;padding:10px 20px;font-size:16px;background-color:#005B99;color:white;border:none;border-radius:5px;">
                Book Quote
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    # Reset flow back to quote page
    if st.button("Get New Quote"):
        for k in ("quote_total", "quote_id", "quote_details"):
            st.session_state.pop(k, None)
        st.session_state.page = "quote"
        st.rerun()
