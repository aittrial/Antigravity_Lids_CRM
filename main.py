import streamlit as st
import pandas as pd
import os
from database import init_db, get_leads, add_lead, update_lead, delete_lead, get_allowed_emails, add_allowed_email, delete_allowed_email
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM ANTIGRAVITY v2.5", layout="wide")
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
        st.write(f"Всего записей в базе: {len(leads)}")
        if not leads:
            st.info("Лидов пока нет.")
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
        st.subheader("➕ Новый лид")
        with st.form("manual_add"):
            n, p, e, c = st.text_input("Имя"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс")
            if st.form_submit_button("Добавить"):
                add_lead(n, p, e, c, "Manual")
                st.success("Добавлен!")
                st.rerun()

    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Импорт из Excel")
        up_file = st.file_uploader("Загрузите файл", type=["xlsx"])
        if up_file:
            xl = pd.ExcelFile(up_file)
            sheet = 'Test' if 'Test' in xl.sheet_names else xl.sheet_names[0]
            # Читаем без заголовков, чтобы видеть всё
            df = pd.read_excel(up_file, sheet_name=sheet, header=None)
            st.write(f"Лист: {sheet}")
            st.dataframe(df.head(10))
            
            if st.button("🚀 НАЧАТЬ ИМПОРТ"):
                count = 0
                for i, row in df.iterrows():
                    v = list(row.values)
                    if len(v) < 3: continue
                    
                    # Берем колонки B (индекс 1) и C (индекс 2)
                    name = str(v[1]).strip() if pd.notna(v[1]) else ""
                    phone = str(v[2]).strip() if pd.notna(v[2]) else ""
                    
                    # Пропуск заголовков
                    if name.lower() in ['nan', 'name', 'имя', ''] or phone.lower() in ['nan', 'phone', '']:
                        continue
                    
                    try:
                        add_lead(
                            full_name=name,
                            phone=phone,
                            email=str(v[3]) if len(v) > 3 and pd.notna(v[3]) else '',
                            course_name=str(v[4]) if len(v) > 4 and pd.notna(v[4]) else '',
                            source=f"Import {sheet}",
                            comment=str(v[6]) if len(v) > 6 and pd.notna(v[6]) else ''
                        )
                        count += 1
                    except:
                        continue
                
                if count > 0:
                    st.success(f"✅ Успешно! Добавлено лидов: {count}")
                    st.rerun()
                else:
                    st.error("❌ Данные не найдены. Проверьте колонки B и C в Excel.")

if __name__ == "__main__": main()