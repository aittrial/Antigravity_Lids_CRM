import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta
from database import (init_db, get_leads, add_lead, update_lead, delete_lead, 
                    clear_all_leads, get_allowed_emails, add_allowed_email, delete_allowed_email, set_archive_threshold, archive_single_lead)
from auth import check_password, logout

APP_TITLE = "📈 Leads_CRM | Lead Management System"
st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

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
    if not leads_data:
        st.info("По заданным фильтрам ничего не найдено.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        st.markdown(f'''<div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;"><b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | {row["full_name"]} | {row["phone"]}</b></div>''', unsafe_allow_html=True)
        with st.expander("📝 Управление"):
            c1, c2, c3 = st.columns(3)
            # WhatsApp логика
            wa_raw = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            p_cl = ''.join(filter(str.isdigit, str(wa_raw)))
            with c1: st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c2: st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}", language=None)
            with c3:
                if can_archive and st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                    archive_single_lead(row['id']); st.rerun()
            st.divider()
            un = st.text_input("ФИО", row['full_name'], key=f"n_{row['id']}")
            up = st.text_input("Тел", row['phone'], key=f"p_{row['id']}")
            us = st.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"s_{row['id']}")
            if st.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=un, phone=up, status_color=us); st.rerun()

def main():
    if not check_password(): return
    user_role = st.session_state.get("role", "admin")
    st.sidebar.markdown(f"### {APP_TITLE}")
    
    menu = ["📊 Аналитика"]
    if user_role != "analyst":
        menu += ["👥 Список лидов", "➕ Новый лид", "📂 База данных"]
    if user_role == "superadmin":
        menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        df_all = pd.DataFrame(get_leads(mode="all"))
        if not df_all.empty:
            # 1. ОБЩАЯ СТАТИСТИКА (Все данные)
            st.subheader("📈 Общая статистика (все время)")
            m_all = st.columns(7)
            m_all[0].metric("Всего", len(df_all))
            m_all[1].metric("🔵 Работа", len(df_all[df_all['status_color']=='blue']))
            m_all[2].metric("🟡 Ждут", len(df_all[df_all['status_color']=='yellow']))
            m_all[3].metric("🔴 Отказ", len(df_all[df_all['status_color']=='red']))
            m_all[4].metric("🟢 Возврат", len(df_all[df_all['status_color']=='green']))
            m_all[5].metric("🟣 Офис", len(df_all[df_all['status_color']=='purple']))
            m_all[6].metric("💗 Работа 2", len(df_all[df_all['status_color']=='pink']))
            
            st.divider()

            # 2. СТАТИСТИКА ЗА 7 ДНЕЙ (Фильтруем)
            st.subheader("📅 Статистика за последние 7 дней")
            last_w = date.today() - timedelta(days=7)
            df_all['date_only'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['date_only'] >= last_w]
            
            m_w = st.columns(7)
            m_w[0].metric("Всего (7д)", len(df_week))
            m_w[1].metric("🔵", len(df_week[df_week['status_color']=='blue']))
            m_w[2].metric("🟡", len(df_week[df_week['status_color']=='yellow']))
            m_w[3].metric("🔴", len(df_week[df_week['status_color']=='red']))
            m_w[4].metric("🟢", len(df_week[df_week['status_color']=='green']))
            m_w[5].metric("🟣", len(df_week[df_week['status_color']=='purple']))
            m_w[6].metric("💗", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if not df_week.empty:
                    fig_src = px.pie(df_week['source'].value_counts().reset_index(), values='count', names='source', title="Источники лидов (7 дней)", hole=0.4)
                    st.plotly_chart(fig_src, use_container_width=True)
            with c2:
                if not df_week.empty:
                    dyn = df_week.groupby('date_only').size().reset_index(name='count')
                    st.plotly_chart(px.area(dyn, x='date_only', y='count', title="Динамика новых лидов (7 дней)"), use_container_width=True)
            
            st.divider()
            st.subheader("🎨 Работа по статусам (7 дней)")
            if not df_week.empty:
                st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
                st_counts.columns = ['Статус', 'Кол-во']
                c_map = {'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}
                fig_bar = px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map=c_map)
                st.plotly_chart(fig_bar, use_container_width=True)
        else: st.info("База пуста")

    elif choice == "👥 Список лидов":
        st.header("👥 Лиды")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query, d_range = f1.text_input("🔍 Поиск"), f2.date_input("📅 Дата", value=(date.today()-timedelta(days=30), date.today()))
        c_filt, src_filt = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP), f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        t1, t2 = st.tabs(["🔥 Активные", "📦 Архив"])
        with t1: render_leads_list(get_leads(s_query, st_d, en_d, mode="active", status_filter=c_filt, source_filter=src_filt), can_archive=True)
        with t2: 
            all_archived = get_leads(s_query, st_d, en_d, mode="archive", status_filter=c_filt, source_filter=src_filt)
            render_leads_list(all_archived)

    elif choice == "➕ Новый лид":
        st.header("➕ Новый лид")
        with st.form("new_lead_form", clear_on_submit=True):
            fn, ph = st.text_input("ФИО"), st.text_input("Тел")
            crs, src = st.selectbox("Курс", COURSE_OPTIONS), st.selectbox("Источник", SOURCE_OPTIONS)
            if st.form_submit_button("🚀 Создать"):
                if fn and ph: 
                    add_lead(fn, ph, course_name=crs, source=src)
                    st.success("✅ Лид добавлен!")

    elif choice == "📂 База данных":
        st.header("📂 База данных")
        if user_role == "superadmin":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📦 ВСЁ В АРХИВ"): set_archive_threshold(); st.rerun()
            with c2:
                if st.checkbox("Я уверен, что хочу очистить базу"):
                    if st.button("🔥 ОЧИСТИТЬ ВСЁ"): clear_all_leads(); st.rerun()
        else: st.warning("Доступ только суперадмину")

    elif choice == "🔑 Администрирование" and user_role == "superadmin":
        st.header("🔑 Доступы")
        nm = st.text_input("Email:")
        nr = st.selectbox("Роль", ["admin", "analyst"])
        if st.button("Добавить"):
            add_allowed_email(nm, nr); st.rerun()
        for d in get_allowed_emails():
            st.write(f"• {d['email']} ({d['role']})")
            if st.button("Удалить", key=f"del_{d['email']}"):
                delete_allowed_email(d['email']); st.rerun()

if __name__ == "__main__": main()