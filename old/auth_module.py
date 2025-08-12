import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

# === Setup ===
DB_PATH = "sqlite:///app.db"
engine = create_engine(DB_PATH, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

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

def is_valid_password(password):
    if len(password) >= 14 and re.search(r'[A-Z]', password) and re.search(r'[a-z]', password) and re.search(r'[0-9]', password) and re.search(r'[^a-zA-Z0-9]', password):
        return True
    if len(password) >= 24 and password.isalpha():
        return True
    return False

def register():
    st.subheader("🔐 Register")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    business_name = st.text_input("Business Name")
    business_phone = st.text_input("Business Phone")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
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
                name=name,
                email=email,
                phone=phone,
                business_name=business_name,
                business_phone=business_phone,
                password_hash=generate_password_hash(password),
                is_approved=False,
                role="user"
            )
            db.add(new_user)
            db.commit()
            st.success("Registration submitted. Await admin approval.")
        db.close()

def login():
    st.subheader("🔑 Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        db = Session()
        user = db.query(User).filter_by(email=email).first()
        db.close()
       if user and check_password_hash(user.password_hash, password):
        if user.is_approved:
            st.session_state.user = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
            # 👇 Set default view for admin
            st.session_state.page = "quote" if user.role != "admin" else "quote"

            st.success(f"Welcome {user.name}!")
            else:
                st.warning("Your account is pending admin approval.")
        else:
            st.error("Invalid credentials.")

def auth_ui():
    if "user" not in st.session_state:
        auth_mode = st.radio("Select:", ["Login", "Register"])
        if auth_mode == "Login":
            login()
        else:
            register()
    else:
        st.success(f"Logged in as {st.session_state.user['name']}")
        if st.session_state.user["role"] == "admin":
            st.radio("🔀 Switch View", ["Quote Tool", "Admin Panel"], key="page", horizontal=True)

        if st.button("Logout"):
            for key in ["user", "page"]:
                if key in st.session_state:
                    del st.session_state[key]
