import streamlit as st
from auth import login_ui, register_ui
from quote.ui import quote_ui
from quote.admin_view import quote_admin_view
from admin import admin_panel
from quote.email_form import email_form_ui
from config import Config

st.set_page_config("Quote Tool", layout="wide")

# Honor query params (?page=...)
qp = st.query_params
if qp.get("page"):
    page_from_qp = qp["page"][0] if isinstance(qp.get("page"), list) else qp.get("page")
    st.session_state.page = page_from_qp

# Initialize session state
if "page" not in st.session_state:
    # PUBLIC by default
    st.session_state.page = "quote"
if "role" not in st.session_state:
    st.session_state.role = "guest"   # guest/user/admin

def require_admin():
    if st.session_state.get("role") != "admin":
        st.warning("Admin login required.")
        st.session_state.page = "auth"
        st.rerun()

# ---- Simple top bar ----
with st.sidebar:
    st.image("FSI-logo.png", width=200)
    if st.session_state.get("role") == "admin":
        st.success(f"Admin: {st.session_state.get('name', '')}")
        if st.button("Go to Admin Dashboard"):
            st.session_state.page = "admin"; st.rerun()
        if st.button("Log out"):
            for k in ("user","name","email","role"):
                st.session_state.pop(k, None)
            st.session_state.page = "quote"
            st.rerun()
    else:
        if st.button("Admin Login"):
            st.session_state.page = "auth"; st.rerun()
    # Always available to everyone
    if st.button("Get Quote"):
        st.session_state.page = "quote"; st.rerun()

# ---- Routing ----
page = st.session_state.page

if page == "auth":
    # Only show login (keep register link optional)
    tabs = st.tabs(["Login", "Register"])
    with tabs[0]:
        login_ui()
    with tabs[1]:
        register_ui()  # remove this tab if you don't want self-signup

elif page == "quote":
    quote_ui()

elif page == "email_request":
    email_form_ui()

elif page == "admin":
    require_admin()
    st.title("🛠️ Admin Dashboard")
    admin_mode = st.radio("Choose admin function", ["Manage Users", "View Quotes"], horizontal=True)
    if admin_mode == "Manage Users":
        admin_panel()
    elif admin_mode == "View Quotes":
        quote_admin_view()
