# File: admin_view.py
import streamlit as st
import pandas as pd
from db import Session, Quote
from quote.theme import inject_fsi_theme

def quote_admin_view():
    inject_fsi_theme()
    st.subheader("📦 All Submitted Quotes")

    db = Session()
    quotes = db.query(Quote).all()
    db.close()

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