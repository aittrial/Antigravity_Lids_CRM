import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta

# Импортируем функции (теперь delete_lead точно есть в database.py)
from database import (
    init_db, get_leads, add_lead, update_lead, delete_lead, 
    clear_all_leads, get_allowed_emails, add_allowed_email, 
    delete_allowed_email, set_archive_threshold, archive_single_lead
)
from auth import check_password, logout

APP_TITLE = "📈 Leads_CRM | Lead Management System"
st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

# Константы
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"
SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS
COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def get_status_color(status):
    colors = {"blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", "green": "#C8E6C9", "purple": "#E1BEE7", "pink": "#F8BBD0", "white": "#F0F2F6"}
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1, can_archive=False):
    """Развернутая отрисовка карточек лидов."""
    if not leads_data:
        st.info("По заданным фильтрам ничего не найдено.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        st.markdown(f'''
            <div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;">
                <b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | {row["full_name"]} | {row["phone"]}</b>
            </div>
        ''', unsafe_allow_html=True)
        
        with st.expander("📝 Управление"):
            c1, c2, c3 = st.columns(3)
            # WhatsApp
            wa_raw = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            p_cl = ''.join(filter(str.isdigit, str(wa_raw)))
            with c1:
                st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c2:
                st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}", language=None)
            with c3:
                if can_archive:
                    if st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                        archive_single_lead(row['id'])
                        st.rerun()
            
            st.divider()
            # Форма редактирования
            u_name = st.text_input("Изменить ФИО", row['full_name'], key=f"fn_{row['id']}")
            u_phone = st.text_input("Изменить Тел", row['phone'], key=f"ph_{row['id']}")
            u_status = st.selectbox("Изменить Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"st_{row['id']}")
            
            if st.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=u_name, phone=u_phone, status_color=u_status)
                st.success("Обновлено!")
                st.rerun()

def main():
    if not check_password(): return
    user_role = st.session_state.get("role", "admin")
    
    # Инициализация страниц
    if 'archive_page' not in st.session_state: st.session_state.archive_page = 0
    if 'active_page' not in st.session_state: st.session_state.active_page = 0

    st.sidebar.markdown(f"### {APP_TITLE}")
    
    # Меню навигации
    menu = ["📊 Аналитика"]
    if user_role != "analyst":
        menu.append("👥 Список лидов")
        menu.append("➕ Новый лид")
        menu.append("📂 База данных")
    if user_role == "superadmin":
        menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    # --- АНАЛИТИКА ---
    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        leads_raw = get_leads(mode="all", limit=5000)
        df_all = pd.DataFrame(leads_raw)
        
        if not df_all.empty:
            # СТАТИСТИКА ЗА ВСЕ ВРЕМЯ
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
            # СТАТИСТИКА ЗА 7 ДНЕЙ
            st.subheader("📅 Статистика за последние 7 дней")
            last_week = date.today() - timedelta(days=7)
            df_all['date_only'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['date_only'] >= last_week]
            
            m2 = st.columns(7)
            m2[0].metric("Новых (7д)", len(df_week))
            m2[1].metric("🔵", len(df_week[df_week['status_color']=='blue']))
            m2[2].metric("🟡", len(df_week[df_week['status_color']=='yellow']))
            m2[3].metric("🔴", len(df_week[df_week['status_color']=='red']))
            m2[4].metric("🟢", len(df_week[df_week['status_color']=='green']))
            m2[5].metric("🟣", len(df_week[df_week['status_color']=='purple']))
            m2[6].metric("💗", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            # Графики
            c1, c2 = st.columns(2)
            with c1:
                if not df_week.empty:
                    fig_src = px.pie(df_week['source'].value_counts().reset_index(), values='count', names='source', title="Источники (7 дней)", hole=0.4)
                    st.plotly_chart(fig_src, use_container_width=True)
            with c2:
                if not df_week.empty:
                    dyn = df_week.groupby('date_only').size().reset_index(name='count')
                    st.plotly_chart(px.area(dyn, x='date_only', y='count', title="Динамика (7 дней)"), use_container_width=True)
            
            # ГРАФИК ПО ЦВЕТАМ
            st.divider()
            st.subheader("🎨 Статусы за неделю")
            if not df_week.empty:
                st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
                st_counts.columns = ['Статус', 'Кол-во']
                c_map = {'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}
                fig_bar = px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map=c_map)
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("База пуста")

    # --- СПИСОК ЛИДОВ ---
    elif choice == "👥 Список лидов":
        st.header("👥 Лиды")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query = f1.text_input("🔍 Поиск")
        d_range = f2.date_input("📅 Даты", value=(date.today()-timedelta(days=30), date.today()))
        c_filt = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP)
        src_filt = f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        
        tab_act, tab_arc = st.tabs(["🔥 Активные", "📦 Архив"])
        
        with tab_act:
            # Активные по 50
            limit = 50
            off_act = st.session_state.active_page * limit
            data_act = get_leads(s_query, st_d, en_d, mode="active", status_filter=c_filt, source_filter=src_filt, limit=limit, offset=off_act)
            render_leads_list(data_act, start_order=off_act+1, can_archive=True)
            # Навигация + - -
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            if nav1.button("⬅️", key="act_prev") and st.session_state.active_page > 0:
                st.session_state.active_page -= 1; st.rerun()
            nav2.write(f"Страница {st.session_state.active_page + 1}")
            if nav3.button("➡️", key="act_next"):
                st.session_state.active_page += 1; st.rerun()

        with tab_arc:
            # Архив по 50
            limit = 50
            off_arc = st.session_state.archive_page * limit
            data_arc = get_leads(s_query, st_d, en_d, mode="archive", status_filter=c_filt, source_filter=src_filt, limit=limit, offset=off_arc)
            render_leads_list(data_arc, start_order=off_arc+1)
            # Навигация + - -
            arc1, arc2, arc3 = st.columns([1, 2, 1])
            if arc1.button("⬅️", key="arc_prev") and st.session_state.archive_page > 0:
                st.session_state.archive_page -= 1; st.rerun()
            arc2.write(f"Страница {st.session_state.archive_page + 1}")
            if arc3.button("➡️", key="arc_next"):
                st.session_state.archive_page += 1; st.rerun()

    # --- НОВЫЙ ЛИД ---
    elif choice == "➕ Новый лид":
        st.header("➕ Добавить лид")
        with st.form("new_lead"):
            f_name = st.text_input("ФИО")
            f_phone = st.text_input("Телефон")
            f_course = st.selectbox("Курс", COURSE_OPTIONS)
            f_source = st.selectbox("Источник", SOURCE_OPTIONS)
            if st.form_submit_button("Создать"):
                if f_name and f_phone:
                    add_lead(f_name, f_phone, course_name=f_course, source=f_source)
                    st.success("Добавлен!"); st.rerun()

    # --- БАЗА ДАННЫХ ---
    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        if user_role == "superadmin":
            c_arc, c_clr = st.columns(2)
            with c_arc:
                if st.button("📦 ВСЕ В АРХИВ"):
                    set_archive_threshold(); st.rerun()
            with c_clr:
                if st.checkbox("Я уверен, что хочу всё удалить"):
                    if st.button("🔥 УДАЛИТЬ ВСЁ"):
                        clear_all_leads(); st.rerun()
            st.divider()
            # Экспорт
            all_raw = get_leads(mode="all", limit=10000)
            if all_raw:
                df_ex = pd.DataFrame(all_raw)
                towrite = io.BytesIO()
                df_ex.to_excel(towrite, index=False, engine='xlsxwriter')
                st.download_button("📥 Скачать Excel", data=towrite.getvalue(), file_name=f"export_{date.today()}.xlsx")
        else:
            st.warning("Только для суперадмина")

if __name__ == "__main__": main()