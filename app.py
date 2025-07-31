# app.py

import streamlit as st
from auth import login_ui, register_ui
from quote.ui import quote_ui
from quote.admin_view import quote_admin_view
from admin import admin_panel

st.set_page_config("Quote Tool", layout="wide")

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "auth"

# Routing
if st.session_state.page == "auth":
    st.image("FSI-logo.png", width=240)
    mode = st.radio("Choose Action", ["Login", "Register"], horizontal=True)
    if mode == "Login":
        login_ui()
    else:
        register_ui()

elif st.session_state.page == "quote":
    quote_ui()

elif st.session_state.page == "admin":
    st.title("🛠️ Admin Dashboard")
    admin_mode = st.radio("Choose admin function", ["Manage Users", "View Quotes"], horizontal=True)

    if admin_mode == "Manage Users":
        admin_panel()
    elif admin_mode == "View Quotes":
        quote_admin_view()
