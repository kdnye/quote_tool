import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import hashlib
import re

# Shared DB setup
DB_PATH = "sqlite:///app.db"
engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(pw):
    return (len(pw) >= 14 and re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw) and re.search(r"[^a-zA-Z0-9]", pw)) or len(pw) >= 24

def login(email, password):
    user = session.query(User).filter_by(email=email).first()
    if user and user.password_hash == hash_password(password):
        return user
    return None

def register_user(name, email, phone, biz_name, biz_phone, password):
    if not validate_password(password):
        st.error("Password does not meet complexity requirements.")
        return
    existing = session.query(User).filter_by(email=email).first()
    if existing:
        st.error("Email already registered.")
        return
    user = User(name=name, email=email, phone=phone, business_name=biz_name, business_phone=biz_phone, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    st.success("Registration submitted for approval.")

st.set_page_config(page_title="Quote App", layout="wide")

st.sidebar.title("Authentication")
auth_action = st.sidebar.radio("Choose Action", ["Login", "Register"])

if auth_action == "Register":
    with st.sidebar.form("register_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        biz_name = st.text_input("Business Name")
        biz_phone = st.text_input("Business Phone")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Register")
        if submit:
            register_user(name, email, phone, biz_name, biz_phone, password)

elif auth_action == "Login":
    with st.sidebar.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            user = login(email, password)
            if user:
                if not user.is_approved:
                    st.sidebar.warning("Awaiting admin approval.")
                else:
                    st.sidebar.success(f"Welcome, {user.name}")
                    st.session_state['user'] = user.id
                    st.session_state['role'] = user.role
            else:
                st.sidebar.error("Invalid credentials.")

if st.session_state.get("role") == "admin":
    st.subheader("🛠️ Admin Panel")
    if st.button("Refresh Users"):
        st.rerun()
    users = session.query(User).all()
    for u in users:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.text(f"{u.name} ({u.email})")
        with col2:
            st.text(f"{'✅ Approved' if u.is_approved else '❌ Pending'} - {u.role.title()}")
        with col3:
            if not u.is_approved and st.button(f"Approve {u.id}"):
                u.is_approved = True
                session.commit()
                st.success(f"User {u.name} approved")
            if st.button(f"Delete {u.id}"):
                session.delete(u)
                session.commit()
                st.warning(f"User {u.name} deleted")
