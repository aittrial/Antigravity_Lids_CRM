import streamlit as st
import pandas as pd
import os
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                      clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email)
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM v4.0 Final", layout="wide")
init_db()

def get_status_color(status):
    colors = {
        "blue": "#D1E8FF", 
        "yellow": "#FFF9C4", 
        "red": "#FFCDD2", 
        "white": "#F0F2F6"
    }
    return colors.get(status, "#F0F2F6")

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
        leads = get_leads()
        
        for i, row in enumerate(leads):
            color = get_status_color(row['status_color'])
            order_num = i + 1
            
            # РЕШЕНИЕ ДЛЯ ОКРАШИВАНИЯ ВСЕГО БЛОКА
            st.markdown(f"""
                <div style="background-color:{color}; border-radius:10px; padding:10px; margin-bottom:15px; border:1px solid #ddd; color:black;">
                <h4 style="margin:0; padding-bottom:10px;">#{order_num} | {row['full_name']} | {row['phone']}</h4>
            """, unsafe_allow_html=True)
            
            with st.expander("Детали лида и управление"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                
                c4, c5, c6 = st.columns(3)
                curr_c = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
                curr_s = c5.selectbox("Цвет", ["white", "blue", "yellow", "red"], 
                                     index=["white", "blue", "yellow", "red"].index(row['status_color']), key=f"s_{row['id']}")
                curr_src = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
                
                curr_comm = st.text_area("Комментарий", row['comment'] if row['comment'] else "", key=f"cm_{row['id']}")
                
                b1, b2 = st.columns([1, 5])
                if b1.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=n, phone=p, email=e, 
                                course_name=curr_c, status_color=curr_s, comment=curr_comm, source=curr_src)
                    st.rerun()
                
                if st.session_state.get("role") == "superadmin":
                    if b2.button("🗑️ Удалить", key=f"del_{row['id']}"):
                        delete_lead(row['id']); st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

    # --- РАЗДЕЛ ИМПОРТ / ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Инструменты")
        
        if st.session_state.get("role") == "superadmin":
            st.warning("⚠️ Опасная зона")
            
            if 'confirm_clear' not in st.session_state:
                st.session_state.confirm_clear = False

            if not st.session_state.confirm_clear:
                if st.button("🔥 ОЧИСТИТЬ ВСЮ БАЗУ ДАННЫХ"):
                    st.session_state.confirm_clear = True
                    st.rerun()
            else:
                st.error("ВЫ УВЕРЕНЫ? Данные будут удалены навсегда!")
                col_y, col_n = st.columns(2)
                if col_y.button("✅ ДА, Я УВЕРЕН"):
                    clear_all_leads()
                    st.session_state.confirm_clear = False
                    st.success("База очищена!")
                    st.rerun()
                if col_n.button("❌ ОТМЕНА"):
                    st.session_state.confirm_clear = False
                    st.rerun()
        
        st.divider()
        up_file = st.file_uploader("Загрузить .xlsx", type=["xlsx"])
        if up_file:
            df = pd.read_excel(up_file, sheet_name=0, header=None)
            if st.button("🚀 НАЧАТЬ ИМПОРТ"):
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    name, phone = str(v[1]).strip(), str(v[2]).strip()
                    if name.lower() in ['nan', ''] or phone.lower() in ['nan', '']: continue
                    add_lead(name, phone, str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel", str(v[6]) if len(v)>6 else '')
                st.success("Импорт завершен!")
                st.rerun()

    # --- УПРАВЛЕНИЕ АДМИНАМИ ---
    elif choice == "Управление доступом" and st.session_state.get("role") == "superadmin":
        st.subheader("🔑 Доступ")
        new_mail = st.text_input("Email:")
        if st.button("Добавить"):
            add_allowed_email(new_mail); st.rerun()
        
        st.divider()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1])
            c1.write(e)
            if c2.button("Удалить", key=e):
                delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()