import streamlit as st
from db import Session, EmailQuoteRequest, Quote
import urllib.parse
import csv
from io import StringIO

BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"
ADMIN_FEE = 15.00  # Email-only processing fee


def _load_quote_from_db(quote_id: str):
    if not quote_id:
        return None
    db = Session()
    q = db.query(Quote).filter(Quote.quote_id == quote_id).first()
    db.close()
    if not q:
        return None
    # Rebuild the dict the UI expects (BASE total only; fee is added on this page)
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
        "quote_total": float(q.total or 0.0),  # base total from DB
    }


def email_form_ui():
    st.subheader("Email Quote Request ($15 Admin Fee)")
    st.markdown("Please fill out the form below to request a booking for this quote. The information will be sent to the FSI Operations Team.")

    # Read quote_id from the URL for new-tab flows
    qp = st.query_params  # modern API
    qp_quote_id = None
    if qp.get("quote_id"):
        qp_quote_id = qp["quote_id"][0] if isinstance(qp["quote_id"], list) else qp["quote_id"]

    # If session is missing the quote (new tab), backfill from query param + DB
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

    # Compute email-only totals/flags
    base_total = float(quote_details.get("quote_total", 0.0) or 0.0)
    email_total = base_total + ADMIN_FEE
    guarantee_selected = bool(
        quote_details.get("guarantee_selected")
        or any("guarantee" in s.lower() for s in quote_details.get("accessorials", []))
    )

    # Show a banner clarifying why the total differs here
    st.info(
        f"Email processing adds a ${ADMIN_FEE:.2f} admin fee. "
        f"The 'Book Quote' button does not include this fee."
    )

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
            value=", ".join(quote_details.get("accessorials", []))
        )

        submitted = st.form_submit_button("Submit & Launch Email")

    if submitted:
        # Save record
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
            "Total Weight","Special Instructions","Base Total","Email Total (incl. $15)"
        ])
        writer.writerow([
            quote_id, shipper_name, shipper_address, shipper_contact, shipper_phone,
            consignee_name, consignee_address, consignee_contact, consignee_phone,
            total_weight, special_instructions, f"{base_total:.2f}", f"{email_total:.2f}"
        ])

        # Build and open email (new tab)
        email_body = f"""FSI Operations Team,

I'd like to move forward with the shipment for this quote. Please proceed with scheduling and confirm once booked.

Origin: {quote_details.get("origin","")}
Shipper info:
Name: {shipper_name}
Address: {shipper_address}
Contact: {shipper_contact}
Phone: {shipper_phone}

Destination: {quote_details.get("destination","")}
Consignee info:
Name: {consignee_name}
Address: {consignee_address}
Contact: {consignee_contact}
Phone: {consignee_phone}

Weight: {total_weight}
Accessorials: {', '.join(quote_details.get('accessorials', []))}
Guarantee: {"Yes" if guarantee_selected else "No"}
Quote Total: ${email_total:,.2f} (includes ${ADMIN_FEE:.2f} email admin fee)

Let me know if any additional info is needed.

Quote ID: {quote_id}
"""
        mailto_link = (
            "mailto:operations@fsi.com"
            f"?subject={urllib.parse.quote(f'Quote Request for ID: {quote_id}')}"
            f"&body={urllib.parse.quote(email_body)}"
        )

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

        st.download_button(
            label="Download CSV",
            data=csv_data.getvalue(),
            file_name="quote_request.csv",
            mime="text/csv"
        )

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

        if st.button("Get New Quote"):
            for k in ("quote_total", "quote_id", "quote_details"):
                st.session_state.pop(k, None)
            st.session_state.page = "quote"
            st.rerun()
