import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead, clear_all_leads
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM v3.2", layout="wide")
init_db()

def get_status_color(status):
    colors = {"blue": "#ADD8E6", "yellow": "#FFFFE0", "red": "#FFB6C1", "white": "#FFFFFF"}
    return colors.get(status, "#FFFFFF")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    choice = st.sidebar.selectbox("Меню", menu)
    if st.sidebar.button("Выйти"): logout()

    if choice == "Лиды":
        st.subheader("📋 Управление лидами")
        leads = get_leads()
        st.write(f"Всего записей: **{len(leads)}**")
        for row in leads:
            bg = get_status_color(row['status_color'])
            with st.expander(f"👤 {row['full_name']} | 📞 {row['phone']} | 📚 {row['course_name']}"):
                st.markdown(f'<div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #ddd; color: black;">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                new_n = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                new_p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                new_e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                b1, b2 = st.columns([1, 5])
                if b1.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=new_n, phone=new_p, email=new_e)
                    st.rerun()
                if st.session_state.get("role") == "superadmin":
                    if b2.button("🗑️ Удалить", key=f"del_{row['id']}"):
                        delete_lead(row['id'])
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    elif choice == "Добавить лид":
        st.subheader("➕ Новый лид")
        with st.form("manual"):
            n, p, e, c = st.text_input("Имя"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс")
            if st.form_submit_button("Добавить"):
                add_lead(n, p, e, c, "Manual")
                st.success("Добавлен!")
                st.rerun()

    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт и Очистка")
        
        if st.session_state.get("role") == "superadmin":
            st.warning("⚠️ Опасная зона")
            
            # Логика подтверждения удаления
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = False

            if not st.session_state.confirm_delete:
                if st.button("🔥 ОЧИСТИТЬ ВСЮ БАЗУ ДАННЫХ"):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.error("ВЫ УВЕРЕНЫ? Это действие нельзя отменить!")
                col1, col2 = st.columns(2)
                if col1.button("✅ ДА, УДАЛИТЬ ВСЁ"):
                    clear_all_leads()
                    st.session_state.confirm_delete = False
                    st.success("База полностью очищена!")
                    st.rerun()
                if col2.button("❌ ОТМЕНА"):
                    st.session_state.confirm_delete = False
                    st.rerun()
        
        st.divider()
        
        up_file = st.file_uploader("Загрузите .xlsx", type=["xlsx"])
        if up_file:
            df = pd.read_excel(up_file, sheet_name=0, header=None)
            st.dataframe(df.head(5))
            if st.button("🚀 НАЧАТЬ ИМПОРТ"):
                count = 0
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    name, phone = str(v[1]).strip(), str(v[2]).strip()
                    if name.lower() in ['nan', 'name', ''] or phone.lower() in ['nan', 'phone', '']: continue
                    add_lead(name, phone, str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel", str(v[6]) if len(v)>6 else '')
                    count += 1
                st.success(f"Загружено: {count}")
                st.rerun()

if __name__ == "__main__":
    main()