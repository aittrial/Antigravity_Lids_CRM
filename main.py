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
        st.subheader("📋 Список Лидов")
        
        leads = get_leads()
        if leads:
            df = pd.DataFrame(leads)
            
            # Formatting for WhatsApp
            def format_whatsapp(phone):
                if not phone: return ""
                clean_phone = "".join(filter(str.isdigit, str(phone)))
                return f"https://wa.me/{clean_phone}"
            
            df['WhatsApp'] = df['phone'].apply(format_whatsapp)
            
            # Display configuration
            cols_to_show = ["id", "full_name", "phone", "email", "course_name", "source", "callback_time", "comment", "status_color", "WhatsApp"]
            
            # Search
            search_query = st.text_input("Поиск (Имя, Телефон, Комментарий...):")
            if search_query:
                mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                df = df[mask]
                
            # Column configuration
            st.data_editor(
                df[cols_to_show],
                column_config={
                    "WhatsApp": st.column_config.LinkColumn("WhatsApp Chat", width="small"),
                    "status_color": st.column_config.SelectboxColumn(
                        "Статус (Цвет)",
                        options=["white", "blue", "yellow", "red"],
                        required=True
                    )
                },
                disabled=["id", "created_at"],
                hide_index=True,
                key="leads_editor",
                use_container_width=True
            )
            
            if st.button("Сохранить изменения"):
                # Handle updates from data_editor
                # Note: st.session_state.leads_editor contains 'edited_rows'
                edits = st.session_state.leads_editor.get("edited_rows", {})
                for row_idx, changes in edits.items():
                    lead_id = df.iloc[int(row_idx)]["id"]
                    update_lead(lead_id, **changes)
                st.success("Изменения сохранены!")
                st.rerun()

        else:
            st.info("Лидов пока нет.")

    # --- ДОБАВИТЬ ЛИД ---
    elif choice == "Добавить лид":
        st.subheader("➕ Создать нового Лида")
        with st.form("new_lead_form"):
            full_name = st.text_input("ФИО / Full Name (RU/EN/HE)")
            phone = st.text_input("Телефон / Phone")
            email = st.text_input("Email")
            course_name = st.text_input("Название курса")
            source = st.selectbox("Источник", ["Google", "Facebook", "Telegram", "Другое"])
            callback_time = st.date_input("Дата звонка")
            comment = st.text_area("Комментарий")
            status_color = st.selectbox("Статус (Цвет)", ["white", "blue", "yellow", "red"])
            
            submitted = st.form_submit_button("Сохранить")
            if submitted:
                try:
                    add_lead(full_name, phone, email, course_name, source, callback_time, comment, status_color)
                    st.success(f"Лид {full_name} успешно добавлен!")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    # --- ИМПОРТ / ЭКСПОРТ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("💾 Работа с Excel")
        
        # Export
        if st.button("Скачать всех Лидов (Excel)"):
            leads = get_leads()
            if leads:
                df_export = pd.DataFrame(leads)
                output = pd.ExcelWriter("leads_export.xlsx", engine='xlsxwriter')
                df_export.to_excel(output, index=False, sheet_name='Leads')
                output.close()
                with open("leads_export.xlsx", "rb") as f:
                    st.download_button("Нажмите здесь для загрузки", f, "leads_export.xlsx")
            else:
                st.warning("Нет данных для экспорта.")
        
        st.divider()
        
        # Import
        uploaded_file = st.file_uploader("Загрузить лидов из Excel", type=["xlsx"])
        if uploaded_file:
            df_import = pd.read_excel(uploaded_file)
            st.write("Предпросмотр данных:")
            st.dataframe(df_import.head())
            if st.button("Начать импорт"):
                count = 0
                for _, row in df_import.iterrows():
                    try:
                        add_lead(
                            row.get('full_name', ''), 
                            str(row.get('phone', '')), 
                            row.get('email', ''),
                            row.get('course_name', ''),
                            row.get('source', ''),
                            comment=row.get('comment', ''),
                            status_color=row.get('status_color', 'white')
                        )
                        count += 1
                    except Exception as e:
                        st.error(f"Ошибка в строке {count+1}: {e}")
                st.success(f"Импортировано {count} лидов!")

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
