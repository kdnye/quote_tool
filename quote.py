import streamlit as st 
import pandas as pd
import os
import requests
from datetime import datetime
from db import Session, Quote

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

def quote_ui():
    st.title("📦 Quote Tool")
    quote_mode = st.radio("Select Quote Type", ["Hotshot", "Air"])
    workbook = pd.read_excel("HotShot Quote.xlsx", sheet_name=None)

    accessorials_df = workbook["Accessorials"]
    accessorials_df.columns = accessorials_df.columns.str.strip().str.upper()

    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input("Origin Zip")
        destination = st.text_input("Destination Zip")
        weight = st.number_input("Weight (lbs)", step=1, min_value=1)
    with col2:
        st.subheader("🔧 Accessorials")
        selected = []
        if quote_mode == "Hotshot":
            options = {
                "4hr Window Pickup/Delivery": "4hr Window",
                "Specific Time Pickup/Delivery": "Special",
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

                zip_zone_df.columns = zip_zone_df.columns.str.strip().str.upper()
                cost_zone_table.columns = cost_zone_table.columns.str.strip().str.upper()
                air_cost_df.columns = air_cost_df.columns.str.strip().str.upper()

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

                if "Guarantee Service (25%, Deliveries Only)" in selected:
                    quote_total *= 1.25

            st.success(f"Total Quote: ${quote_total:,.2f}")
            st.write(f"Weight: {weight}")
            st.write(f"Weight Break: {weight_break}")
            st.write(f"Per LB: {per_lb}")
            st.write(f"Min Charge: {min_charge}")
            st.write(f"Accessorials: {accessorial_total}")

            db = Session()
            quote = Quote(
                user_id=st.session_state.user,
                quote_type=quote_mode,
                origin=origin,
                destination=destination,
                weight=weight,
                zone=zone if quote_mode == "Hotshot" else str(concat),
                total=quote_total,
                quote_metadata=", ".join(selected)
            )
            db.add(quote)
            db.commit()
            db.close()
        except Exception as e:
            st.error(f"Quote failed: {e}")
