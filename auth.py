import streamlit as st
import os
from database import get_connection

def check_password():
    """Проверка входа: Суперадмин по паролю, сотрудники по Email."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
        st.session_state["role"] = None

    if st.session_state["authenticated"]:
        return True

    st.title("🔐 Вход в CRM")

    # Создаем две вкладки для разных типов входа
    tab_super, tab_staff = st.tabs(["🔑 Суперадмин", "📧 Сотрудник"])

    with tab_super:
        # Получаем пароль из переменных окружения
        correct_password = os.getenv("ADMIN_PASSWORD")
        
        master_pass = st.text_input("Введите мастер-пароль", type="password", key="super_pass_input")
        
        if st.button("Войти как Суперадмин", key="btn_super_auth"):
            if not correct_password:
                st.error("⚠️ Критическая ошибка: Пароль суперадмина не настроен в Railway (переменная ADMIN_PASSWORD пуста).")
            elif master_pass == correct_password:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "superadmin"
                st.success("Доступ разрешен (Superadmin)")
                st.rerun()
            else:
                st.error("❌ Неверный мастер-пароль")

    with tab_staff:
        email_in = st.text_input("Введите ваш рабочий Email", key="staff_email_input").lower().strip()
        
        if st.button("Войти по Email", key="btn_staff_auth"):
            if email_in:
                conn = get_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        # Ищем роль пользователя по его имейлу
                        cur.execute("SELECT role FROM allowed_emails WHERE email = %s", (email_in,))
                        result = cur.fetchone()
                        
                        if result and result[0]:
                            st.session_state["authenticated"] = True
                            st.session_state["role"] = str(result[0])
                            st.success(f"Доступ разрешен (Роль: {st.session_state['role']})")
                            st.rerun()
                        else:
                            st.error("🚫 Доступ запрещен: Email не найден в базе или роль не назначена.")
                    finally:
                        conn.close()
            else:
                st.warning("Пожалуйста, введите Email.")

    return False

def logout():
    """Сброс сессии при выходе."""
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.rerun()