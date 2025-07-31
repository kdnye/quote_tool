# Directory: quote/
# File: ui.py
import streamlit as st
import pandas as pd
from quote.theme import inject_fsi_theme
from quote.utils import normalize_workbook, calculate_accessorials
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from db import Session, Quote

def quote_ui():
    inject_fsi_theme()
    if "email" not in st.session_state:
        st.session_state.email = ""

    st.image("FSI-logo.png", width=280)
    st.title("📦 Quote Tool")
    quote_mode = st.radio("Select Quote Type", ["Hotshot", "Air"])
    workbook = pd.read_excel("HotShot Quote.xlsx", sheet_name=None)
    workbook = normalize_workbook(workbook)

    accessorials_df = workbook["Accessorials"]

    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input("Origin Zip")
        destination = st.text_input("Destination Zip")

        st.subheader("📦 Weight Entry")
        weight_input_method = st.radio("Choose weight type", ["Actual Weight", "Dimensional Weight"])

        if weight_input_method == "Actual Weight":
            weight = st.number_input("Enter actual weight (lbs)", min_value=1.0, step=1.0)
        else:
            st.markdown("**Enter package dimensions (inches):**")
            length = st.number_input("Length", min_value=1.0)
            width = st.number_input("Width", min_value=1.0)
            height = st.number_input("Height", min_value=1.0)
            dim_factor = 166 if quote_mode == "Air" else 139
            weight = (length * width * height) / dim_factor
            st.info(f"Calculated Dimensional Weight: **{weight:.2f} lbs**")

    with col2:
        st.subheader("🔧 Accessorials")
        selected = []
        if quote_mode == "Hotshot":
            options = {
                "4hr Window Pickup/Delivery": "4hr Window",
                "Specific Time Pickup/Delivery": "Less than 4 hrs",
                "Afterhours Pickup (Return Only)": "After Hours",
                "Weekend Pickup/Delivery": "Weekend",
                "Two-Man Team Pickup/Delivery": "Two Man",
                "Liftgate Pickup/Delivery": "Liftgate",
            }
        else:
            options = {
                "Guarantee Service (25%, Deliveries Only)": "Guarantee",
                "Anything less than 8hrs but more than 4hrs": "4hr Window",
                "4hrs or less Pickup/Delivery": "Less than 4 hrs",
                "After Hours": "After Hours",
                "Weekend Pickup/Delivery": "Weekend",
                "Two-Man Team Pickup/Delivery": "Two Man",
                "Liftgate Pickup/Delivery": "Liftgate",
            }
        for label in options:
            if st.checkbox(label):
                selected.append(label)

    if st.button("Get Quote"):
        try:
            accessorial_total = calculate_accessorials(selected, accessorials_df, options)
            result = {}

            if quote_mode == "Hotshot":
                rates_df = workbook["Hotshot Rates"]
                result = calculate_hotshot_quote(origin, destination, weight, accessorial_total, rates_df)
            else:
                result = calculate_air_quote(origin, destination, weight, accessorial_total, workbook)
                if result.get("origin_charge", 0) > 0:
                    selected.append(f"Origin Beyond Zone {result['origin_beyond']}: ${result['origin_charge']:,.2f}")
                if result.get("dest_charge", 0) > 0:
                    selected.append(f"Destination Beyond Zone {result['dest_beyond']}: ${result['dest_charge']:,.2f}")
                if "Guarantee Service (25%, Deliveries Only)" in selected:
                    result["quote_total"] *= 1.25

            st.success(f"Total Quote: ${result['quote_total']:,.2f}")
            if result["quote_total"] > 6000 or weight > (1200 if quote_mode == "Air" else 5000):
                st.warning("""🚨 **Please contact FSI directly to confirm the most correct rate for your shipment.**\nPhone: 800-651-0423\nEmail: Operations@freightservices.net""")

            st.write(f"Weight: {weight}")
            st.write(f"Weight Break: {result['weight_break']}")
            st.write(f"Per LB: {result['per_lb']}")
            st.write(f"Min Charge: {result['min_charge']}")
            st.write(f"Accessorials: {accessorial_total}")
            if quote_mode == "Air":
                st.write(f"Beyond Charges: ${result['beyond_total']:,.2f}")

            db = Session()
            quote = Quote(
                user_id=st.session_state.user,
                user_email=st.session_state.get("email", ""),
                quote_type=quote_mode,
                origin=origin,
                destination=destination,
                weight=weight,
                weight_method="Dimensional" if weight_input_method == "Dimensional Weight" else "Actual",
                zone=result["zone"],
                total=result["quote_total"],
                quote_metadata=", ".join(selected)
            )
            db.add(quote)
            db.commit()
            st.write(f"Quote ID: {quote.quote_id}")
            db.close()

            st.markdown("""
                <a href="https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F" target="_blank">
                    <button style="margin-top:10px;padding:10px 20px;font-size:16px;background-color:#005B99;color:white;border:none;border-radius:5px;">
                        Book Shipment
                    </button>
                </a>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Quote failed: {e}")