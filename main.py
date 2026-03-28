import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead, get_allowed_emails, add_allowed_email, delete_allowed_email
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM FINAL DIAGNOSTIC", layout="wide")

# Принудительная инициализация при каждом запуске
init_db()

def get_status_color(status):
    colors = {"blue": "#ADD8E6", "yellow": "#FFFFE0", "red": "#FFB6C1", "white": "#FFFFFF"}
    return colors.get(status, "#FFFFFF")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state.get("role") == "superadmin": menu.append("Управление доступом")
    choice = st.sidebar.selectbox("Меню", menu)
    
    if st.sidebar.button("Выйти"): logout()

    if choice == "Лиды":
        st.subheader("📋 Список лидов")
        leads = get_leads()
        st.write(f"Записей в базе найдено: **{len(leads)}**")
        
        if not leads:
            st.info("В базе данных пока нет лидов.")
        else:
            df = pd.DataFrame(leads)
            for index, row in df.iterrows():
                with st.expander(f"{row['full_name']} | {row['phone']} | {row['course_name']}"):
                    st.markdown(f'<div style="background-color:{get_status_color(row["status_color"])}; padding:10px; border-radius:5px;">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    un_name = c1.text_input("Имя", str(row['full_name']), key=f"n_{row['id']}")
                    un_phone = c2.text_input("Телефон", str(row['phone']), key=f"p_{row['id']}")
                    un_email = c3.text_input("Email", str(row['email']), key=f"e_{row['id']}")
                    if st.button("Сохранить", key=f"sv_{row['id']}"):
                        update_lead(row['id'], full_name=un_name, phone=un_phone, email=un_email)
                        st.success("Обновлено!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    elif choice == "Добавить лид":
        st.subheader("➕ Ручное добавление (ТЕСТ СВЯЗИ)")
        with st.form("manual_form"):
            n = st.text_input("Имя")
            p = st.text_input("Телефон")
            e = st.text_input("Email")
            c = st.text_input("Курс")
            if st.form_submit_button("СОХРАНИТЬ В БАЗУ"):
                if n or p:
                    success = add_lead(n, p, e, c, "Manual Test")
                    if success:
                        st.success("✅ Лид добавлен! Проверьте вкладку 'Лиды'")
                else:
                    st.error("Заполните имя или телефон")

    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт из Excel")
        up_file = st.file_uploader("Загрузите файл", type=["xlsx"])
        if up_file:
            xl = pd.ExcelFile(up_file)
            sheet = 'Test' if 'Test' in xl.sheet_names else xl.sheet_names[0]
            df = pd.read_excel(up_file, sheet_name=sheet, header=None)
            st.write(f"Лист: {sheet}")
            st.dataframe(df.head(5))
            
            if st.button("🚀 НАЧАТЬ ИМПОРТ"):
                count = 0
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    
                    name = str(v[1]).strip() if pd.notna(v[1]) else ""
                    phone = str(v[2]).strip() if pd.notna(v[2]) else ""
                    
                    if name.lower() in ['nan', 'name', 'имя', ''] or phone.lower() in ['nan', 'phone', '']:
                        continue
                    
                    if add_lead(name, phone, source=f"Excel {sheet}"):
                        count += 1
                
                if count > 0:
                    st.success(f"✅ Успешно импортировано: {count}")
                    st.rerun()
                else:
                    st.error("❌ Данные не найдены или ошибка в файле.")

if __name__ == "__main__": main()