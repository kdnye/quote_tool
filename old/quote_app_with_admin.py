
import streamlit as st
import pandas as pd
import os
import sqlite3
import requests
from datetime import datetime
from io import BytesIO
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import re

# === DB Setup ===
DB_PATH = "sqlite:///app.db"
engine = create_engine(DB_PATH, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()
session = Session()

# === Models ===
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(50))
    business_name = Column(String(100))
    business_phone = Column(String(50))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    quotes = relationship("Quote", back_populates="user")

class Quote(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    quote_type = Column(String(20))
    origin = Column(String(20))
    destination = Column(String(20))
    weight = Column(Float)
    zone = Column(String(5))
    total = Column(Float)
    quote_metadata = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="quotes")

Base.metadata.create_all(engine)

# === Auth ===
def is_valid_password(password):
    return (len(password) >= 14 and re.search(r"[A-Z]", password) and re.search(r"[a-z]", password) and re.search(r"[0-9]", password) and re.search(r"[^a-zA-Z0-9]", password)) or (len(password) >= 24 and password.isalpha())

def login():
    st.subheader("🔑 Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        db = Session()
        user = db.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if user.is_approved:
                st.session_state.user = user.id
                st.session_state.role = user.role
                st.session_state.name = user.name
                st.session_state.page = "quote"
                st.rerun()
            else:
                st.warning("Awaiting admin approval.")
        else:
            st.error("Invalid credentials.")

def register():
    st.subheader("📝 Register")
    with st.form("register_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        business_name = st.text_input("Business Name")
        business_phone = st.text_input("Business Phone")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        if submit:
            if password != confirm:
                st.error("Passwords do not match.")
                return
            if not is_valid_password(password):
                st.error("Password must be ≥14 chars with upper/lower/number/symbol OR a 24+ char passphrase (letters only).")
                return
            db = Session()
            if db.query(User).filter_by(email=email).first():
                st.error("Email already registered.")
            else:
                new_user = User(
                    name=name, email=email, phone=phone, business_name=business_name, business_phone=business_phone,
                    password_hash=generate_password_hash(password)
                )
                db.add(new_user)
                db.commit()
                st.success("Registration submitted. Await admin approval.")

# === Google Distance Helper ===
def get_distance_miles(origin_zip, destination_zip):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin_zip}&destination={destination_zip}&mode=driving&key={api_key}&sensor=false"
    try:
        response = requests.get(url)
        data = response.json()
        if data["status"] == "OK":
            meters = data["routes"][0]["legs"][0]["distance"]["value"]
            return meters / 1609.344
    except Exception:
        return None

# === Quote Logic ===
def show_quote_ui():
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

                zone = "X"
                for _, row in rates_df[["MILES", "ZONE"]].dropna().sort_values("MILES").iterrows():
                    if miles <= row["MILES"]:
                        zone = row["ZONE"]
                        break

                is_zone_x = zone.upper() == "X"
                per_lb = float(rates_df.loc[rates_df["ZONE"] == zone, "PER LB"].values[0])
                fuel_pct = float(rates_df.loc[rates_df["ZONE"] == zone, "FUEL"].values[0]) / 100
                min_charge = float(rates_df.loc[rates_df["ZONE"] == zone, "MIN"].values[0])
                weight_break = float(rates_df.loc[rates_df["ZONE"] == zone, "WEIGHT BREAK"].values[0])

                if is_zone_x:
                    per_mile = min_charge
                    subtotal = (miles * per_mile) + (weight * per_lb) + accessorial_total
                else:
                    base = ((weight - weight_break) * per_lb + min_charge) if weight > weight_break else min_charge
                    subtotal = base + accessorial_total

                quote_total = subtotal * (1 + fuel_pct) * 1.25

            else:  # Air
                zip_zone_df = workbook["ZIP CODE ZONES"]
                cost_zone_table = workbook["COST ZONE TABLE"]
                air_cost_df = workbook["Air Cost Zone"]
                zip_zone_df.columns = zip_zone_df.columns.str.strip().str.upper()
                cost_zone_table.columns = cost_zone_table.columns.str.strip().str.upper()
                air_cost_df.columns = air_cost_df.columns.str.strip().str.upper()

                orig_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(origin)]["DEST ZONE"].values[0])
                dest_zone = int(zip_zone_df[zip_zone_df["ZIPCODE"] == int(destination)]["DEST ZONE"].values[0])
                beyond_zone = zip_zone_df[zip_zone_df["ZIPCODE"] == int(destination)]["BEYOND"].values[0]
                concat = int(f"{orig_zone}{dest_zone}")
                cost_zone = cost_zone_table[cost_zone_table["CONCATENATE"] == concat]["COST ZONE"].values[0]
                cost_row = air_cost_df[air_cost_df["ZONE"] == cost_zone]
                min_charge = float(cost_row["MIN"].values[0])
                per_lb = float(cost_row["PER LB"].replace("$", "").values[0])
                weight_break = float(cost_row["WEIGHT BREAK"].values[0])
                base = max(min_charge, weight * per_lb if weight <= weight_break else min_charge)
                quote_total = base + accessorial_total
                if "Guarantee Service (25%, Deliveries Only)" in selected:
                    quote_total *= 1.25

            st.success(f"Total Quote: ${quote_total:,.2f}")
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
            session.add(quote)
            session.commit()
        except Exception as e:
            st.error(f"Quote failed: {e}")

# === App Start ===
st.set_page_config("Quote App", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "auth"

if st.session_state.page == "auth":
    auth_mode = st.radio("Choose Action", ["Login", "Register"])
    login() if auth_mode == "Login" else register()
elif st.session_state.page == "quote":
    st.sidebar.success(f"Logged in as {st.session_state.name}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    show_quote_ui()

# === Admin Panel ===
def show_admin_panel():
    st.subheader("🛠️ Admin Panel")
    users = session.query(User).all()
    for u in users:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.text(f"{u.name} ({u.email})")
        with col2:
            st.text(f"{'✅ Approved' if u.is_approved else '❌ Pending'} - {u.role.title()}")
        with col3:
            if not u.is_approved and st.button(f"Approve {u.id}", key=f"approve_{u.id}"):
                u.is_approved = True
                session.commit()
                st.success(f"User {u.name} approved")
            if st.button(f"Delete {u.id}", key=f"delete_{u.id}"):
                session.delete(u)
                session.commit()
                st.warning(f"User {u.name} deleted")
