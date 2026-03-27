import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead, get_allowed_emails, add_allowed_email, delete_allowed_email
from auth import check_password, logout

# Initial Page Config
st.set_page_config(page_title="Lids_CRM ANTIGRAVITY v2.1", layout="wide")

# Ensure DB is initialized
init_db()

# Custom CSS for status colors
def get_status_color(status):
    colors = {
        "blue": "#ADD8E6", # Голубой: Лид передан
        "yellow": "#FFFFE0", # Желтый: Перезвонить
        "red": "#FFB6C1", # Красный: Отказ
        "white": "#FFFFFF"
    }
    return colors.get(status, "#FFFFFF")

def main():
    if not check_password():
        return

    # Sidebar
    st.sidebar.title(f"Lids_CRM v2.1")
    st.sidebar.info(f"Вход как: {st.session_state['role']} | {st.session_state['user_email']}")
    
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state["role"] == "superadmin":
        menu.append("Управление доступом")
    
    choice = st.sidebar.selectbox("Меню", menu)
    
    if st.sidebar.button("Выйти"):
        logout()

    # --- ЛИДЫ ---
    if choice == "Лиды":
        st.subheader("📋 Список лидов")
        
        leads = get_leads()
        if not leads:
            st.info("Лидов пока нет.")
        else:
            df = pd.DataFrame(leads)
            
            # Reorder columns for display
            cols = ["id", "full_name", "phone", "email", "course_name", "source", "status_color", "comment", "created_at"]
            df = df[cols]

            for index, row in df.iterrows():
                with st.expander(f"{row['full_name']} | {row['phone']} | {row['course_name']}"):
                    bg_color = get_status_color(row['status_color'])
                    st.markdown(f'<div style="background-color:{bg_color}; padding:10px; border-radius:5px;">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    new_name = col1.text_input("Имя", row['full_name'], key=f"name_{row['id']}")
                    new_phone = col2.text_input("Телефон", row['phone'], key=f"phone_{row['id']}")
                    new_email = col3.text_input("Email", row['email'], key=f"email_{row['id']}")
                    
                    col4, col5, col6 = st.columns(3)
                    new_course = col4.text_input("Курс", row['course_name'], key=f"course_{row['id']}")
                    new_status = col5.selectbox("Статус (цвет)", ["white", "blue", "yellow", "red"], 
                                              index=["white", "blue", "yellow", "red"].index(row['status_color']),
                                              key=f"status_{row['id']}")
                    new_source = col6.text_input("Источник", row['source'], key=f"source_{row['id']}")
                    
                    new_comment = st.text_area("Комментарий", row['comment'], key=f"comm_{row['id']}")
                    
                    if st.button("Сохранить изменения", key=f"save_{row['id']}"):
                        update_lead(row['id'], full_name=new_name, phone=new_phone, email=new_email, 
                                    course_name=new_course, status_color=new_status, comment=new_comment, source=new_source)
                        st.success("Обновлено!")
                        st.rerun()
                    
                    if st.session_state["role"] == "superadmin":
                        if st.button("❌ Удалить лид", key=f"del_{row['id']}"):
                            delete_lead(row['id'])
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- ДОБАВИТЬ ЛИД ---
    elif choice == "Добавить лид":
        st.subheader("➕ Добавить нового лида")
        with st.form("add_form"):
            f_name = st.text_input("ФИО")
            f_phone = st.text_input("Телефон")
            f_email = st.text_input("Email")
            f_course = st.text_input("Курс")
            f_source = st.text_input("Источник", value="Manual")
            f_comment = st.text_area("Комментарий")
            
            submitted = st.form_submit_button("Добавить")
            if submitted:
                if f_name or f_phone:
                    add_lead(f_name, f_phone, f_email, f_course, f_source, comment=f_comment)
                    st.success("Лид добавлен!")
                else:
                    st.error("Имя или телефон обязательны")

    # --- ИМПОРТ / ЭКСПОРТ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт лидов из Excel")
        uploaded_file = st.file_uploader("Выберите Excel файл", type=["xlsx", "xls", "csv"])
        
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                df_import = pd.read_csv(uploaded_file)
            else:
                df_import = pd.read_excel(uploaded_file)
            
            st.write("Предпросмотр данных:")
            st.dataframe(df_import.head())
            
            if st.button("Начать импорт"):
                count = 0
                for _, row in df_import.iterrows():
                    try:
                        # Сопоставляем заголовки из вашей вкладки "Test"
                        # Используем .get() и проверку на пустые значения (NaN)
                        name = row.get('Name', '')
                        phone = row.get('Phone', '')
                        email = row.get('Email', '')
                        course = row.get('City/Course', '')
                        comment = row.get('Comments', '')

                        # Пропускаем строки, где нет ни имени, ни телефона
                        if pd.isna(name) and pd.isna(phone):
                            continue

                        # Превращаем данные в строку, заменяя NaN на пустую строку
                        add_lead(
                            str(name) if pd.notna(name) else '', 
                            str(phone) if pd.notna(phone) else '', 
                            str(email) if pd.notna(email) else '',
                            str(course) if pd.notna(course) else '',
                            "Excel Import (Test)", # Источник
                            comment=str(comment) if pd.notna(comment) else '',
                            status_color='white'
                        )
                        count += 1
                    except Exception as e:
                        st.error(f"Ошибка в строке {count+1}: {e}")
                
                st.success(f"Импортировано {count} лидов!")
                st.rerun()

    # --- УПРАВЛЕНИЕ ДОСТУПОМ ---
    elif choice == "Управление доступом" and st.session_state["role"] == "superadmin":
        st.subheader("🔑 Управление разрешенными Email")
        
        new_email = st.text_input("Добавить новый Email:")
        if st.button("Добавить"):
            add_allowed_email(new_email)
            st.success(f"Email {new_email} добавлен.")
            st.rerun()
            
        allowed_emails = get_allowed_emails()
        st.write("Список разрешенных Email:")
        for email in allowed_emails:
            col1, col2 = st.columns([4, 1])
            col1.write(email)
            if col2.button("Удалить", key=email):
                delete_allowed_email(email)
                st.rerun()

if __name__ == "__main__":
    main()