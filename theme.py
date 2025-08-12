# File: theme.py
import streamlit as st

def inject_fsi_theme():
    st.markdown("""
        <style>
            body {
                background-color: #a0a0a0;
                color: #FFFFFF;
            }
            .stApp {
                background-color: #a0a0a0;
                color: #FFFFFF;
            }
            .stButton>button {
                background-color: #005B99;
                color: white;
                border-radius: 6px;
                padding: 0.5em 1em;
                font-weight: 600;
            }
            .stButton>button:hover {
                background-color: #003366;
            }
            .stRadio > div {
                color: #FFFFFF;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #FFFFFF;
            }
            .stCheckbox > label, .stTextInput > div > label, .stNumberInput > div > label {
                color: #FFFFFF;
                font-weight: 500;
            }
            .stSubheader, .stMarkdown {
                color: #FFFFFF;
            }
        </style>
    """, unsafe_allow_html=True)