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
    tab1, tab2 = st.tabs(["🔑 Суперадмин", "📧 Сотрудник"])

    with tab1:
        # Уникальный ключ для суперадмина
        master_pass = st.text_input("Мастер-пароль", type="password", key="super_pass_field")
        if st.button("Войти как Суперадмин", key="super_btn"):
            if master_pass == os.getenv("ADMIN_PASSWORD"):
                st.session_state["authenticated"] = True
                st.session_state["role"] = "superadmin"
                st.rerun()
            else:
                st.error("Неверный пароль")

    with tab2:
        email_in = st.text_input("Ваш Email", key="email_field").lower().strip()
        if st.button("Войти по Email", key="email_btn"):
            if email_in:
                conn = get_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT role FROM allowed_emails WHERE email = %s", (email_in,))
                        res = cur.fetchone()
                        if res and res[0]: # Проверяем, что результат есть и роль не пустая
                            st.session_state["authenticated"] = True
                            st.session_state["role"] = str(res[0])
                            st.rerun()
                        else:
                            st.error("Email не найден или роль не назначена")
                    finally:
                        conn.close()
            else:
                st.warning("Введите Email")
    return False

def logout():
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.rerun()