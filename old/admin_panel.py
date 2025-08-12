import streamlit as st
from sqlalchemy import text  
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd

# --- DB Setup ---
DB_PATH = "sqlite:///app.db"  # Unified path
engine = create_engine(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

# --- Functions ---
def load_users():
    df = pd.read_sql("""
        SELECT id, name, email, phone, business_name, business_phone, role, is_approved, created_at 
        FROM users
    """, con=engine)
    df.columns = df.columns.str.strip().str.lower()
    return df

def approve_user(user_id):
    session.execute(text("UPDATE users SET is_approved = 1 WHERE id = :id"), {"id": user_id})

    session.commit()

def change_role(user_id, new_role):
    session.execute(
        text("UPDATE users SET role = :role WHERE id = :id"),
        {"role": new_role, "id": user_id}
)
    session.commit()

# --- UI ---
st.title("👤 Admin Panel")
users_df = load_users()

st.subheader("📋 Registered Users")
st.dataframe(users_df)

st.subheader("✅ Approve User")
pending_df = users_df[~users_df['is_approved'].astype(bool)]
if not pending_df.empty:
    user_to_approve = st.selectbox("Select user ID to approve", pending_df['id'].tolist(), key="approve_user")
    if st.button("Approve"):
        approve_user(user_to_approve)
        st.success(f"User {user_to_approve} approved.")
        st.rerun()
else:
    st.info("No users awaiting approval.")

st.subheader("🔄 Change User Role")
if not users_df.empty:
    user_to_change = st.selectbox("Select user ID to change role", users_df['id'].tolist(), key="change_role_user")
    new_role = st.selectbox("Select new role", ["user", "admin"])
    if st.button("Change Role"):
        change_role(user_to_change, new_role)
        st.success(f"User {user_to_change} role updated to {new_role}.")
        st.rerun()
else:
    st.warning("No users found in the system.")
