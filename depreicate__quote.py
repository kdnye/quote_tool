#quote.py
import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime
from db import Session, Quote
from config import Config

def inject_fsi_theme():
    st.markdown("""
        <style>
            body {
                background-color: #a0a0a0;
                color: #FFFFFF;
            }
            .stApp {
                background-color: #a0a0a0;
                color: #FFFFFF;
            }
            .stButton>button {
                background-color: #005B99;
                color: white;
                border-radius: 6px;
                padding: 0.5em 1em;
                font-weight: 600;
            }
            .stButton>button:hover {
                background-color: #003366;
            }
            .stRadio > div {
                color: #FFFFFF;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF;
            }
            .stCheckbox > label, .stTextInput > div > label, .stNumberInput > div > label {
                color: #FFFFFF;
                font-weight: 500;
            }
            .stSubheader, .stMarkdown {
                color: #FFFFFF;
            }
        </style>
    """, unsafe_allow_html=True)
    
def get_distance_miles(origin_zip, destination_zip):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_zip}&destination={destination_zip}&mode=driving&key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1609.344  # exact float
    except:
        return None
def quote_admin_view():
    inject_fsi_theme()
    st.subheader("📦 All Submitted Quotes")

    db = Session()
    quotes = db.query(Quote).all()
    db.close()

    import pandas as pd
    df = pd.DataFrame([{
        "Quote ID": q.quote_id,
        "User ID": q.user_id,
        "User Email": q.user_email,
        "Type": q.quote_type,
        "Origin": q.origin,
        "Destination": q.destination,
        "Weight": q.weight,
        "Method": q.weight_method,
        "Zone": q.zone,
        "Total": q.total,
        "Accessorials": q.quote_metadata,
        "Date": q.created_at.strftime("%Y-%m-%d %H:%M")
    } for q in quotes])

    st.dataframe(df)

def quote_ui():
    inject_fsi_theme()
    if "email" not in st.session_state:
        st.session_state.email = ""
    st.image("FSI-logo.png", width=280)
    st.title("📦 Quote Tool")
    quote_mode = st.radio("Select Quote Type", ["Hotshot", "Air"])
    workbook = pd.read_excel(Config.WORKBOOK_PATH, sheet_name=None)

    accessorials_df = workbook["Accessorials"]
    accessorials_df.columns = accessorials_df.columns.str.strip().str.upper()

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
            accessorial_total = 0
            for label in selected:
                key = options[label].upper()
                if key != "GUARANTEE":
                    cost = float(accessorials_df[key].values[0])
                    accessorial_total += cost

            if quote_mode == "Hotshot":
                rates_df = workbook["Hotshot Rates"]
                rates_df.columns = rates_df.columns.str.strip().str.upper()
                rates_df["MILES"] = pd.to_numeric(rates_df["MILES"], errors="coerce")
                miles = get_distance_miles(origin, destination) or 0
                st.markdown(f"**Exact Miles:** {miles:.2f}")

                zone = "X"
                for _, row in rates_df[["MILES", "ZONE"]].dropna().sort_values("MILES").iterrows():
                    if miles <= row["MILES"]:
                        zone = row["ZONE"]
                        break

                is_zone_x = zone.upper() == "X"
                per_lb = float(rates_df.loc[rates_df["ZONE"] == zone, "PER LB"].values[0])
                fuel_pct = float(rates_df.loc[rates_df["ZONE"] == zone, "FUEL"].values[0])
                min_charge = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
                weight_break = float(rates_df.loc[rates_df["ZONE"] == zone, "WEIGHT BREAK"].values[0])

                if is_zone_x:
                    rate_per_mile = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
                    miles_charge = miles * rate_per_mile * (1 + fuel_pct)
                    subtotal = miles_charge + accessorial_total
                else:
                    base = max(min_charge, weight * per_lb)
                    subtotal = base * (1 + fuel_pct) + accessorial_total

                quote_total = subtotal

            else:
                zip_zone_df = workbook["ZIP CODE ZONES"]
                cost_zone_table = workbook["COST ZONE TABLE"]
                air_cost_df = workbook["Air Cost Zone"]
                beyond_df = workbook["Beyond Price"]

                zip_zone_df.columns = zip_zone_df.columns.str.strip().str.upper()
                cost_zone_table.columns = cost_zone_table.columns.str.strip().str.upper()
                air_cost_df.columns = air_cost_df.columns.str.strip().str.upper()
                beyond_df.columns = beyond_df.columns.str.strip().str.upper()

                orig_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(origin)]["DEST ZONE"].values[0])
                dest_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(destination)]["DEST ZONE"].values[0])
                concat = int(f"{orig_zone}{dest_zone}")

                cost_zone = cost_zone_table[cost_zone_table["CONCATENATE"] == concat]["COST ZONE"].values[0]
                cost_row = air_cost_df[air_cost_df["ZONE"].str.strip() == str(cost_zone).strip()].iloc[0]

                min_charge = float(cost_row["MIN"])
                per_lb = float(str(cost_row["PER LB"]).replace("$", "").replace(",", ""))
                weight_break = float(cost_row["WEIGHT BREAK"])

                if weight > weight_break:
                    base = ((weight - weight_break) * per_lb) + min_charge
                else:
                    base = min_charge

                quote_total = base + accessorial_total

                def get_beyond_zone(zipcode):
                    row = zip_zone_df[zip_zone_df["ZIPCODE"] == int(zipcode)]
                    if not row.empty and "BEYOND" in row.columns:
                        val = str(row["BEYOND"].values[0]).strip().upper()
                        if val in ("", "N/A", "NO", "NONE", "NAN"):
                            return None
                        return val.split()[-1]  # e.g., "Zone B" → "B"
                    return None

                def get_beyond_rate(zone_code):
                    if not zone_code:
                        return 0.0
                    match = beyond_df[beyond_df["ZONE"].str.strip().str.upper() == zone_code]
                    if not match.empty:
                        try:
                            return float(str(match["RATE"].values[0]).replace("$", "").replace(",", "").strip())
                        except Exception:
                            return 0.0
                    return 0.0

                origin_beyond = get_beyond_zone(origin)
                dest_beyond = get_beyond_zone(destination)
                origin_charge = get_beyond_rate(origin_beyond)
                dest_charge = get_beyond_rate(dest_beyond)

                beyond_total = origin_charge + dest_charge
                quote_total += beyond_total

                if origin_charge > 0:
                    selected.append(f"Origin Beyond Zone {origin_beyond}: ${origin_charge:,.2f}")
                if dest_charge > 0:
                    selected.append(f"Destination Beyond Zone {dest_beyond}: ${dest_charge:,.2f}")

                if "Guarantee Service (25%, Deliveries Only)" in selected:
                    quote_total *= 1.25

            st.success(f"Total Quote: ${quote_total:,.2f}")
            weight_threshold = 1200 if quote_mode == "Air" else 5000

            if quote_total > 6000 or weight > weight_threshold:
                st.warning("""🚨 **Please contact FSI directly to confirm the most correct rate for your shipment.**
                                   Phone: 800-651-0423  
                                   Email: Operations@freightservices.net""")

            st.write(f"Weight: {weight}")
            st.write(f"Weight Break: {weight_break}")
            st.write(f"Per LB: {per_lb}")
            st.write(f"Min Charge: {min_charge}")
            st.write(f"Accessorials: {accessorial_total}")
            if quote_mode == "Air":
                st.write(f"Beyond Charges: ${beyond_total:,.2f} ({origin_beyond or 'N/A'}: ${origin_charge:,.2f}, {dest_beyond or 'N/A'}: ${dest_charge:,.2f})")
                st.write(f"Origin Beyond: {origin_beyond} @ ${origin_charge}")
                st.write(f"Dest Beyond: {dest_beyond} @ ${dest_charge}")

            db = Session()
            quote = Quote(
                user_id=st.session_state.user,
                user_email = st.session_state.get("email", ""),
                quote_type=quote_mode,
                origin=origin,
                destination=destination,
                weight=weight,
                weight_method="Dimensional" if weight_input_method == "Dimensional Weight" else "Actual",
                zone=zone if quote_mode == "Hotshot" else str(concat),
                total=quote_total,
                quote_metadata=", ".join(selected)
            )
            db.add(quote)
            db.commit()
            st.write(f"Quote ID: {quote.quote_id}")
            db.close()
            book_url = "https://freightservices.ts2000.net/login?returnUrl=%2FLogin%2F"
            st.markdown(f"""
            <a href="{book_url}" target="_blank">
                <button style="margin-top:10px;padding:10px 20px;font-size:16px;background-color:#005B99;color:white;border:none;border-radius:5px;">
                    Book Shipment
                </button>
            </a>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Quote failed: {e}")