import streamlit as st
import pandas as pd
import plotly.express as px
import io
import requests
import os
from datetime import datetime, date, timedelta

from database import (
    init_db, get_leads, add_lead, update_lead, delete_lead, 
    clear_all_leads, get_allowed_emails, add_allowed_email, 
    delete_allowed_email, set_archive_threshold, archive_single_lead
)
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

def send_telegram_notification(full_name, phone, course, source):
    """Отправка уведомления о новом лиде в Telegram."""
    try:
        text = (
            f"🔔 **Новый лид!**\n\n"
            f"👤 ФИО: {full_name}\n"
            f"📞 Тел: {phone}\n"
            f"📚 Курс: {course}\n"
            f"📡 Источник: {source}\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'})
    except Exception as e:
        st.error(f"Ошибка отправки в Telegram: {e}")

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
        st.markdown(f'<div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;"><b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | {row["full_name"]} | {row["phone"]}</b></div>', unsafe_allow_html=True)
        
        with st.expander("🛠 Управление"):
            c1, c2, c3 = st.columns([1, 2, 1])
            
            # Кнопка WhatsApp
            wa_val = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            p_cl = ''.join(filter(str.isdigit, str(wa_val)))
            with c1: 
                st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            
            # Блок для копирования (Copy to clipboard)
            with c2:
                copy_parts = [f"ФИО: {row['full_name']}", f"Тел: {row['phone']}"]
                if row.get('whatsapp'): copy_parts.append(f"WhatsApp: {row['whatsapp']}")
                if row.get('email'): copy_parts.append(f"Email: {row['email']}")
                if row.get('course_name'): copy_parts.append(f"Курс: {row['course_name']}")
                if row.get('comment'): copy_parts.append(f"Комментарий: {row['comment']}")
                st.code("\n".join(copy_parts), language=None)
            
            with c3:
                if can_archive and st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                    archive_single_lead(row['id']); st.rerun()
            
            st.divider()
            
            # ПОЛЯ УПРАВЛЕНИЯ (ВОССТАНОВЛЕНО)
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                n_fn = st.text_input("Изменить ФИО", row['full_name'], key=f"fn_{row['id']}")
                n_ph = st.text_input("Изменить Тел", row['phone'], key=f"ph_{row['id']}")
                n_wa = st.text_input("Изменить WhatsApp", row.get('whatsapp', ''), key=f"wa_{row['id']}")
            with col_edit2:
                n_em = st.text_input("Изменить Email", row.get('email', ''), key=f"em_{row['id']}")
                n_sc = st.selectbox("Изменить Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"sc_{row['id']}")
                n_cm = st.text_area("Комментарий", row.get('comment', ''), key=f"cm_{row['id']}", height=68)
            
            if st.button("💾 Сохранить изменения", key=f"save_{row['id']}", use_container_width=True):
                update_lead(row['id'], full_name=n_fn, phone=n_ph, whatsapp=n_wa, email=n_em, status_color=n_sc, comment=n_cm)
                st.rerun()

def main():
    if not check_password(): return
    user_role = st.session_state.get("role", "admin")
    
    if 'archive_page_number' not in st.session_state: st.session_state.archive_page_number = 0

    st.sidebar.markdown(f"### {APP_TITLE}")
    
    if user_role == "analyst": menu = ["📊 Аналитика"]
    else:
        menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
        if user_role == "superadmin": menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        all_leads = get_leads(mode="all")
        df_all = pd.DataFrame(all_leads)
        if not df_all.empty:
            st.subheader("📈 Общая статистика")
            m1 = st.columns(7)
            m1[0].metric("Всего", len(df_all))
            m1[1].metric("🔵", len(df_all[df_all['status_color']=='blue'])); m1[2].metric("🟡", len(df_all[df_all['status_color']=='yellow'])); m1[3].metric("🔴", len(df_all[df_all['status_color']=='red'])); m1[4].metric("🟢", len(df_all[df_all['status_color']=='green'])); m1[5].metric("🟣", len(df_all[df_all['status_color']=='purple'])); m1[6].metric("💗", len(df_all[df_all['status_color']=='pink']))
            
            st.divider()
            st.subheader("📅 За 7 дней")
            last_w = date.today() - timedelta(days=7)
            df_all['d_only'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['d_only'] >= last_w]
            m2 = st.columns(7)
            m2[0].metric("Новых", len(df_week)); m2[1].metric("🔵", len(df_week[df_week['status_color']=='blue'])); m2[2].metric("🟡", len(df_week[df_week['status_color']=='yellow'])); m2[3].metric("🔴", len(df_week[df_week['status_color']=='red'])); m2[4].metric("🟢", len(df_week[df_week['status_color']=='green'])); m2[5].metric("🟣", len(df_week[df_week['status_color']=='purple'])); m2[6].metric("💗", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.pie(df_week['source'].value_counts().reset_index(), values='count', names='source', title="Источники", hole=0.4), use_container_width=True)
            with c2: st.plotly_chart(px.area(df_week.groupby('d_only').size().reset_index(name='count'), x='d_only', y='count', title="Динамика"), use_container_width=True)
            
            st.divider()
            st.subheader("🎨 Статусы (7 дней)")
            st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
            st_counts.columns = ['Статус', 'Кол-во']
            c_map = {'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}
            st.plotly_chart(px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map=c_map), use_container_width=True)
        else: st.info("База пуста")

    elif choice == "👥 Список лидов":
        st.header("👥 Лиды")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query = f1.text_input("🔍 Поиск")
        d_range = f2.date_input("📅 Даты", value=(date.today()-timedelta(days=30), date.today()))
        c_filt, src_filt = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP), f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        
        t1, t2 = st.tabs(["🔥 Активные", "📦 Архив"])
        with t1:
            data_active = get_leads(s_query, st_d, en_d, mode="active", status_filter=c_filt, source_filter=src_filt, limit=50, offset=0)
            render_leads_list(data_active, start_order=1, can_archive=True)

        with t2:
            l_per_page = 50
            c_off = st.session_state.archive_page_number * l_per_page
            data_archive = get_leads(s_query, st_d, en_d, mode="archive", status_filter=c_filt, source_filter=src_filt, limit=l_per_page, offset=c_off)
            render_leads_list(data_archive, start_order=c_off + 1)
            
            st.write("---")
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                if st.button("⬅️ Назад", key="btn_arc_p") and st.session_state.archive_page_number > 0:
                    st.session_state.archive_page_number -= 1; st.rerun()
            with nav2: st.markdown(f"<center>Страница {st.session_state.archive_page_number + 1}</center>", unsafe_allow_html=True)
            with nav3:
                if len(data_archive) >= 50:
                    if st.button("Вперед ➡️", key="btn_arc_n"):
                        st.session_state.archive_page_number += 1; st.rerun()
                else: st.write("Конец")

    elif choice == "➕ Новый лид":
        st.header("➕ Новый лид")
        with st.form("f_new"):
            fn = st.text_input("ФИО")
            ph = st.text_input("Тел")
            crs = st.selectbox("Курс", COURSE_OPTIONS)
            src = st.selectbox("Источник", SOURCE_OPTIONS)
            if st.form_submit_button("Создать"):
                if fn and ph:
                    add_lead(fn, ph, course_name=crs, source=src)
                    send_telegram_notification(fn, ph, crs, src)
                    st.success("✅ Добавлен и отправлен в Telegram!"); st.rerun()

    elif choice == "📂 База данных":
        st.header("📂 База данных")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("📥 Экспорт")
            all_l = get_leads(mode="all")
            if all_l:
                df_ex = pd.DataFrame(all_l)
                towrite = io.BytesIO()
                df_ex.to_excel(towrite, index=False, engine='xlsxwriter')
                st.download_button("📥 Скачать Excel", data=towrite.getvalue(), file_name=f"export_{date.today()}.xlsx", use_container_width=True)
                
                if st.button("🤖 Отправить бэкап в Telegram", use_container_width=True):
                    try:
                        buf_xls = io.BytesIO()
                        with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as writer:
                            df_ex.to_excel(writer, index=False)
                        buf_xls.seek(0)
                        
                        buf_csv = io.BytesIO()
                        df_ex.to_csv(buf_csv, index=False, encoding='utf-8-sig')
                        buf_csv.seek(0)
                        
                        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
                        ts = datetime.now().strftime('%d.%m.%Y %H:%M')
                        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': f"📦 Excel Backup | 📅 {ts}"}, files={'document': (f"leads_backup_{date.today()}.xlsx", buf_xls)})
                        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': f"📄 CSV Backup | 📅 {ts}"}, files={'document': (f"leads_backup_{date.today()}.csv", buf_csv)})
                        st.success("✅ Бэкап отправлен (Excel + CSV)!")
                    except Exception as e:
                        st.error(f"Ошибка отправки: {e}")

        with c2:
            st.subheader("📦 Архивация")
            if user_role in ["admin", "superadmin"]:
                if st.button("📦 ВСЕ В АРХИВ", use_container_width=True):
                    set_archive_threshold(); st.rerun()
        with c3:
            st.subheader("🔥 Очистка")
            if user_role == "superadmin":
                conf = st.checkbox("Подтверждаю очистку")
                if st.button("🔥 УДАЛИТЬ ВСЁ", disabled=not conf, use_container_width=True):
                    clear_all_leads(); st.rerun()
        st.divider()
        st.subheader("🚀 Импорт")
        up_f = st.file_uploader("Загрузите .xlsx", type=["xlsx"])
        if up_f and st.button("🚀 Начать", use_container_width=True):
            try:
                df_im = pd.read_excel(up_f)
                for _, r in df_im.iterrows():
                    add_lead(str(r.get('full_name','')), str(r.get('phone','')), source="Excel Import")
                st.success("✅ Импорт завершен!"); st.rerun()
            except Exception as e: st.error(f"Ошибка: {e}")

    elif choice == "🔑 Администрирование" and user_role == "superadmin":
        st.header("🔑 Доступы")
        nm, nr = st.text_input("Email:"), st.selectbox("Роль:", ["admin", "analyst"])
        if st.button("Добавить"): add_allowed_email(nm, nr); st.rerun()
        st.divider()
        for e in get_allowed_emails():
            col1, col2 = st.columns([4, 1])
            col1.write(f"• {e['email']} ({e['role']})")
            if col2.button("Удалить", key=f"del_{e['email']}", use_container_width=True): delete_allowed_email(e['email']); st.rerun()

if __name__ == "__main__": main()