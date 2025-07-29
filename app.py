import streamlit as st
from auth import login_ui, register_ui
from quote import quote_ui
from admin import admin_panel

st.set_page_config("Quote Tool", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "auth"

if st.session_state.page == "auth":
    mode = st.radio("Choose Action", ["Login", "Register"])
    login_ui() if mode == "Login" else register_ui()
elif st.session_state.page == "quote":
    quote_ui()
elif st.session_state.page == "admin":
    admin_panel()