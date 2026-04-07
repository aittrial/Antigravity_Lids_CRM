import streamlit as st
import os
from database import get_connection

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["role"] = None

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в систему")

    tab1, tab2 = st.tabs(["🔑 Суперадмин", "📧 Сотрудник (Админ/Аналитик)"])

    with tab1:
        master_pass = st.text_input("Введите мастер-пароль", type="password", key="super_pass")
        if st.button("Войти как Суперадмин"):
            if master_pass == os.getenv("ADMIN_PASSWORD"):
                st.session_state["authenticated"] = True
                st.session_state["role"] = "superadmin"
                st.rerun()
            else:
                st.error("Неверный мастер-пароль")

    with tab2:
        email_input = st.text_input("Введите ваш Email", key="user_email_login").lower().strip()
        if st.button("Войти по Email"):
            if email_input:
                conn = get_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT role FROM allowed_emails WHERE email = %s", (email_input,))
                        res = cur.fetchone()
                        if res:
                            st.session_state["authenticated"] = True
                            st.session_state["role"] = res[0] # Роль подтянется автоматически (admin или analyst)
                            st.rerun()
                        else:
                            st.error("Email не найден в списке разрешенных")
                    finally:
                        conn.close()
            else:
                st.warning("Введите Email")
            
    return False

def logout():
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.rerun()