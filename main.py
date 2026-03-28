import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                      clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email)
from auth import check_password, logout

st.set_page_config(page_title="Lids_CRM Analytics v5.0", layout="wide")
init_db()

def get_status_color(status):
    colors = {"blue": "#D1E8FF", "yellow": "#FFF9C4", "red": "#FFCDD2", "white": "#F8F9FA"}
    return colors.get(status, "#F8F9FA")

def main():
    if not check_password(): return

    st.sidebar.title("CRM ANTIGRAVITY")
    menu = ["Аналитика", "Лиды", "Добавить лид", "Импорт/Экспорт"]
    if st.session_state.get("role") == "superadmin":
        menu.append("Управление доступом")
    
    choice = st.sidebar.selectbox("Меню", menu)
    if st.sidebar.button("Выйти"): logout()

    # --- ПРЕДВАРИТЕЛЬНАЯ ЗАГРУЗКА ДАННЫХ ДЛЯ ФИЛЬТРОВ ---
    today = date.today()
    default_start = today - timedelta(days=30)
    
    # --- РАЗДЕЛ АНАЛИТИКА ---
    if choice == "Аналитика":
        st.header("📊 Дашборд аналитики")
        
        # Фильтр дат для дашборда
        d_range = st.date_input("Период анализа", value=(default_start, today))
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (default_start, today)
        
        data = get_leads(None, st_d, en_d)
        if not data:
            st.warning("Нет данных за выбранный период")
        else:
            df = pd.DataFrame(data)
            
            # 1. Метрики (карточки)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Всего лидов", len(df))
            m2.metric("🔵 В работе", len(df[df['status_color'] == 'blue']))
            m3.metric("🟡 Ожидание", len(df[df['status_color'] == 'yellow']))
            m4.metric("🔴 Отказ", len(df[df['status_color'] == 'red']))
            
            st.divider()
            
            col_left, col_right = st.columns(2)
            
            # 2. График распределения по статусам
            fig_status = px.pie(df, names='status_color', title="Распределение по статусам",
                                color='status_color',
                                color_discrete_map={'blue':'#D1E8FF','yellow':'#FFF9C4','red':'#FFCDD2','white':'#F8F9FA'})
            col_left.plotly_chart(fig_status, use_container_width=True)
            
            # 3. Динамика по дням
            df['day'] = pd.to_datetime(df['created_at']).dt.date
            df_counts = df.groupby('day').size().reset_index(name='counts')
            fig_date = px.line(df_counts, x='day', y='counts', title="Поступление лидов по дням", markers=True)
            col_right.plotly_chart(fig_date, use_container_width=True)

    # --- РАЗДЕЛ ЛИДЫ ---
    elif choice == "Лиды":
        st.subheader("📋 Список лидов")
        
        with st.expander("🛠️ Фильтры и Поиск", expanded=True):
            f1, f2 = st.columns([2, 2])
            search = f1.text_input("🔍 Поиск", "")
            d_range = f2.date_input("📅 Период", value=(default_start, today))
        
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        all_leads = get_leads(search if search else None, st_d, en_d)
        total_count = len(all_leads)
        
        st.info(f"📊 Найдено: **{total_count}**")

        items_per_page = 50
        num_pages = max(1, (total_count // items_per_page) + (1 if total_count % items_per_page > 0 else 0))
        
        if 'page' not in st.session_state: st.session_state.page = 1
        c_nav1, _, c_nav3 = st.columns([1, 2, 1])
        if c_nav1.button("⏮ В начало"): st.session_state.page = 1
        if c_nav3.button("В конец ⏭"): st.session_state.page = num_pages

        page = st.number_input("Страница", min_value=1, max_value=num_pages, key="page")
        start_idx = (page - 1) * items_per_page
        current_leads = all_leads[start_idx : start_idx + items_per_page]

        for i, row in enumerate(current_leads):
            color = get_status_color(row['status_color'])
            date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
            
            st.markdown(f"""
                <div style="background-color:{color}; border-radius:8px; padding:6px 12px; margin-bottom:5px; border:1px solid #ddd; color:black;">
                    <span style="font-size: 12px; font-weight: bold;">#{start_idx+i+1} | 📅 {date_s} | {row['full_name']} | {row['phone']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Детали"):
                # Кнопка WhatsApp
                clean_phone = ''.join(filter(str.isdigit, str(row['phone'])))
                st.markdown(f'''<a href="https://wa.me/{clean_phone}" target="_blank">
                    <button style="background-color:#25D366; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">
                    💬 Написать в WhatsApp</button></a>''', unsafe_allow_html=True)
                
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
                
                bs, bd = st.columns([1, 5])
                if bs.button("💾 Сохранить", key=f"sv_{row['id']}"):
                    update_lead(row['id'], full_name=n, phone=p, email=e, 
                                course_name=curr_c, status_color=curr_s, comment=curr_comm, source=curr_src)
                    st.rerun()
                if st.session_state.get("role") == "superadmin" and bd.button("🗑️ Удалить", key=f"del_{row['id']}"):
                    delete_lead(row['id']); st.rerun()

    # --- РАЗДЕЛ ДОБАВИТЬ ЛИД ---
    elif choice == "Добавить лид":
        st.subheader("➕ Новая запись")
        with st.form("manual_add", clear_on_submit=True):
            f_n, f_p, f_e, f_c = st.text_input("ФИО"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс")
            f_cm = st.text_area("Комментарий")
            if st.form_submit_button("Добавить"):
                if f_n and f_p:
                    add_lead(f_n, f_p, f_e, f_c, "Manual", f_cm); st.success("Добавлено!")
                else: st.error("Заполните Имя и Телефон")

    # --- РАЗДЕЛ ИМПОРТ ---
    elif choice == "Импорт/Экспорт":
        st.subheader("📂 Инструменты")
        if st.session_state.get("role") == "superadmin" and st.button("🔥 ОЧИСТИТЬ БАЗУ"):
            clear_all_leads(); st.rerun()
        
        st.divider()
        up = st.file_uploader("Excel", type=["xlsx"])
        if up and st.button("🚀 ИМПОРТ"):
            df_up = pd.read_excel(up, header=None)
            for _, r in df_up.iterrows():
                v = list(r.values)
                if len(v) >= 3:
                    add_lead(str(v[1]), str(v[2]), str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel")
            st.success("Готово!"); st.rerun()

    # --- АДМИНЫ ---
    elif choice == "Управление доступом" and st.session_state.get("role") == "superadmin":
        st.subheader("🔑 Доступ")
        new_m = st.text_input("Email:")
        if st.button("Добавить"): add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1])
            c1.write(e)
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()