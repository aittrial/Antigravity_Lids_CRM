import streamlit as st
import os
from database import get_connection

def check_password():
    """Возвращает True, если пароль верный и email разрешен."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в CRM")
    
    email_input = st.text_input("Email", key="login_email").lower().strip()
    password_input = st.text_input("Пароль", type="password", key="login_pass")

    if st.button("Войти"):
        # 1. Проверка главного пароля из секретов Railway
        if password_input == os.getenv("ADMIN_PASSWORD"):
            
            # 2. Ищем email в базе данных
            conn = get_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT role FROM allowed_emails WHERE email = %s", (email_input,))
                    result = cur.fetchone()
                    
                    if result:
                        # Email найден, забираем его роль
                        st.session_state["authenticated"] = True
                        st.session_state["user_email"] = email_input
                        st.session_state["role"] = result[0] # Роль из базы (admin/analyst/superadmin)
                        
                        # Если это твой личный мейл из секретов, даем superadmin
                        if email_input == os.getenv("ADMIN_EMAIL"):
                            st.session_state["role"] = "superadmin"
                        
                        st.success(f"Добро пожаловать, роль: {st.session_state['role']}")
                        st.rerun()
                    else:
                        st.error("🚫 Доступ запрещен: этого Email нет в списке разрешенных.")
                finally:
                    conn.close()
        else:
            st.error("🔑 Неверный пароль")
            
    return False

def logout():
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.rerun()