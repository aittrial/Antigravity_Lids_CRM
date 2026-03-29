import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime, date, timedelta
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                      clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email, set_archive_threshold)
from auth import check_password, logout

APP_TITLE = "📈 LeadFlow | Lead Management System"

st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]
# Список цветов для БД
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple"]
# Соответствие для фильтра
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый"]

def get_status_color(status):
    colors = {
        "blue": "#B3D7FF",    # Синий
        "yellow": "#FFF59D",  # Желтый
        "red": "#FFAB91",     # Красный
        "green": "#C8E6C9",   # Зеленый (Требует возврата)
        "purple": "#E1BEE7",  # Фиолетовый (Передан в офис)
        "white": "#F0F2F6"    # Белый
    }
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1):
    if not leads_data:
        st.info("По заданным фильтрам ничего не найдено.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        pref_time = row.get('preferred_time', '---')
        
        st.markdown(f"""
            <div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: #000000 !important;">
                <b style="color: #000000 !important; font-size: 14px;">
                    #{start_order+i} | 📅 {date_s} | 🕒 {pref_time} | {row['full_name']} | {row['phone']}
                </b>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Управление лидом"):
            col_wa, col_copy = st.columns([1, 1])
            phone_num = ''.join(filter(str.isdigit, str(row['phone'])))
            with col_wa:
                st.markdown(f'''<a href="https://wa.me/{phone_num}" target="_blank">
                    <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">
                    💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with col_copy:
                lead_text = f"--- ДАННЫЕ ЛИДА ---\nФИО: {row['full_name']}\nТелефон: {row['phone']}\nEmail: {row['email']}\nКурс: {row['course_name']}"
                st.code(lead_text, language=None)
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("ФИО", row['full_name'], key=f"n_{row['id']}")
            p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
            e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
            
            c4, c5, c6 = st.columns(3)
            current_course = row['course_name'] if row['course_name'] in COURSE_OPTIONS else "Other"
            curr_c_select = c4.selectbox("Курс", COURSE_OPTIONS, index=COURSE_OPTIONS.index(current_course), key=f"cs_{row['id']}")
            curr_c = c4.text_input("Уточните курс", row['course_name'], key=f"c_manual_{row['id']}") if curr_c_select == "Other" else curr_c_select
            curr_t = c5.text_input("Время созвона", row.get('preferred_time', ''), key=f"t_{row['id']}")
            
            # Обновленный выбор статуса
            curr_s = c6.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"s_{row['id']}")
            
            c7, c8 = st.columns(2)
            current_src_val = row.get('source', 'Other')
            if current_src_val not in SOURCE_OPTIONS: current_src_val = "Other"
            curr_src_select = c7.selectbox("Источник", SOURCE_OPTIONS, index=SOURCE_OPTIONS.index(current_src_val), key=f"srcs_{row['id']}")
            curr_src = c7.text_input("Уточните источник", row.get('source', ''), key=f"src_manual_{row['id']}") if curr_src_select == "Other" else curr_src_select
            curr_comm = c8.text_area("Комментарии", row['comment'] if row['comment'] else "", key=f"cm_{row['id']}", height=100)
            
            bs, bd = st.columns([1, 5])
            if bs.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=n, phone=p, email=e, course_name=curr_c, preferred_time=curr_t, status_color=curr_s, comment=curr_comm, source=curr_src)
                st.rerun()
            if st.session_state.get("role") == "superadmin" and bd.button("🗑️ Удалить", key=f"del_{row['id']}"):
                delete_lead(row['id']); st.rerun()

def main():
    if not check_password(): return

    st.sidebar.markdown(f"### {APP_TITLE}")
    menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
    if st.session_state.get("role") == "superadmin":
        menu.append("🔑 Администрирование")
    
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    today = date.today()
    default_start = today - timedelta(days=30)

    if choice == "📊 Аналитика":
        st.header("📊 Аналитический дашборд")
        d_range = st.date_input("Период", value=(default_start, today))
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (default_start, today)
        data = get_leads(None, st_d, en_d, mode="active") + get_leads(None, st_d, en_d, mode="archive")
        if data:
            df = pd.DataFrame(data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Всего", len(df))
            m2.metric("🔵 Работа", len(df[df['status_color'] == 'blue']))
            m3.metric("🟡 Ожидание", len(df[df['status_color'] == 'yellow']))
            m4.metric("🔴 Отказ", len(df[df['status_color'] == 'red']))
            m5.metric("🟢 Возврат", len(df[df['status_color'] == 'green']))
            m6.metric("🟣 Офис", len(df[df['status_color'] == 'purple']))
            st.divider()
            cl, cr = st.columns(2)
            st_counts = df['status_color'].value_counts().reset_index()
            st_counts.columns = ['Статус', 'Количество']
            fig_bar = px.bar(st_counts, x='Количество', y='Статус', orientation='h', title="Статусы", template="plotly_white", color='Статус', 
                             color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','white':'#E0E0E0','green':'#C8E6C9','purple':'#E1BEE7'})
            cl.plotly_chart(fig_bar, use_container_width=True)
            df['Дата'] = df['created_at'].dt.date
            daily = df.groupby('Дата').size().reset_index(name='Лидов')
            fig_area = px.area(daily, x='Дата', y='Лидов', title="Динамика поступления", template="plotly_white")
            cr.plotly_chart(fig_area, use_container_width=True)

    elif choice == "👥 Список лидов":
        st.header("👥 Работа с лидами")
        with st.container():
            f_col1, f_col2, f_col3 = st.columns([2, 1.5, 1.2])
            search = f_col1.text_input("🔍 Поиск", "", key="main_search")
            d_range = f_col2.date_input("📅 Дата", value=(default_start, today), key="main_date")
            color_f = f_col3.selectbox("🎨 Статус", FILTER_COLOR_MAP, key="main_color")
        
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        st.divider()

        tab_active, tab_archive = st.tabs(["🔥 Активные", "📦 Архив"])
        with tab_active:
            leads_active = get_leads(search if search else None, st_d, en_d, mode="active", status_filter=color_f)
            st.info(f"Активных лидов: **{len(leads_active)}**")
            render_leads_list(leads_active, start_order=1)
        with tab_archive:
            leads_archive = get_leads(search if search else None, st_d, en_d, mode="archive", status_filter=color_f)
            if leads_archive:
                ipp = 50
                num_p = max(1, (len(leads_archive) // ipp) + (1 if len(leads_archive) % ipp > 0 else 0))
                page = st.number_input("Страница", 1, num_p)
                render_leads_list(leads_archive[(page-1)*ipp : page*ipp], start_order=1)

    elif choice == "➕ Новый лид":
        st.header("➕ Добавление записи")
        with st.form("manual_add", clear_on_submit=True):
            f1, f2 = st.columns(2)
            f_n, f_p = f1.text_input("ФИО"), f2.text_input("Телефон")
            f3, f4 = st.columns(2)
            f_e, f_t = f3.text_input("Email"), f4.text_input("Время созвона")
            f5, f6 = st.columns(2)
            f_c, f_src = f5.selectbox("Курс", COURSE_OPTIONS), f6.selectbox("Источник", SOURCE_OPTIONS)
            f_s = st.selectbox("Статус (Цвет)", COLOR_KEYS)
            f_cm = st.text_area("Комментарий")
            if st.form_submit_button("Создать запись"):
                if f_n and f_p: add_lead(f_n, f_p, f_e, f_c, f_t, f_src, f_cm, f_s); st.success("Лид добавлен!"); st.rerun()
                else: st.error("Имя и Телефон обязательны")

    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c_ex, c_arch = st.columns(2)
        with c_ex:
            st.subheader("📥 Экспорт")
            all_l = get_leads(mode="active") + get_leads(mode="archive")
            if all_l:
                df_ex = pd.DataFrame(all_l)
                cols = {'created_at':'Дата','full_name':'ФИО','phone':'Телефон','email':'Email','course_name':'Курс','preferred_time':'Время','source':'Источник','comment':'Комментарий','status_color':'Статус'}
                df_ex = df_ex[list(cols.keys())].rename(columns=cols)
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_ex.to_excel(wr, index=False)
                st.download_button("📥 Скачать Excel", data=buf.getvalue(), file_name=f"export_{date.today()}.xlsx")
        with c_arch:
            st.subheader("📦 Архивация")
            if st.session_state.get("role") == "superadmin":
                if st.button("📦 ПЕРЕМЕСТИТЬ ВСЁ В АРХИВ"): set_archive_threshold(); st.rerun()

    elif choice == "🔑 Администрирование" and st.session_state.get("role") == "superadmin":
        st.header("🔑 Доступы")
        new_m = st.text_input("Email:")
        if st.button("Добавить"):
            if new_m: add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1]); c1.write(f"• {e}")
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()