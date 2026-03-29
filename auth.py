import streamlit as st
import os

def check_password():
    """Returns True if the user had the correct password."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "role" not in st.session_state:
        st.session_state["role"] = None
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None

    if st.session_state["authenticated"]:
        return True

    st.title("Leads_CRM - Авторизация")
    
    auth_mode = st.radio("Выберите способ входа:", ["Superadmin (Master Password)", "Admin (Email)"])

    if auth_mode == "Superadmin (Master Password)":
        password = st.text_input("Введите мастер-пароль:", type="password")
        if st.button("Войти как Superadmin"):
            master_pass = os.getenv("MASTER_PASSWORD", "crm_master_2026")
            if password == master_pass:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "superadmin"
                st.session_state["user_email"] = "superadmin@system.local"
                st.rerun()
            else:
                st.error("Неверный пароль")
    
    else:
        email = st.text_input("Введите ваш Email:")
        # For simplicity in this version, we check against the allowed_emails table
        # In a real app, you'd have a password or use Google OAuth
        if st.button("Войти как Admin"):
            from database import get_allowed_emails
            allowed = get_allowed_emails()
            if email in allowed:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "admin"
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Этот Email не имеет доступа. Обратитесь к Superadmin.")

    return False

def logout():
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.session_state["user_email"] = None
    st.rerun()
