#auth.py
try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - streamlit not required for tests
    st = None
from werkzeug.security import generate_password_hash, check_password_hash
import re
from db import Session, User

def is_valid_password(password):
    if len(password) >= 14 and re.search(r'[A-Z]', password) and re.search(r'[a-z]', password) and re.search(r'[0-9]', password) and re.search(r'[^a-zA-Z0-9]', password):
        return True
    if len(password) >= 24 and password.isalpha():
        return True
    return False

def login_ui():
    if st is None:
        raise RuntimeError("Streamlit is required for the legacy UI.")
    st.subheader("🔑 Admin Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        db = Session()
        user = db.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            if not getattr(user, "is_approved", True):
                st.error("Account pending approval.")
            else:
                st.session_state.user = user.id
                st.session_state.name = user.name
                st.session_state.email = user.email
                st.session_state.role = user.role or "user"
                # Send admins to admin, everyone else to quote
                st.session_state.page = "admin" if st.session_state.role == "admin" else "quote"
                st.success(f"Welcome {user.name}!")
                st.rerun()
        else:
            st.error("Invalid credentials.")
        db.close()


def register_ui():
    if st is None:
        raise RuntimeError("Streamlit is required for the legacy UI.")
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
                    name=name,
                    email=email,
                    phone=phone,
                    business_name=business_name,
                    business_phone=business_phone,
                    password_hash=generate_password_hash(password),
                    is_approved=True
                )
                db.add(new_user)
                db.commit()
                st.success("Registration successful! You can now log in.")
            db.close()

def reset_password_ui():
    if st is None:
        raise RuntimeError("Streamlit is required for the legacy UI.")
    st.subheader("🔁 Reset Password")
    with st.form("reset_form"):
        email = st.text_input("Email")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit = st.form_submit_button("Reset Password")
        if submit:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
            if not is_valid_password(new_password):
                st.error("Password must meet complexity requirements.")
                return
            db = Session()
            user = db.query(User).filter_by(email=email).first()
            if user:
                user.password_hash = generate_password_hash(new_password)
                db.commit()
                st.success("Password updated successfully.")
            else:
                st.error("No user found with that email.")
            db.close()
