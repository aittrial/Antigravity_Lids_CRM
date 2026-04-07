import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta

# Импортируем все необходимые функции из нашего database.py
from database import (
    init_db, 
    get_leads, 
    add_lead, 
    update_lead, 
    delete_lead, 
    clear_all_leads, 
    get_allowed_emails, 
    add_allowed_email, 
    delete_allowed_email, 
    set_archive_threshold, 
    archive_single_lead
)
from auth import check_password, logout

# --- ОСНОВНЫЕ НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
APP_TITLE = "📈 Leads_CRM | Lead Management System"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# Инициализация структуры базы данных при старте
init_db()

# Данные для Telegram уведомлений и бэкапов
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"

# Списки опций для выпадающих меню
SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS

COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]

# Цветовая схема статусов
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def get_status_color(status_name):
    """Возвращает HEX-код цвета для визуального оформления карточки лида."""
    color_dict = {
        "blue": "#B3D7FF", 
        "yellow": "#FFF59D", 
        "red": "#FFAB91", 
        "green": "#C8E6C9", 
        "purple": "#E1BEE7", 
        "pink": "#F8BBD0", 
        "white": "#F0F2F6"
    }
    return color_dict.get(status_name, "#F0F2F6")

def render_leads_list(leads_data, start_order=1, can_archive=False):
    """
    Развернутая функция отрисовки списка лидов. 
    Каждый лид отображается как отдельная карточка с формой управления.
    """
    if not leads_data:
        st.info("По вашему запросу лидов не найдено.")
        return

    for index, row in enumerate(leads_data):
        # Определяем цвет фона карточки
        current_card_color = get_status_color(row['status_color'])
        creation_date_formatted = row['created_at'].strftime("%d.%m.%Y %H:%M")
        
        # HTML-разметка карточки для красоты и наглядности
        st.markdown(f'''
            <div style="background-color:{current_card_color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;">
                <b style="color: black !important; font-size: 14px;">
                    #{start_order + index} | 📅 {creation_date_formatted} | {row["full_name"]} | {row["phone"]}
                </b>
            </div>
        ''', unsafe_allow_html=True)
        
        # Раскрывающийся блок управления лидом
        with st.expander("🛠 Управление данными лида"):
            col_actions_1, col_actions_2, col_actions_3 = st.columns(3)
            
            # Подготовка номера для WhatsApp
            raw_phone = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            clean_phone_digits = ''.join(filter(str.isdigit, str(raw_phone)))
            
            with col_actions_1:
                # Кнопка прямой ссылки на WhatsApp
                st.markdown(f'''
                    <a href="https://wa.me/{clean_phone_digits}" target="_blank">
                        <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">
                            💬 Написать в WhatsApp
                        </button>
                    </a>
                ''', unsafe_allow_html=True)
                
            with col_actions_2:
                # Отображение данных для быстрого копирования
                st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}", language=None)
                
            with col_actions_3:
                # Кнопка архивации (если разрешено)
                if can_archive:
                    if st.button("📦 Отправить в архив", key=f"btn_to_archive_{row['id']}"):
                        archive_single_lead(row['id'])
                        st.rerun()
            
            st.divider()
            
            # Развернутая форма редактирования полей
            input_name = st.text_input("Изменить ФИО", row['full_name'], key=f"edit_name_{row['id']}")
            
            input_phone = st.text_input("Изменить Телефон", row['phone'], key=f"edit_phone_{row['id']}")
            
            input_status = st.selectbox(
                "Изменить Статус (Цвет)", 
                COLOR_KEYS, 
                index=COLOR_KEYS.index(row['status_color']), 
                key=f"edit_status_{row['id']}"
            )
            
            # Кнопка сохранения изменений
            if st.button("💾 Сохранить изменения", key=f"btn_save_edit_{row['id']}"):
                update_lead(
                    row['id'], 
                    full_name=input_name, 
                    phone=input_phone, 
                    status_color=input_status
                )
                st.success("Данные успешно обновлены!")
                st.rerun()

def main():
    # Проверка пароля и авторизация
    if not check_password():
        return
        
    # Извлекаем роль пользователя из текущей сессии
    user_current_role = st.session_state.get("role", "admin")
    
    # Инициализация переменных для пагинации (страниц)
    if 'archive_page_num' not in st.session_state:
        st.session_state.archive_page_num = 0
        
    if 'active_page_num' not in st.session_state:
        st.session_state.active_page_num = 0

    # Боковая панель (Сайдбар)
    st.sidebar.markdown(f"### {APP_TITLE}")
    
    # Формирование меню в зависимости от роли
    main_menu_options = ["📊 Аналитика"]
    
    if user_current_role != "analyst":
        main_menu_options.append("👥 Список лидов")
        main_menu_options.append("➕ Новый лид")
        main_menu_options.append("📂 База данных")
        
    if user_current_role == "superadmin":
        main_menu_options.append("🔑 Администрирование")
            
    user_choice = st.sidebar.selectbox("Выберите раздел:", main_menu_options)
    
    if st.sidebar.button("🚪 Завершить сеанс"):
        logout()

    # --- РАЗДЕЛ: АНАЛИТИКА ---
    if user_choice == "📊 Аналитика":
        st.header("📊 Аналитическая панель")
        
        # Получаем все данные для расчетов
        all_leads_raw = get_leads(mode="all", limit=10000, offset=0)
        df_full = pd.DataFrame(all_leads_raw)
        
        if not df_full.empty:
            # 1. СТАТИСТИКА ЗА ВСЕ ВРЕМЯ (Явный расчет)
            st.subheader("📈 Общие показатели (вся история)")
            
            metric_cols_all = st.columns(7)
            metric_cols_all[0].metric("Всего лидов", len(df_full))
            metric_cols_all[1].metric("🔵 В работе", len(df_full[df_full['status_color']=='blue']))
            metric_cols_all[2].metric("🟡 Ожидание", len(df_full[df_full['status_color']=='yellow']))
            metric_cols_all[3].metric("🔴 Отказ", len(df_full[df_full['status_color']=='red']))
            metric_cols_all[4].metric("🟢 Возврат", len(df_full[df_full['status_color']=='green']))
            metric_cols_all[5].metric("🟣 Офис", len(df_full[df_full['status_color']=='purple']))
            metric_cols_all[6].metric("💗 Работа 2", len(df_full[df_full['status_color']=='pink']))
            
            st.divider()

            # 2. СТАТИСТИКА ЗА 7 ДНЕЙ (Явный фильтр)
            st.subheader("📅 Активность за последние 7 дней")
            
            date_threshold = date.today() - timedelta(days=7)
            df_full['just_date'] = pd.to_datetime(df_full['created_at']).dt.date
            df_recent = df_full[df_full['just_date'] >= date_threshold]
            
            metric_cols_week = st.columns(7)
            metric_cols_week[0].metric("Новых (7д)", len(df_recent))
            metric_cols_week[1].metric("🔵", len(df_recent[df_recent['status_color']=='blue']))
            metric_cols_week[2].metric("🟡", len(df_recent[df_recent['status_color']=='yellow']))
            metric_cols_week[3].metric("🔴", len(df_recent[df_recent['status_color']=='red']))
            metric_cols_week[4].metric("🟢", len(df_recent[df_recent['status_color']=='green']))
            metric_cols_week[5].metric("🟣", len(df_recent[df_recent['status_color']=='purple']))
            metric_cols_week[6].metric("💗", len(df_recent[df_recent['status_color']=='pink']))

            st.divider()
            
            # Визуализация данных через графики
            chart_col_1, chart_col_2 = st.columns(2)
            
            with chart_col_1:
                if not df_recent.empty:
                    # Круговая диаграмма источников
                    src_distribution = df_recent['source'].value_counts().reset_index()
                    fig_pie = px.pie(
                        src_distribution, 
                        values='count', 
                        names='source', 
                        title="Источники трафика (7 дней)", 
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
            with chart_col_2:
                if not df_recent.empty:
                    # График динамики поступления лидов
                    daily_dynamics = df_recent.groupby('just_date').size().reset_index(name='count')
                    fig_area = px.area(
                        daily_dynamics, 
                        x='just_date', 
                        y='count', 
                        title="Динамика новых лидов (7 дней)"
                    )
                    st.plotly_chart(fig_area, use_container_width=True)
            
            # Гистограмма по статусам (Цветам)
            st.divider()
            st.subheader("🎨 Распределение по статусам (7 дней)")
            
            if not df_recent.empty:
                # Фильтруем только раскрашенные статусы (без белого)
                status_counts = df_recent[df_recent['status_color'] != 'white']['status_color'].value_counts().reset_index()
                status_counts.columns = ['Статус', 'Количество']
                
                # Маппинг для графиков Plotly
                custom_color_map = {
                    'blue':'#B3D7FF', 'yellow':'#FFF59D', 'red':'#FFAB91', 
                    'green':'#C8E6C9', 'purple':'#E1BEE7', 'pink':'#F8BBD0'
                }
                
                fig_bar = px.bar(
                    status_counts, 
                    x='Количество', 
                    y='Статус', 
                    orientation='h', 
                    color='Статус', 
                    color_discrete_map=custom_color_map
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("База данных пока пуста. Аналитика недоступна.")

    # --- РАЗДЕЛ: СПИСОК ЛИДОВ (С ПАГИНАЦИЕЙ) ---
    elif user_choice == "👥 Список лидов":
        st.header("👥 Работа с лидами")
        
        # Блок фильтров
        filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns([2, 1.2, 1, 1])
        
        search_text = filter_col_1.text_input("🔍 Быстрый поиск (Имя/Телефон)")
        
        date_pick = filter_col_2.date_input(
            "📅 Выбор периода", 
            value=(date.today() - timedelta(days=30), date.today())
        )
        
        color_filter_val = filter_col_3.selectbox("🎨 По цвету", FILTER_COLOR_MAP)
        
        source_filter_val = filter_col_4.selectbox("📡 По источнику", FILTER_SOURCE_MAP)
        
        # Обработка дат
        start_dt, end_dt = (date_pick[0], date_pick[1]) if len(date_pick) == 2 else (None, None)
        
        # Вкладки Активные / Архив
        tab_active_leads, tab_archive_leads = st.tabs(["🔥 Активные лиды", "📦 Архивные лиды"])
        
        with tab_active_leads:
            # Логика пагинации для активных
            leads_per_page = 50
            active_offset = st.session_state.active_page_num * leads_per_page
            
            data_active = get_leads(
                search_text, start_dt, end_dt, 
                mode="active", 
                status_filter=color_filter_val, 
                source_filter=source_filter_val, 
                limit=leads_per_page, 
                offset=active_offset
            )
            
            render_leads_list(data_active, start_order=active_offset + 1, can_archive=True)
            
            # Кнопки навигации по страницам (+ - -)
            st.write("---")
            nav_col_1, nav_col_2, nav_col_3 = st.columns([1, 2, 1])
            
            if nav_col_1.button("⬅️ Назад", key="btn_prev_active"):
                if st.session_state.active_page_num > 0:
                    st.session_state.active_page_num -= 1
                    st.rerun()
            
            nav_col_2.markdown(f"<center>Страница <b>{st.session_state.active_page_num + 1}</b></center>", unsafe_allow_html=True)
            
            if nav_col_3.button("Вперед ➡️", key="btn_next_active"):
                st.session_state.active_page_num += 1
                st.rerun()

        with tab_archive_leads:
            # Логика пагинации для архива
            leads_per_page_arc = 50
            archive_offset = st.session_state.archive_page_num * leads_per_page_arc
            
            data_archive = get_leads(
                search_text, start_dt, end_dt, 
                mode="archive", 
                status_filter=color_filter_val, 
                source_filter=source_filter_val, 
                limit=leads_per_page_arc, 
                offset=archive_offset
            )
            
            render_leads_list(data_archive, start_order=archive_offset + 1)
            
            # Кнопки навигации по страницам (+ - -)
            st.write("---")
            arc_nav_1, arc_nav_2, arc_nav_3 = st.columns([1, 2, 1])
            
            if arc_nav_1.button("⬅️ Назад", key="btn_prev_archive"):
                if st.session_state.archive_page_num > 0:
                    st.session_state.archive_page_num -= 1
                    st.rerun()
            
            arc_nav_2.markdown(f"<center>Страница <b>{st.session_state.archive_page_num + 1}</b></center>", unsafe_allow_html=True)
            
            if arc_nav_3.button("Вперед ➡️", key="btn_next_archive"):
                st.session_state.archive_page_num += 1
                st.rerun()

    # --- РАЗДЕЛ: НОВЫЙ ЛИД ---
    elif user_choice == "➕ Новый лид":
        st.header("➕ Регистрация нового лида")
        
        with st.form("form_create_new_lead", clear_on_submit=True):
            input_fn = st.text_input("Полное имя (ФИО)*")
            input_ph = st.text_input("Номер телефона (с кодом страны)*")
            
            input_crs = st.selectbox("Интересующий курс", COURSE_OPTIONS)
            input_src = st.selectbox("Откуда пришел лид?", SOURCE_OPTIONS)
            
            if st.form_submit_button("🚀 Добавить в систему"):
                if input_fn and input_ph:
                    add_lead(input_fn, input_ph, course_name=input_crs, source=input_src)
                    st.success(f"Лид {input_fn} успешно создан!")
                else:
                    st.error("Поля Имя и Телефон обязательны для заполнения.")

    # --- РАЗДЕЛ: БАЗА ДАННЫХ ---
    elif user_choice == "📂 База данных":
        st.header("📂 Управление хранилищем")
        
        if user_current_role == "superadmin":
            col_db_1, col_db_2 = st.columns(2)
            
            with col_db_1:
                # Массовая архивация
                if st.button("📦 ПЕРЕМЕСТИТЬ ВСЕ ТЕКУЩИЕ В АРХИВ"):
                    set_archive_threshold()
                    st.success("Все активные лиды перенесены в архив.")
                    st.rerun()
                    
            with col_db_2:
                # Полная очистка
                if st.checkbox("Я понимаю, что это действие необратимо"):
                    if st.button("🔥 ПОЛНОСТЬЮ ОЧИСТИТЬ БАЗУ"):
                        clear_all_leads()
                        st.success("База данных очищена.")
                        st.rerun()
            
            st.divider()
            
            # Выгрузка данных
            st.subheader("📤 Экспорт данных")
            all_data_for_export = get_leads(mode="all", limit=10000, offset=0)
            
            if all_data_for_export:
                df_export = pd.DataFrame(all_data_for_export)
                
                # Подготовка Excel файла
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Скачать базу в Excel", 
                    data=excel_buffer.getvalue(), 
                    file_name=f"crm_export_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("У вас недостаточно прав для управления базой данных.")

    # --- РАЗДЕЛ: АДМИНИСТРИРОВАНИЕ ---
    elif user_choice == "🔑 Администрирование" and user_current_role == "superadmin":
        st.header("🔑 Управление правами доступа")
        
        col_adm_1, col_adm_2 = st.columns([3, 1])
        
        mail_to_add = col_adm_1.text_input("Введите Email нового сотрудника:")
        role_to_assign = col_adm_2.selectbox("Выберите роль:", ["admin", "analyst"])
        
        if st.button("✅ Предоставить доступ"):
            if mail_to_add:
                add_allowed_email(mail_to_add, role_to_assign)
                st.success(f"Сотрудник {mail_to_add} добавлен.")
                st.rerun()
        
        st.divider()
        
        # Список текущих доступов
        st.subheader("Список активных доступов")
        current_access_list = get_allowed_emails()
        
        for record in current_access_list:
            col_row_1, col_row_2 = st.columns([4, 1])
            col_row_1.write(f"• **{record['email']}** (Роль: `{record['role']}`)")
            
            if col_row_2.button("Удалить", key=f"btn_del_access_{record['email']}"):
                delete_allowed_email(record['email'])
                st.rerun()

if __name__ == "__main__":
    main()