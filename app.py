# =============================
# File: app.py (updated)
# =============================

import streamlit as st
from auth import login_ui, register_ui
from quote.ui import quote_ui
from quote.admin_view import quote_admin_view
from admin import admin_panel
from quote.email_form import email_form_ui

st.set_page_config("Quote Tool", layout="wide")

# NEW: honor query params so ?page=email_request works in a new tab
qp = st.query_params
if qp.get("page"):
    st.session_state.page = qp["page"][0] if isinstance(qp.get("page"), list) else qp.get("page")


# --- Read routing from query params so we can open pages in a NEW TAB via ?page=...
# Uses the non-experimental API per deprecation notice
qp = st.query_params
if qp.get("page"):
    # qp values may be list-like; handle both
    page_from_qp = qp["page"][0] if isinstance(qp.get("page"), list) else qp.get("page")
    st.session_state.page = page_from_qp

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

elif st.session_state.page == "email_request":
    email_form_ui()

elif st.session_state.page == "admin":
    st.title("🛠️ Admin Dashboard")
    admin_mode = st.radio("Choose admin function", ["Manage Users", "View Quotes"], horizontal=True)

    if admin_mode == "Manage Users":
        admin_panel()
    elif admin_mode == "View Quotes":
        quote_admin_view()