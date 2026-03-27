import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead, get_allowed_emails, add_allowed_email, delete_allowed_email
from auth import check_password, logout

# Настройка страницы
st.set_page_config(page_title="Lids_CRM ANTIGRAVITY v2.1", layout="wide")

# Инициализация БД
init_db()

# Цвета статусов
def get_status_color(status):
    colors = {
        "blue": "#ADD8E6", 
        "yellow": "#FFFFE0", 
        "red": "#FFB6C1", 
        "white": "#FFFFFF"
    }
    return colors.get(status, "#FFFFFF")

def main():
    if not check_password():
        return

    # Боковая панель
    st.sidebar.title(f"Lids_CRM v2.1")
    st.sidebar.info(f"Вход как: {st.session_state['role']}")
    
    menu = ["Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state["role"] == "superadmin":
        menu.append("Управление доступом")
    
    choice = st.sidebar.selectbox("Меню", menu)
    
    if st.sidebar.button("Выйти"):
        logout()

    # --- РАЗДЕЛ: ЛИДЫ ---
    if choice == "Лиды":
        st.subheader("📋 Список лидов")
        leads = get_leads()
        if not leads:
            st.info("Лидов пока нет.")
        else:
            df = pd.DataFrame(leads)
            cols = ["id", "full_name", "phone", "email", "course_name", "source", "status_color", "comment", "created_at"]
            df = df[cols]

            for index, row in df.iterrows():
                with st.expander(f"{row['full_name']} | {row['phone']} | {row['course_name']}"):
                    bg_color = get_status_color(row['status_color'])
                    st.markdown(f'<div style="background-color:{bg_color}; padding:10px; border-radius:5px;">', unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    new_name = c1.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
                    new_phone = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
                    new_email = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
                    
                    c4, c5, c6 = st.columns(3)
                    new_course = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
                    new_status = c5.selectbox("Статус", ["white", "blue", "yellow", "red"], 
                                              index=["white", "blue", "yellow", "red"].index(row['status_color']),
                                              key=f"s_{row['id']}")
                    new_source = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
                    
                    new_comment = st.text_area("Комментарий", row['comment'], key=f"cm_{row['id']}")
                    
                    if st.button("Сохранить", key=f"sv_{row['id']}"):
                        update_lead(row['id'], full_name=new_name, phone=new_phone, email=new_email, 
                                    course_name=new_course, status_color=new_status, comment=new_comment, source=new_source)
                        st.success("Обновлено!")
                        st.rerun()
                    
                    if st.session_state["role"] == "superadmin":
                        if st.button("❌ Удалить", key=f"dl_{row['id']}"):
                            delete_lead(row['id'])
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- РАЗДЕЛ: ДОБАВИТЬ ЛИД ---
    elif choice == "Добавить лид":
        st.subheader("➕ Новый лид")
        with st.form("add_f"):
            f_n = st.text_input("ФИО")
            f_p = st.text_input("Телефон")
            f_e = st.text_input("Email")
            f_c = st.text_input("Курс")
            f_s = st.text_input("Источник", value="Manual")
            f_comm = st.text_area("Комментарий")
            if st.form_submit_button("Добавить"):
                if f_n or f_p:
                    add_lead(f_n, f_p, f_e, f_c, f_s, comment=f_comm)
                    st.success("Лид добавлен!")
                else:
                    st.error("Нужно имя или телефон")

    # --- РАЗДЕЛ: ИМПОРТ (ФИНАЛЬНАЯ ВЕРСИЯ) ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт из Excel")
        up_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])
        
        if up_file:
            try:
                xl = pd.ExcelFile(up_file)
                t_sheet = 'Test' if 'Test' in xl.sheet_names else xl.sheet_names[0]
                # Читаем как есть, без заголовков, чтобы видеть всё
                df_import = pd.read_excel(up_file, sheet_name=t_sheet, header=None)
                
                st.write(f"Лист: **{t_sheet}**")
                st.dataframe(df_import.head(10)) # Показываем первые 10 строк
                
                if st.button("🚀 НАЧАТЬ ИМПОРТ"):
                    count = 0
                    for index, row in df_import.iterrows():
                        vals = row.values
                        # Пропускаем строку, если она слишком короткая
                        if len(vals) < 3: continue
                        
                        # Пропускаем технические строки и заголовки
                        name_val = str(vals[1])
                        if name_val.lower() in ['nan', 'name', 'имя', 'фио', '']: continue
                        
                        try:
                            # Берем данные по индексам колонок (1-Имя, 2-Телефон, 3-Email, 4-Курс, 6-Коммент)
                            name = str(vals[1]).strip()
                            phone = str(vals[2]).strip()
                            email = str(vals[3]).strip() if len(vals) > 3 else ""
                            course = str(vals[4]).strip() if len(vals) > 4 else ""
                            comment = str(vals[6]).strip() if len(vals) > 6 else ""

                            # Чистим от NaN
                            name = "" if name.lower() == "nan" else name
                            phone = "" if phone.lower() == "nan" else phone
                            email = "" if email.lower() == "nan" else email
                            course = "" if course.lower() == "nan" else course
                            comment = "" if comment.lower() == "nan" else comment

                            if name or phone:
                                add_lead(name, phone, email, course, f"Import {t_sheet}", comment=comment)
                                count += 1
                        except:
                            continue
                    
                    if count > 0:
                        st.success(f"✅ ПОБЕДА! Импортировано {count} лидов!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Лиды не найдены. Проверьте, что во втором столбце есть имена.")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    # --- УПРАВЛЕНИЕ ДОСТУПОМ ---
    elif choice == "Управление доступом" and st.session_state["role"] == "superadmin":
        st.subheader("🔑 Доступ")
        new_e = st.text_input("Новый Email:")
        if st.button("Добавить"):
            add_allowed_email(new_e)
            st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1])
            c1.write(e)
            if c2.button("Удалить", key=e):
                delete_allowed_email(e)
                st.rerun()

if __name__ == "__main__":
    main()