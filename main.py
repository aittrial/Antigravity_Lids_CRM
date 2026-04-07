import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta

# Импортируем все функции из нашего database.py
from database import (
    init_db, get_leads, add_lead, update_lead, delete_lead, 
    clear_all_leads, get_allowed_emails, add_allowed_email, 
    delete_allowed_email, set_archive_threshold, archive_single_lead
)
from auth import check_password, logout

# Настройки приложения
APP_TITLE = "📈 Leads_CRM | Lead Management System"
st.set_page_config(page_title=APP_TITLE, layout="wide")

# Инициализация базы данных при запуске
init_db()

# Константы для Telegram
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"

# Списки опций для выбора (Константы)
SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS

COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]

# Цвета и их названия
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def send_telegram_backup(df):
    """Функция отправки бэкапа в Телеграм."""
    try:
        buf_xls = io.BytesIO()
        with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        buf_xls.seek(0)
        
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
        caption = f"📦 CRM BACKUP | 📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': caption}, 
                      files={'document': (f"leads_backup_{date.today()}.xlsx", buf_xls)})
        st.success("✅ Бэкап успешно отправлен в Telegram!")
        return True
    except Exception as e:
        st.error(f"❌ Ошибка при отправке бэкапа: {e}")
        return False

def get_status_color(status):
    """Возвращает HEX-код цвета для фона карточки."""
    colors = {
        "blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", 
        "green": "#C8E6C9", "purple": "#E1BEE7", "pink": "#F8BBD0", "white": "#F0F2F6"
    }
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1, can_archive=False):
    """Отрисовка списка лидов в виде карточек."""
    if not leads_data:
        st.info("По заданным фильтрам ничего не найдено.")
        return

    for i, row in enumerate(leads_data):
        card_color = get_status_color(row['status_color'])
        date_str = row['created_at'].strftime("%d.%m.%Y %H:%M")
        
        # Сама карточка лида
        st.markdown(f'''
            <div style="background-color:{card_color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;">
                <b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_str} | {row["full_name"]} | {row["phone"]}</b>
            </div>
        ''', unsafe_allow_html=True)
        
        # Раскрывающееся меню управления
        with st.expander("📝 Управление лидом"):
            col_wa, col_co, col_ar = st.columns(3)
            
            # Логика WhatsApp
            wa_number = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            clean_phone = ''.join(filter(str.isdigit, str(wa_number)))
            
            with col_wa:
                st.markdown(f'''<a href="https://wa.me/{clean_phone}" target="_blank">
                    <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button>
                </a>''', unsafe_allow_html=True)
            
            with col_co:
                st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}\nКурс: {row['course_name']}", language=None)
            
            with col_ar:
                if can_archive:
                    if st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                        archive_single_lead(row['id'])
                        st.rerun()

            st.divider()
            
            # Форма редактирования внутри карточки
            edit_name = st.text_input("ФИО", row['full_name'], key=f"name_{row['id']}")
            edit_phone = st.text_input("Телефон", row['phone'], key=f"phone_{row['id']}")
            
            c1, c2, c3 = st.columns(3)
            edit_email = c1.text_input("Email", row['email'], key=f"email_{row['id']}")
            edit_time = c2.text_input("Время", row.get('preferred_time', ''), key=f"time_{row['id']}")
            edit_status = c3.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"status_{row['id']}")
            
            if st.button("💾 Сохранить изменения", key=f"save_{row['id']}"):
                update_lead(row['id'], full_name=edit_name, phone=edit_phone, email=edit_email, 
                            status_color=edit_status, preferred_time=edit_time)
                st.success("Изменения сохранены!")
                st.rerun()

def main():
    # Проверка авторизации
    if not check_password():
        return

    # Получаем роль пользователя из сессии
    user_role = st.session_state.get("role", "admin")
    
    st.sidebar.markdown(f"### {APP_TITLE}")
    st.sidebar.write(f"👤 Роль: **{user_role}**")
    
    # Формируем меню навигации
    menu = ["📊 Аналитика"]
    
    if user_role != "analyst":
        menu.append("👥 Список лидов")
        menu.append("➕ Новый лид")
        menu.append("📂 База данных")
        
    if user_role == "superadmin":
        menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    
    if st.sidebar.button("🚪 Выйти из системы"):
        logout()

    # --- РАЗДЕЛ: АНАЛИТИКА ---
    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        all_leads = get_leads(mode="all")
        df_all = pd.DataFrame(all_leads)
        
        if not df_all.empty:
            # 1. ОБЩАЯ СТАТИСТИКА
            st.subheader("📈 Общие показатели (все время)")
            cols_all = st.columns(7)
            cols_all[0].metric("Всего", len(df_all))
            cols_all[1].metric("🔵 Работа", len(df_all[df_all['status_color']=='blue']))
            cols_all[2].metric("🟡 Ждут", len(df_all[df_all['status_color']=='yellow']))
            cols_all[3].metric("🔴 Отказ", len(df_all[df_all['status_color']=='red']))
            cols_all[4].metric("🟢 Возврат", len(df_all[df_all['status_color']=='green']))
            cols_all[5].metric("🟣 Офис", len(df_all[df_all['status_color']=='purple']))
            cols_all[6].metric("💗 Работа 2", len(df_all[df_all['status_color']=='pink']))
            
            st.divider()

            # 2. СТАТИСТИКА ЗА 7 ДНЕЙ
            st.subheader("📅 Статистика за последние 7 дней")
            last_week_date = date.today() - timedelta(days=7)
            df_all['created_date'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['created_date'] >= last_week_date]
            
            cols_week = st.columns(7)
            cols_week[0].metric("Лидов за 7д", len(df_week))
            cols_week[1].metric("🔵", len(df_week[df_week['status_color']=='blue']))
            cols_week[2].metric("🟡", len(df_week[df_week['status_color']=='yellow']))
            cols_week[3].metric("🔴", len(df_week[df_week['status_color']=='red']))
            cols_week[4].metric("🟢", len(df_week[df_week['status_color']=='green']))
            cols_week[5].metric("🟣", len(df_week[df_week['status_color']=='purple']))
            cols_week[6].metric("💗", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            
            # Графики за неделю
            c_left, c_right = st.columns(2)
            
            with c_left:
                if not df_week.empty:
                    src_data = df_week['source'].value_counts().reset_index()
                    fig_src = px.pie(src_data, values='count', names='source', title="Источники лидов (7 дней)", hole=0.4)
                    st.plotly_chart(fig_src, use_container_width=True)
            
            with c_right:
                if not df_week.empty:
                    dyn_data = df_week.groupby('created_date').size().reset_index(name='кол-во')
                    fig_dyn = px.area(dyn_data, x='created_date', y='кол-во', title="Динамика поступления (7 дней)")
                    st.plotly_chart(fig_dyn, use_container_width=True)

            # График по статусам (цветам)
            st.divider()
            st.subheader("🎨 Работа по статусам (7 дней)")
            if not df_week.empty:
                st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
                st_counts.columns = ['Статус', 'Кол-во']
                color_map = {'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}
                fig_bar = px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map=color_map)
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Нет данных для аналитики.")

    # --- РАЗДЕЛ: СПИСОК ЛИДОВ ---
    elif choice == "👥 Список лидов":
        st.header("👥 Управление лидами")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query = f1.text_input("🔍 Поиск по ФИО или Телефону")
        d_range = f2.date_input("📅 Период", value=(date.today() - timedelta(days=30), date.today()))
        c_filt = f3.selectbox("🎨 Фильтр цвета", FILTER_COLOR_MAP)
        src_filt = f4.selectbox("📡 Фильтр источника", FILTER_SOURCE_MAP)
        
        start_d, end_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        
        tab_act, tab_arc = st.tabs(["🔥 Активные (Топ-50)", "📦 Архив"])
        with tab_act:
            active_leads = get_leads(s_query, start_d, end_d, mode="active", status_filter=c_filt, source_filter=src_filt)
            render_leads_list(active_leads, can_archive=True)
        with tab_arc:
            archived_leads = get_leads(s_query, start_d, end_d, mode="archive", status_filter=c_filt, source_filter=src_filt)
            render_leads_list(archived_leads)

    # --- РАЗДЕЛ: НОВЫЙ ЛИД ---
    elif choice == "➕ Новый лид":
        st.header("➕ Добавить новый лид")
        with st.form("new_lead_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_name = col1.text_input("ФИО клиента*")
            f_phone = col2.text_input("Номер телефона*")
            f_email = col1.text_input("Email")
            f_whatsapp = col2.text_input("WhatsApp (если отличается)")
            
            col3, col4 = st.columns(2)
            f_course = col3.selectbox("Курс", COURSE_OPTIONS)
            f_source = col4.selectbox("Источник", SOURCE_OPTIONS)
            
            f_comment = st.text_area("Комментарий")
            
            if st.form_submit_button("🚀 Создать лид"):
                if f_name and f_phone:
                    add_lead(f_name, f_phone, email=f_email, course_name=f_course, source=f_source, comment=f_comment, whatsapp=f_whatsapp)
                    st.success("✅ Лид успешно добавлен в систему!")
                else:
                    st.error("Пожалуйста, заполните ФИО и Телефон.")

    # --- РАЗДЕЛ: БАЗА ДАННЫХ ---
    elif choice == "📂 База данных":
        st.header("📂 Управление базой данных")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.subheader("📥 Экспорт")
            all_leads_data = get_leads(mode="all")
            if all_leads_data:
                df_export = pd.DataFrame(all_leads_data)
                
                # Excel
                towrite = io.BytesIO()
                df_export.to_excel(towrite, index=False, engine='xlsxwriter')
                st.download_button("📥 Скачать Excel (.xlsx)", data=towrite.getvalue(), file_name=f"leads_{date.today()}.xlsx")
                
                # Телеграм Бэкап
                if st.button("🤖 Отправить бэкап в Telegram"):
                    send_telegram_backup(df_export)
                    
        with c2:
            st.subheader("📦 Архивация")
            if user_role == "superadmin":
                if st.button("📦 Отправить ВСЁ в архив"):
                    set_archive_threshold()
                    st.success("Все текущие лиды перенесены в архив.")
                    st.rerun()
            else:
                st.warning("Доступно только суперадмину.")

        with c3:
            st.subheader("🔥 Очистка")
            if user_role == "superadmin":
                # ИСПРАВЛЕНИЕ: Используем checkbox вместо несуществующего st.confirm
                confirm_delete = st.checkbox("Я уверен, что хочу удалить ВСЕ данные")
                if confirm_delete:
                    if st.button("🔥 ПОДТВЕРДИТЬ УДАЛЕНИЕ"):
                        clear_all_leads()
                        st.success("База данных полностью очищена.")
                        st.rerun()

        st.divider()
        st.subheader("🚀 Импорт из Excel")
        uploaded_file = st.file_uploader("Выберите файл .xlsx для загрузки", type=["xlsx"])
        if uploaded_file and st.button("🚀 Начать импорт"):
            try:
                df_import = pd.read_excel(uploaded_file)
                for _, r in df_import.iterrows():
                    add_lead(str(r.get('full_name', '')), str(r.get('phone', '')), source="Excel Import")
                st.success(f"Успешно импортировано {len(df_import)} строк!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка при импорте: {e}")

    # --- РАЗДЕЛ: АДМИНИСТРИРОВАНИЕ ---
    elif choice == "🔑 Администрирование" and user_role == "superadmin":
        st.header("🔑 Управление доступом")
        new_mail = st.text_input("Добавить Email нового сотрудника:")
        new_role = st.selectbox("Назначить роль:", ["admin", "analyst"])
        
        if st.button("✅ Предоставить доступ"):
            if new_mail:
                add_allowed_email(new_mail, new_role)
                st.success(f"Доступ для {new_mail} открыт.")
                st.rerun()

        st.divider()
        st.subheader("Список сотрудников с доступом")
        all_emails = get_allowed_emails()
        for item in all_emails:
            col1, col2 = st.columns([4, 1])
            col1.write(f"• **{item['email']}** | Роль: `{item['role']}`")
            if col2.button("Удалить", key=f"del_{item['email']}"):
                delete_allowed_email(item['email'])
                st.rerun()

if __name__ == "__main__":
    main()