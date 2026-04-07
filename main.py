import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta

# Импортируем все функции
from database import (
    init_db, get_leads, add_lead, update_lead, delete_lead, 
    clear_all_leads, get_allowed_emails, add_allowed_email, 
    delete_allowed_email, set_archive_threshold, archive_single_lead
)
from auth import check_password, logout

APP_TITLE = "📈 Leads_CRM | Lead Management System"
st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

# Константы для системы
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"
SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS
COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def send_telegram_backup(df):
    try:
        buf_xls = io.BytesIO()
        with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        buf_xls.seek(0)
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
        caption = f"📦 CRM BACKUP | 📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': caption}, files={'document': (f"leads_backup.xlsx", buf_xls)})
        st.success("✅ Бэкап отправлен!")
    except Exception as e:
        st.error(f"Ошибка бэкапа: {e}")

def get_status_color(status):
    colors = {"blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", "green": "#C8E6C9", "purple": "#E1BEE7", "pink": "#F8BBD0", "white": "#F0F2F6"}
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1, can_archive=False):
    if not leads_data:
        st.info("Лидов не найдено.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        st.markdown(f'''<div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;"><b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | {row["full_name"]} | {row["phone"]}</b></div>''', unsafe_allow_html=True)
        with st.expander("🛠 Управление"):
            c1, c2, c3 = st.columns(3)
            wa_raw = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            p_cl = ''.join(filter(str.isdigit, str(wa_raw)))
            with c1:
                st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c2:
                st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}", language=None)
            with c3:
                if can_archive and st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                    archive_single_lead(row['id']); st.rerun()
            st.divider()
            n_name = st.text_input("Имя", row['full_name'], key=f"n_{row['id']}")
            n_phone = st.text_input("Тел", row['phone'], key=f"p_{row['id']}")
            n_color = st.selectbox("Цвет", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"c_{row['id']}")
            if st.button("💾 Сохранить", key=f"s_{row['id']}"):
                update_lead(row['id'], full_name=n_name, phone=n_phone, status_color=n_color); st.rerun()

def main():
    if not check_password(): return
    user_role = st.session_state.get("role", "admin")
    
    # Инициализация страниц
    if 'archive_page_number' not in st.session_state: st.session_state.archive_page_number = 0

    st.sidebar.markdown(f"### {APP_TITLE}")
    
    if user_role == "analyst":
        menu = ["📊 Аналитика"]
    else:
        menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
        if user_role == "superadmin": menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    # --- РАЗДЕЛ: АНАЛИТИКА ---
    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        # Здесь mode="all" берет все данные без лимитов
        all_leads = get_leads(mode="all")
        df_all = pd.DataFrame(all_leads)
        
        if not df_all.empty:
            st.subheader("📈 Общая статистика (все время)")
            m1 = st.columns(7)
            m1[0].metric("Всего", len(df_all))
            m1[1].metric("🔵 Работа", len(df_all[df_all['status_color']=='blue']))
            m1[2].metric("🟡 Ждут", len(df_all[df_all['status_color']=='yellow']))
            m1[3].metric("🔴 Отказ", len(df_all[df_all['status_color']=='red']))
            m1[4].metric("🟢 Возврат", len(df_all[df_all['status_color']=='green']))
            m1[5].metric("🟣 Офис", len(df_all[df_all['status_color']=='purple']))
            m1[6].metric("💗 Работа 2", len(df_all[df_all['status_color']=='pink']))
            
            st.divider()
            st.subheader("📅 Статистика за последние 7 дней")
            last_w = date.today() - timedelta(days=7)
            df_all['d_only'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['d_only'] >= last_w]
            
            m2 = st.columns(7)
            m2[0].metric("Новых (7д)", len(df_week))
            m2[1].metric("🔵", len(df_week[df_week['status_color']=='blue'])); m2[2].metric("🟡", len(df_week[df_week['status_color']=='yellow'])); m2[3].metric("🔴", len(df_week[df_week['status_color']=='red'])); m2[4].metric("🟢", len(df_week[df_week['status_color']=='green'])); m2[5].metric("🟣", len(df_week[df_week['status_color']=='purple'])); m2[6].metric("💗", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if not df_week.empty:
                    st.plotly_chart(px.pie(df_week['source'].value_counts().reset_index(), values='count', names='source', title="Источники (7 дней)", hole=0.4), use_container_width=True)
            with c2:
                if not df_week.empty:
                    dyn = df_week.groupby('d_only').size().reset_index(name='count')
                    st.plotly_chart(px.area(dyn, x='d_only', y='count', title="Динамика (7 дней)"), use_container_width=True)
            
            st.divider()
            st.subheader("🎨 Работа по статусам (7 дней)")
            if not df_week.empty:
                st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
                st_counts.columns = ['Статус', 'Кол-во']
                c_map = {'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}
                st.plotly_chart(px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map=c_map), use_container_width=True)
        else: st.info("База пуста")

    # --- РАЗДЕЛ: СПИСОК ЛИДОВ ---
    elif choice == "👥 Список лидов":
        st.header("👥 Список лидов")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query = f1.text_input("🔍 Поиск")
        d_range = f2.date_input("📅 Даты", value=(date.today()-timedelta(days=30), date.today()))
        c_filt = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP)
        src_filt = f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        
        tab_active, tab_archive = st.tabs(["🔥 Активные", "📦 Архив"])
        with tab_active:
            # Активные: только последние 50 штук без кнопок страниц
            data_act = get_leads(s_query, st_d, en_d, mode="active", status_filter=c_filt, source_filter=src_filt, limit=50, offset=0)
            render_leads_list(data_act, start_order=1, can_archive=True)

        with tab_archive:
            # Архив: постраничный переход по 50 штук
            l_per_page = 50
            c_off = st.session_state.archive_page_number * l_per_page
            data_arc = get_leads(s_query, st_d, en_d, mode="archive", status_filter=c_filt, source_filter=src_filt, limit=l_per_page, offset=c_off)
            render_leads_list(data_arc, start_order=c_off + 1)
            
            st.write("---")
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                if st.button("⬅️ Назад", key="btn_p") and st.session_state.archive_page_number > 0:
                    st.session_state.archive_page_number -= 1; st.rerun()
            with nav2:
                st.markdown(f"<center>Страница {st.session_state.archive_page_number + 1}</center>", unsafe_allow_html=True)
            with nav3:
                # Кнопка Вперед работает, если на странице ровно 50 записей (значит, есть ещё)
                if len(data_arc) == l_per_page:
                    if st.button("Вперед ➡️", key="btn_n"):
                        st.session_state.archive_page_number += 1; st.rerun()
                else: st.write("Конец")

    # --- РАЗДЕЛ: НОВЫЙ ЛИД ---
    elif choice == "➕ Новый лид":
        st.header("➕ Добавить лид")
        with st.form("f_new"):
            fn, ph = st.text_input("ФИО"), st.text_input("Телефон")
            crs, src = st.selectbox("Курс", COURSE_OPTIONS), st.selectbox("Источник", SOURCE_OPTIONS)
            if st.form_submit_button("Создать"):
                if fn and ph: add_lead(fn, ph, course_name=crs, source=src); st.success("✅ Готово!"); st.rerun()

    # --- РАЗДЕЛ: БАЗА ДАННЫХ ---
    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("📥 Экспорт")
            all_raw = get_leads(mode="all")
            if all_raw:
                df_ex = pd.DataFrame(all_raw)
                towrite = io.BytesIO()
                df_ex.to_excel(towrite, index=False, engine='xlsxwriter')
                st.download_button("📥 Скачать Excel", data=towrite.getvalue(), file_name=f"crm_{date.today()}.xlsx")
                if st.button("🤖 Бэкап в Telegram"): send_telegram_backup(df_ex)
        with c2:
            st.subheader("📦 Архивация")
            if user_role == "superadmin":
                if st.button("📦 ВСЕ В АРХИВ"): set_archive_threshold(); st.rerun()
        with c3:
            st.subheader("🔥 Очистка")
            if user_role == "superadmin":
                if st.checkbox("Я подтверждаю очистку"):
                    if st.button("🔥 УДАЛИТЬ ВСЁ"): clear_all_leads(); st.rerun()
        st.divider()
        st.subheader("🚀 Импорт из Excel")
        up_file = st.file_uploader("Загрузите .xlsx", type=["xlsx"])
        if up_file and st.button("🚀 Начать импорт"):
            try:
                df_im = pd.read_excel(up_file)
                for _, r in df_im.iterrows():
                    add_lead(str(r.get('full_name','')), str(r.get('phone','')), source="Excel Import")
                st.success("✅ Импорт завершен!"); st.rerun()
            except Exception as e: st.error(f"Ошибка: {e}")

    # --- РАЗДЕЛ: АДМИНИСТРИРОВАНИЕ ---
    elif choice == "🔑 Администрирование" and user_role == "superadmin":
        st.header("🔑 Доступы")
        nm, nr = st.text_input("Email:"), st.selectbox("Роль:", ["admin", "analyst"])
        if st.button("Добавить"): add_allowed_email(nm, nr); st.rerun()
        st.divider()
        for e in get_allowed_emails():
            col1, col2 = st.columns([4, 1])
            col1.write(f"• {e['email']} ({e['role']})")
            if col2.button("Удалить", key=f"del_{e['email']}"): delete_allowed_email(e['email']); st.rerun()

if __name__ == "__main__": main()