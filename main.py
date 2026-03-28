import streamlit as st
import pandas as pd
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                      clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email)
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM PRO v4.3", layout="wide")
init_db()

def get_status_color(status):
    colors = {"blue": "#D1E8FF", "yellow": "#FFF9C4", "red": "#FFCDD2", "white": "#F8F9FA"}
    return colors.get(status, "#F8F9FA")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state.get("role") == "superadmin":
        menu.append("Управление доступом")
    
    choice = st.sidebar.selectbox("Меню", menu)
    if st.sidebar.button("Выйти"): logout()

    # --- РАЗДЕЛ ЛИДЫ ---
    if choice == "Лиды":
        st.subheader("📋 Список лидов")
        
        search = st.text_input("🔍 Поиск", "")
        all_leads = get_leads(search if search else None)
        total_count = len(all_leads)
        
        st.info(f"📊 Всего лидов: **{total_count}**")

        # Настройки пагинации
        items_per_page = 50
        num_pages = (total_count // items_per_page) + (1 if total_count % items_per_page > 0 else 0)
        
        # КНОПКИ НАВИГАЦИИ (В начало / В конец)
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        if col_nav1.button("⏮ В начало"): st.session_state.page = 1
        if col_nav3.button("В конец ⏭"): st.session_state.page = num_pages

        if 'page' not in st.session_state: st.session_state.page = 1
        
        page = st.number_input("Текущая страница", min_value=1, max_value=max(1, num_pages), key="page")
        
        start_idx = (page - 1) * items_per_page
        current_leads = all_leads[start_idx : start_idx + items_per_page]

        for i, row in enumerate(current_leads):
            color = get_status_color(row['status_color'])
            order_num = start_idx + i + 1
            # 1. Форматирование даты
            date_str = row['created_at'].strftime("%d.%m.%Y %H:%M") if row['created_at'] else "---"
            
            st.markdown(f"""
                <div style="background-color:{color}; border-radius:8px; padding:6px 12px; margin-bottom:5px; border:1px solid #ddd; color:black;">
                    <span style="font-size: 12px; font-weight: bold;">#{order_num} | 📅 {date_str} | {row['full_name']} | {row['phone']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Детали"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                
                c4, c5, c6 = st.columns(3)
                curr_c = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
                curr_s = c5.selectbox("Статус", ["white", "blue", "yellow", "red"], 
                                     index=["white", "blue", "yellow", "red"].index(row['status_color']), key=f"s_{row['id']}")
                curr_src = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
                
                curr_comm = st.text_area("Комментарий", row['comment'] if row['comment'] else "", key=f"cm_{row['id']}")
                
                b_save, b_del = st.columns([1, 5])
                if b_save.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=n, phone=p, email=e, 
                                course_name=curr_c, status_color=curr_s, comment=curr_comm, source=curr_src)
                    st.rerun()
                
                if st.session_state.get("role") == "superadmin":
                    if b_del.button("🗑️ Удалить", key=f"del_{row['id']}"):
                        delete_lead(row['id']); st.rerun()

    # --- РАЗДЕЛ ДОБАВИТЬ ЛИД (ИСПРАВЛЕН) ---
    elif choice == "Добавить лид":
        st.subheader("➕ Новая запись")
        with st.form("manual_add_form", clear_on_submit=True):
            f_name = st.text_input("ФИО")
            f_phone = st.text_input("Телефон")
            f_email = st.text_input("Email")
            f_course = st.text_input("Курс")
            f_comm = st.text_area("Комментарий")
            submit = st.form_submit_button("Добавить в базу")
            
            if submit:
                if f_name and f_phone:
                    add_lead(f_name, f_phone, f_email, f_course, "Manual", f_comm)
                    st.success(f"Лид {f_name} успешно добавлен!")
                else:
                    st.error("Имя и телефон обязательны!")

    # --- РАЗДЕЛ ИМПОРТ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Инструменты")
        if st.session_state.get("role") == "superadmin":
            if st.button("🔥 ОЧИСТИТЬ БАЗУ"):
                clear_all_leads(); st.rerun()
        
        st.divider()
        up_file = st.file_uploader("Excel", type=["xlsx"])
        if up_file and st.button("🚀 ИМПОРТ"):
            df = pd.read_excel(up_file, header=None)
            for _, r in df.iterrows():
                v = list(r.values)
                if len(v) >= 3:
                    add_lead(str(v[1]), str(v[2]), str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel")
            st.success("Готово!"); st.rerun()

    # --- УПРАВЛЕНИЕ АДМИНАМИ ---
    elif choice == "Управление доступом" and st.session_state.get("role") == "superadmin":
        st.subheader("🔑 Доступ")
        new_mail = st.text_input("Email:")
        if st.button("Добавить"): add_allowed_email(new_mail); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1])
            c1.write(e)
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()