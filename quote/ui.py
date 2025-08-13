# Directory: quote/
# File: ui.py

import streamlit as st
import pandas as pd
from quote.theme import inject_fsi_theme
from quote.utils import normalize_workbook
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from db import Session, Quote  # NEW: persist quotes so email page can load by quote_id
import uuid

BOOK_URL = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"


def _first_numeric_in_column(series: pd.Series) -> float:
    """Return the first numeric value in a column; handle $, commas, %, and skip instructions."""
    for val in series.tolist():
        s = str(val).strip()
        if not s:
            continue
        # Skip instructional text like "multiply total by 1.25"
        if "multiply" in s.lower():
            continue
        s = s.replace("$", "").replace(",", "")
        if s.endswith("%"):
            # Subtotal only includes fixed-$ accessorials; percentage handled separately (e.g., Guarantee)
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


def quote_ui():
    inject_fsi_theme()

    if "email" not in st.session_state:
        st.session_state.email = ""

    st.image("FSI-logo.png", width=280)
    st.title("📦 Quote Tool")

    if st.button("Logout"):
        st.session_state.page = "auth"
        st.session_state.clear()
        st.rerun()

    quote_mode = st.radio("Select Quote Type", ["Hotshot", "Air"])
    workbook = pd.read_excel("HotShot Quote.xlsx", sheet_name=None)
    workbook = normalize_workbook(workbook)
    accessorials_df = workbook["Accessorials"]  # headers are the accessorial names

    # ---------- Last Quote panel ----------
    if "quote_details" in st.session_state:
        st.subheader("Last Quote")
        details = st.session_state.quote_details
        big_text = f"""
        <div style='font-size: 2em; line-height: 1.4;'>
            Quote Total:${details['quote_total']:,.2f}<br>
            Origin: {details['origin']} | Destination: {details['destination']}<br>
            Type: {details['quote_type']} | Weight: {details['weight']:,.2f} lbs<br>
        </div>
        """
        st.markdown(big_text, unsafe_allow_html=True)

        # Open email form in a NEW TAB and pass quote_id for the new tab to load from DB/session
        email_url = f"?page=email_request&quote_id={st.session_state.get('quote_id', '')}"
        st.markdown(
            f"""
            <a href="{email_url}" target="_blank" rel="noopener noreferrer">
                <button style="margin-top:8px;padding:10px 20px;font-size:16px;
                                background-color:#005B99;color:white;border:none;border-radius:5px;">
                    Email Quote Request ($15 admin fee)
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

        # Book Quote (new tab)
        st.markdown(
            f"""
            <a href="{BOOK_URL}" target="_blank" rel="noopener noreferrer">
                <button style="margin-top:8px;padding:10px 20px;font-size:16px;
                                background-color:#005B99;color:white;border:none;border-radius:5px;">
                    Book Quote
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    # ---------- Create New Quote ----------
    st.subheader("Create New Quote")
    col1, col2 = st.columns(2)

    # Left column: shipment + weight
    with col1:
        origin = st.text_input("Origin Zip")
        destination = st.text_input("Destination Zip")

        st.subheader("📦 Weight Entry")
        actual_weight = st.number_input("Enter actual weight (lbs)", min_value=1.0, step=1.0)

        st.markdown("**Enter package dimensions (inches):**")
        pieces = st.number_input("Number of Pieces", min_value=1)
        length = st.number_input("Length", min_value=1.0)
        width = st.number_input("Width", min_value=1.0)
        height = st.number_input("Height", min_value=1.0)
        #FSI uses a dim factor of 166
        dim_weight = ((length * width * height) / 166 )*pieces
     
        st.markdown(f"Dimensional Weight: {dim_weight:,.2f} lbs")
        weight = max(actual_weight, dim_weight)
        st.info(f"Using a billable weight of {weight:,.2f} lbs")

    # Right column: accessorials from HEADERS
    with col2:
        st.subheader("⚙️ Accessorials")
        selected: list[str] = []

        accessorial_options = _headers_as_accessorials(accessorials_df)
        for i, acc in enumerate(accessorial_options):
            if st.checkbox(acc, key=f"acc_{i}"):
                selected.append(acc)

        # Subtotal: sum first numeric cell under each selected header (skip percentage-type like Guarantee here)
        subtotal = 0.0
        for acc in selected:
            if "guarantee" in acc.lower():
                continue
            if acc in accessorials_df.columns:
                subtotal += _first_numeric_in_column(accessorials_df[acc])

        st.write(f"Accessorial Subtotal: ${subtotal:,.2f}")

        # Keep a flag for Guarantee to apply after Air total
        guarantee_selected = any("guarantee" in s.lower() for s in selected)

    # ---------- Generate Quote ----------
    if st.button("Generate Quote"):
        accessorial_total = subtotal  # pass fixed-$ accessorials into the calculators

        if quote_mode == "Air":
            result = calculate_air_quote(origin, destination, weight, accessorial_total, workbook)
            quote_total = result["quote_total"]
            if guarantee_selected:
                # Apply Guarantee last (25% multiplier)
                quote_total *= 1.25
        else:
            result = calculate_hotshot_quote(
                origin, destination, weight, accessorial_total, workbook["Hotshot Rates"]
            )
            quote_total = result["quote_total"]

        # Persist to DB so the email page (new tab) can load via ?quote_id=...
        db = Session()
        q = Quote(
            user_id=st.session_state.get("user"),
            user_email=st.session_state.get("email", ""),
            quote_type=quote_mode,
            origin=origin,
            destination=destination,
            weight=weight,
            weight_method="Dimensional" if weight == dim_weight else "Actual",
            zone=str(result.get("zone", "")),
            total=quote_total,                         # store BASE total (no admin fee)
            quote_metadata=", ".join(selected),        # store selected accessorials as CSV
            pieces=int(pieces),
            length=float(length),
            width=float(width),
            height=float(height),
            actual_weight=float(actual_weight),
            dim_weight=float(dim_weight),
        )
        db.add(q)
        db.commit()
        # SQLAlchemy populates q.quote_id (UUID default on model)
        saved_quote_id = q.quote_id
        db.close()

        # Persist “last quote” in session (BASE total — no admin fee here)
        st.session_state.quote_id = saved_quote_id
        st.session_state.quote_details = {
            "origin": origin,
            "destination": destination,
            "weight": weight,
            "quote_type": quote_mode,
            "accessorials": selected,
            "guarantee_selected": guarantee_selected,
            "quote_total": quote_total,   # base total for display; email page adds $15
            "metadata": result,
        }

        # Immediate Book button (also appears in Last Quote on re-render)
        st.markdown(
            f"""
            <a href="{BOOK_URL}" target="_blank" rel="noopener noreferrer">
                <button style="margin-top:8px;padding:10px 20px;font-size:16px;
                                background-color:#005B99;color:white;border:none;border-radius:5px;">
                    Book Quote
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

        st.rerun()
