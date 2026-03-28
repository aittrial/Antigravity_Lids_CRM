import streamlit as st
import pandas as pd
import os
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                      clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email)
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM v3.6 PRO", layout="wide")
init_db()

def get_status_color(status):
    colors = {"blue": "#ADD8E6", "yellow": "#FFFFE0", "red": "#FFB6C1", "white": "#F0F2F6"}
    return colors.get(status, "#F0F2F6")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    st.sidebar.info(f"Роль: {st.session_state.get('role')}")
    
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state.get("role") == "superadmin":
        menu.append("Управление доступом")
    
    choice = st.sidebar.selectbox("Меню", menu)
    if st.sidebar.button("Выйти"): logout()

    if choice == "Лиды":
        st.subheader("📋 Список лидов")
        leads = get_leads()
        
        # Стилизация экспандеров через CSS
        for row in leads:
            color = get_status_color(row['status_color'])
            # Уникальный стиль для каждого лида
            st.markdown(f"""
                <style>
                div[data-indexed-key="expander-{row['id']}"] {{
                    background-color: {color};
                    border-radius: 10px;
                    margin-bottom: 10px;
                }}
                </style>
            """, unsafe_allow_html=True)
            
            with st.expander(f"👤 {row['full_name']} | 📞 {row['phone']} | 📚 {row['course_name']}", expanded=False):
                st.container()
                st.markdown(f'<div style="background-color:{color}; padding:15px; border-radius:10px; color:black;">', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                
                c4, c5, c6 = st.columns(3)
                curr_c = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
                curr_s = c5.selectbox("Цвет статуса", ["white", "blue", "yellow", "red"], 
                                     index=["white", "blue", "yellow", "red"].index(row['status_color']), key=f"s_{row['id']}")
                curr_src = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
                
                curr_comm = st.text_area("Комментарий", row['comment'], key=f"cm_{row['id']}")
                
                b1, b2 = st.columns([1, 5])
                if b1.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=n, phone=p, email=e, 
                                course_name=curr_c, status_color=curr_s, comment=curr_comm, source=curr_src)
                    st.rerun()
                
                if st.session_state.get("role") == "superadmin":
                    if b2.button("🗑️ Удалить", key=f"del_{row['id']}"):
                        delete_lead(row['id']); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    elif choice == "Добавить лид":
        st.subheader("➕ Новый лид")
        with st.form("manual"):
            n, p, e, c = st.text_input("Имя"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс")
            comm = st.text_area("Комментарий")
            if st.form_submit_button("Добавить"):
                add_lead(n, p, e, c, "Manual", comment=comm); st.success("Добавлен!"); st.rerun()

    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Инструменты")
        if st.session_state.get("role") == "superadmin":
            if st.button("🔥 ОЧИСТИТЬ ВСЮ БАЗУ"):
                clear_all_leads(); st.rerun()
        
        st.divider()
        up_file = st.file_uploader("Excel", type=["xlsx"])
        if up_file:
            df = pd.read_excel(up_file, sheet_name=0, header=None)
            if st.button("🚀 ИМПОРТ"):
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    name, phone = str(v[1]).strip(), str(v[2]).strip()
                    if name.lower() in ['nan', ''] or phone.lower() in ['nan', '']: continue
                    add_lead(name, phone, str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel", str(v[6]) if len(v)>6 else '')
                st.rerun()

    elif choice == "Управление доступом" and st.session_state.get("role") == "superadmin":
        st.subheader("🔑 Доступ")
        new_mail = st.text_input("Email:")
        if st.button("Добавить"):
            add_allowed_email(new_mail); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1])
            c1.write(e)
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()