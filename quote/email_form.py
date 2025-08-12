# Directory: quote/
# File: email_form.py
import streamlit as st
from db import Session, EmailQuoteRequest, Quote
import urllib.parse
import csv
from io import StringIO
import pandas as pd
from quote.utils import normalize_workbook  # read accessorial prices from the workbook

BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"

# ---------- helpers ----------
def _load_quote_from_db(quote_id: str):
    if not quote_id:
        return None
    db = Session()
    q = db.query(Quote).filter(Quote.quote_id == quote_id).first()
    db.close()
    if not q:
        return None
    accessorials = []
    if getattr(q, "quote_metadata", None):
        accessorials = [s.strip() for s in str(q.quote_metadata).split(",") if s.strip()]
    return {
        "origin": getattr(q, "origin", "") or "",
        "destination": getattr(q, "destination", "") or "",
        "weight": float(getattr(q, "weight", 0.0) or 0.0),
        "quote_type": getattr(q, "quote_type", "") or "",
        "accessorials": accessorials,
        "quote_total": float(getattr(q, "total", 0.0) or 0.0),
    }

def _first_numeric_in_column(series: pd.Series) -> float:
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
    """Return ([(name, price), ...], subtotal) from the Accessorials sheet headers."""
    try:
        wb = pd.read_excel("HotShot Quote.xlsx", sheet_name=None)
        wb = normalize_workbook(wb)
        df = wb["Accessorials"]
    except Exception:
        return [(name, 0.0) for name in selected_names], 0.0

    rows = []
    subtotal = 0.0
    for name in selected_names:
        if "guarantee" in str(name).lower():
            continue
        price = _first_numeric_in_column(df[name]) if name in df.columns else 0.0
        rows.append((name, float(price)))
        subtotal += float(price)
    return rows, subtotal

# ---------- main UI ----------
def email_form_ui():
    st.subheader("Email Quote Request ($15 Admin Fee)")
    st.markdown("Please fill out the form below to request a booking for this quote. The information will be sent to the FSI Operations Team.")

    # Read quote_id from the URL for new-tab flows
    qp = st.query_params
    qp_quote_id = qp["quote_id"][0] if isinstance(qp.get("quote_id"), list) else qp.get("quote_id")

    # If session is missing the quote (brand-new tab), backfill from DB
    if "quote_id" not in st.session_state and qp_quote_id:
        st.session_state.quote_id = qp_quote_id
    if "quote_details" not in st.session_state and qp_quote_id:
        loaded = _load_quote_from_db(qp_quote_id)
        if loaded:
            st.session_state.quote_details = loaded

    if "quote_details" not in st.session_state or "quote_id" not in st.session_state:
        st.warning("No active quote found in session.")
        return

    quote_details = st.session_state.quote_details
    quote_id = st.session_state.quote_id

    # Build accessorials data + guarantee amount for email body
    selected_accessorials = quote_details.get("accessorials", [])
    acc_rows, acc_subtotal = _accessorial_prices(selected_accessorials)
    guarantee_selected = any("guarantee" in str(x).lower() for x in selected_accessorials)
    final_total = float(quote_details.get("quote_total", 0.0))
    guarantee_amount = 0.0
    if guarantee_selected and (quote_details.get("quote_type", "") == "Air") and final_total > 0:
        # If final = base*1.25, then guarantee = final * 0.20
        guarantee_amount = round(final_total * 0.20, 2)
    acc_plus_guarantee_subtotal = round(acc_subtotal + guarantee_amount, 2)

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

    # Save the request
    db = Session()
    new_request = EmailQuoteRequest(
        quote_id=quote_id,
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

    # CSV export
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow([
        "Quote ID","Shipper Name","Shipper Address","Shipper Contact","Shipper Phone",
        "Consignee Name","Consignee Address","Consignee Contact","Consignee Phone",
        "Total Weight","Special Instructions"
    ])
    writer.writerow([
        quote_id, shipper_name, shipper_address, shipper_contact, shipper_phone,
        consignee_name, consignee_address, consignee_contact, consignee_phone,
        total_weight, special_instructions
    ])
    st.download_button(
        label="Download CSV",
        data=csv_data.getvalue(),
        file_name="quote_request.csv",
        mime="text/csv"
    )

    # ---------- EMAIL BODY FORMATTING (aligned table + footer info) ----------
    def _fmt_money(x: float) -> str:
        return f"${x:,.2f}"

    NAME_COL = 28
    AMT_COL = 12
    SEP = "-" * 12

    def _line(name: str, amount: float) -> str:
        return f"{name:<{NAME_COL}}{_fmt_money(amount):>{AMT_COL}}"

    lines = []
    # Header triplet
    lines.append(f"Origin: {quote_details.get('origin','')}")
    lines.append(f"Destination: {quote_details.get('destination','')}")
    lines.append(f"Weight: {total_weight}")
    lines.append("")  # blank line

    # Accessorials section
    lines.append("Accessorials")
    lines.append(SEP)
    for name, price in acc_rows:
        lines.append(_line(name, price))
    lines.append(SEP)
    lines.append(_line("Subtotal:", acc_subtotal))
    lines.append(SEP)

    # Guarantee (own block, amount on its own line, then separator)
    if guarantee_selected:
        lines.append(f"{'Guarantee (25%)':<25}{_fmt_money(guarantee_amount)}")
        lines.append(SEP)
        lines.append(_line("Accessorials + Guarantee Subtotal:", acc_plus_guarantee_subtotal))
        lines.append(SEP)

    lines.append("")  # blank line
    lines.append(f"Quote Total: {_fmt_money(final_total)}")
    lines.append("")  # blank line

    # Footer block you wanted (restored)
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
    lines.append(f"Accessorials Selected: {', '.join(selected_accessorials)}")
    lines.append(f"Quote ID: {quote_id}")

    email_body = "\n".join(lines) + "\n"

    mailto_link = (
        "mailto:operations@fsi.com"
        f"?subject={urllib.parse.quote(f'Quote Request for ID: {quote_id}')}"
        f"&body={urllib.parse.quote(email_body)}"
    )

    # Auto-launch the email client immediately (no separate button)
    st.components.v1.html(
        f"""
        <html>
          <head><meta http-equiv="refresh" content="0; url={mailto_link}"></head>
          <body></body>
        </html>
        """,
        height=0,
    )

    # Optional: quick booking button remains visible after launch
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
