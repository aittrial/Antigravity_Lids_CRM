import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM ANTIGRAVITY v3.0", layout="wide")
init_db()

def get_status_color(status):
    colors = {"blue": "#ADD8E6", "yellow": "#FFFFE0", "red": "#FFB6C1", "white": "#FFFFFF"}
    return colors.get(status, "#FFFFFF")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    st.sidebar.info(f"Роль: {st.session_state.get('role')}")
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    choice = st.sidebar.selectbox("Меню", menu)
    if st.sidebar.button("Выйти"): logout()

    # --- СПИСОК ЛИДОВ ---
    if choice == "Лиды":
        st.subheader("📋 Управление лидами")
        leads = get_leads()
        st.write(f"Всего записей: **{len(leads)}**")
        
        for row in leads:
            # Цвет фона в зависимости от статуса
            bg = get_status_color(row['status_color'])
            
            with st.expander(f"{row['full_name']} | {row['phone']} | {row['course_name']}"):
                st.markdown(f'<div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #ccc;">', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                new_name = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                new_phone = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                new_email = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                
                c4, c5, c6 = st.columns(3)
                new_course = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
                new_status = c5.selectbox("Статус (цвет)", ["white", "blue", "yellow", "red"], 
                                         index=["white", "blue", "yellow", "red"].index(row['status_color']),
                                         key=f"s_{row['id']}")
                new_source = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
                
                new_comm = st.text_area("Комментарий", row['comment'], key=f"cm_{row['id']}")
                
                col_btn1, col_btn2 = st.columns([1, 5])
                if col_btn1.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=new_name, phone=new_phone, email=new_email, 
                                course_name=new_course, status_color=new_status, comment=new_comm, source=new_source)
                    st.success("Обновлено!")
                    st.rerun()
                
                if st.session_state.get("role") == "superadmin":
                    if col_btn2.button("🗑️ Удалить", key=f"del_{row['id']}"):
                        delete_lead(row['id'])
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- ДОБАВИТЬ ВРУЧНУЮ ---
    elif choice == "Добавить лид":
        st.subheader("➕ Новый лид")
        with st.form("manual_add"):
            n, p, e, c, s = st.text_input("Имя"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс"), st.text_input("Источник", value="Manual")
            comm = st.text_area("Комментарий")
            if st.form_submit_button("Добавить в базу"):
                add_lead(n, p, e, c, s, comment=comm)
                st.success("Лид добавлен!")
                st.rerun()

    # --- ИМПОРТ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт из Excel")
        up_file = st.file_uploader("Загрузите .xlsx", type=["xlsx"])
        if up_file:
            xl = pd.ExcelFile(up_file)
            sheet = 'Test' if 'Test' in xl.sheet_names else xl.sheet_names[0]
            df = pd.read_excel(up_file, sheet_name=sheet, header=None)
            st.dataframe(df.head(5))
            
            if st.button("🚀 ЗАПУСТИТЬ ПОЛНЫЙ ИМПОРТ"):
                count = 0
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    name, phone = str(v[1]).strip(), str(v[2]).strip()
                    if name.lower() in ['nan', 'name', 'имя', ''] or phone.lower() in ['nan', 'phone', '']: continue
                    
                    # Собираем все данные из колонок Excel
                    add_lead(
                        full_name=name,
                        phone=phone,
                        email=str(v[3]) if len(v) > 3 and pd.notna(v[3]) else '',
                        course_name=str(v[4]) if len(v) > 4 and pd.notna(v[4]) else '',
                        source=f"Import {sheet}",
                        comment=str(v[6]) if len(v) > 6 and pd.notna(v[6]) else ''
                    )
                    count += 1
                st.success(f"Готово! Загружено {count} лидов со всеми данными.")
                st.rerun()

if __name__ == "__main__":
    main()