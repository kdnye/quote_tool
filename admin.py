# admin.py
import streamlit as st
from db import Session, User
from sqlalchemy import text
import pandas as pd

def load_users():
    db = Session()
    users = db.query(User).all()
    db.close()
    return pd.DataFrame([{
        "ID": u.id,
        "Name": u.name,
        "Email": u.email,
        "Phone": u.phone,
        "Business": u.business_name,
        "Role": u.role,
        "Approved": u.is_approved,
        "Created": u.created_at.strftime("%Y-%m-%d")
    } for u in users])

def admin_panel():
    st.title("🛠️ Admin Panel")
    users_df = load_users()

    st.subheader("📋 All Users")
    st.dataframe(users_df)

    st.subheader("✅ Approve Users")
    pending = users_df[~users_df["Approved"]]
    if not pending.empty:
        uid = st.selectbox("Select user to approve", pending["ID"].tolist(), key="approve_user")
        if st.button("Approve"):
            db = Session()
            db.execute(text("UPDATE users SET is_approved = 1 WHERE id = :id"), {"id": uid})
            db.commit()
            db.close()
            st.success(f"User {uid} approved.")
            st.rerun()
    else:
        st.info("No pending users.")

    st.subheader("🔄 Change Roles")
    uid = st.selectbox("User ID", users_df["ID"].tolist(), key="change_user")
    new_role = st.selectbox("Role", ["user", "admin"], key="new_role")
    if st.button("Update Role"):
        db = Session()
        db.execute(text("UPDATE users SET role = :role WHERE id = :id"), {"role": new_role, "id": uid})
        db.commit()
        db.close()
        st.success(f"User {uid} role set to {new_role}.")
        st.rerun()

    st.subheader("🗑️ Delete User")
    uid_del = st.selectbox("Select user to delete", users_df["ID"].tolist(), key="delete_user")
    if st.button("Delete"):
        db = Session()
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid_del})
        db.commit()
        db.close()
        st.warning(f"User {uid_del} deleted.")
        st.rerun()
