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

# ТВОИ ДАННЫЕ TELEGRAM
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
        buf_csv = io.BytesIO()
        df.to_csv(buf_csv, index=False, encoding='utf-8-sig')
        buf_csv.seek(0)
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
        cap = f"📦 CRM FULL BACKUP\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n👥 Лидов: {len(df)}"
        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': cap}, files={'document': (f"leads_backup_{date.today()}.xlsx", buf_xls)})
        res2 = requests.post(url, data={'chat_id': TELE_CHAT_ID}, files={'document': (f"leads_backup_{date.today()}.csv", buf_csv)})
        if res2.status_code == 200:
            return True, "Оба файла отправлены в Telegram!"
        return False, f"Ошибка Telegram: {res2.text}"
    except Exception as e:
        return False, f"Ошибка: {e}"

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
        pref_time = row.get('preferred_time', '---')
        st.markdown(f'<div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;"><b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | 🕒 {pref_time} | {row["full_name"]} | {row["phone"]}</b></div>', unsafe_allow_html=True)
        with st.expander("Управление"):
            c_wa, c_co, c_ar = st.columns(3)
            wa_raw = row.get('whatsapp') if row.get('whatsapp') else row['phone']
            p_cl = ''.join(filter(str.isdigit, str(wa_raw)))
            with c_wa: st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c_co: st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}\nWA: {row.get('whatsapp','')}\nКурс: {row['course_name']}", language=None)
            with c_ar:
                if can_archive and st.button("📦 В архив", key=f"arch_btn_{row['id']}"):
                    archive_single_lead(row['id']); st.rerun()
            st.divider()
            c1, c2, c3 = st.columns(3)
            un, up, uwa = c1.text_input("ФИО", row['full_name'], key=f"n_{row['id']}"), c2.text_input("Тел", row['phone'], key=f"p_{row['id']}"), c3.text_input("WhatsApp", row.get('whatsapp', ''), key=f"wa_{row['id']}")
            c4, c5, c6 = st.columns(3)
            ue, ut, us = c4.text_input("Email", row['email'], key=f"e_{row['id']}"), c5.text_input("Время", row.get('preferred_time',''), key=f"t_{row['id']}"), c6.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']) if row['status_color'] in COLOR_KEYS else 0, key=f"s_{row['id']}")
            c7, c8 = st.columns(2)
            cur_idx = COURSE_OPTIONS.index(row['course_name']) if row['course_name'] in COURSE_OPTIONS else COURSE_OPTIONS.index("Other")
            c_sel = c7.selectbox("Курс", COURSE_OPTIONS, index=cur_idx, key=f"cs_{row['id']}")
            curr_c = c7.text_input("Уточните курс", row['course_name'], key=f"cm_{row['id']}") if c_sel == "Other" else c_sel
            src_val = row.get('source', 'Other')
            src_idx = SOURCE_OPTIONS.index(src_val) if src_val in SOURCE_OPTIONS else SOURCE_OPTIONS.index("Other")
            src_sel = c8.selectbox("Источник", SOURCE_OPTIONS, index=src_idx, key=f"srcs_{row['id']}")
            curr_src = c8.text_input("Уточните источник", src_val, key=f"srcm_{row['id']}") if src_sel == "Other" else src_sel
            ucom = st.text_area("Комментарий", row['comment'] or "", key=f"com_{row['id']}", height=100)
            if st.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=un, phone=up, email=ue, course_name=curr_c, preferred_time=ut, status_color=us, comment=ucom, source=curr_src, whatsapp=uwa); st.rerun()

def main():
    if not check_password(): return
    user_role = st.session_state.get("role")
    
    st.sidebar.markdown(f"### {APP_TITLE}")
    
    # Роли доступа
    if user_role == "analyst":
        menu = ["📊 Аналитика"]
    else:
        menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
        if user_role == "superadmin": menu.append("🔑 Администрирование")
            
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        df_all = pd.DataFrame(get_leads(mode="all"))
        
        if not df_all.empty:
            # 1. СТАТИСТИКА ЗА ВСЁ ВРЕМЯ (Твоя оригинальная строка)
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

            # 2. СТАТИСТИКА ЗА 7 ДНЕЙ (Новая строка)
            st.subheader("📅 Статистика за последние 7 дней")
            last_w_date = date.today() - timedelta(days=7)
            df_all['created_at_dt'] = pd.to_datetime(df_all['created_at']).dt.date
            df_week = df_all[df_all['created_at_dt'] >= last_w_date]
            
            m_week = st.columns(7)
            m_week[0].metric("Всего", len(df_week))
            m_week[1].metric("🔵 Работа", len(df_week[df_week['status_color']=='blue']))
            m_week[2].metric("🟡 Ждут", len(df_week[df_week['status_color']=='yellow']))
            m_week[3].metric("🔴 Отказ", len(df_week[df_week['status_color']=='red']))
            m_week[4].metric("🟢 Возврат", len(df_week[df_week['status_color']=='green']))
            m_week[5].metric("🟣 Офис", len(df_week[df_week['status_color']=='purple']))
            m_week[6].metric("💗 Работа 2", len(df_week[df_week['status_color']=='pink']))

            st.divider()
            
            col_src, col_dyn = st.columns(2)
            
            # График по источникам (СТРОГО за неделю)
            with col_src:
                if not df_week.empty:
                    src_counts = df_week['source'].value_counts().reset_index()
                    src_counts.columns = ['Источник', 'Кол-во']
                    fig_pie = px.pie(src_counts, values='Кол-во', names='Источник', title="Источники лидов (ПОСЛЕДНИЕ 7 ДНЕЙ)", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Нет данных по источникам за неделю.")
            
            # Динамика (за неделю)
            with col_dyn:
                if not df_week.empty:
                    dyn = df_week.groupby('created_at_dt').size().reset_index(name='лидов')
                    st.plotly_chart(px.area(dyn, x='created_at_dt', y='лидов', title="Динамика новых лидов (7 дней)"), use_container_width=True)
            
            st.divider()
            # Бары по статусам (за неделю)
            if not df_week.empty:
                st_counts = df_week[df_week['status_color'] != 'white']['status_color'].value_counts().reset_index()
                st_counts.columns = ['Статус', 'Кол-во']
                st.plotly_chart(px.bar(st_counts, x='Кол-во', y='Статус', orientation='h', color='Статус', 
                                     color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}, 
                                     title="Работа по статусам (ПОСЛЕДНИЕ 7 ДНЕЙ)"), use_container_width=True)
        else: st.info("База пуста")

    # --- Другие разделы ---
    elif choice == "👥 Список лидов":
        st.header("👥 Лиды")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        s_query, d_range = f1.text_input("🔍 Поиск"), f2.date_input("📅 Дата", value=(date.today()-timedelta(days=30), date.today()))
        c_filt, src_filt = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP), f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        t1, t2 = st.tabs(["🔥 Активные (ТОП-50)", "📦 Архив"])
        with t1: render_leads_list(get_leads(s_query, st_d, en_d, mode="active", status_filter=c_filt, source_filter=src_filt), can_archive=True)
        with t2:
            arch = get_leads(s_query, st_d, en_d, mode="archive", status_filter=c_filt, source_filter=src_filt)
            if arch:
                pg = st.number_input("Страница", 1, max(1, len(arch)//50 + 1))
                render_leads_list(arch[(pg-1)*50 : pg*50])

    elif choice == "➕ Новый лид":
        st.header("➕ Новый лид")
        with st.form("new_lead_form", clear_on_submit=True):
            c1, c2 = st.columns(2); fn, ph = c1.text_input("ФИО"), c2.text_input("Тел")
            c3, c4 = st.columns(2); em, tm = c3.text_input("Email"), c4.text_input("Время")
            wa = st.text_input("WhatsApp (если другой)")
            c5, c6 = st.columns(2); crs, src = c5.selectbox("Курс", COURSE_OPTIONS), c6.selectbox("Источник", SOURCE_OPTIONS)
            stt, cmm = st.selectbox("Статус", COLOR_KEYS), st.text_area("Комментарий")
            if st.form_submit_button("Создать"):
                if fn and ph: add_lead(fn, ph, em, crs, tm, src, cmm, stt, whatsapp=wa); st.success("Добавлено!"); st.rerun()

    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c1, c2, c3 = st.columns(3)
        all_l = get_leads(mode="all")
        with c1:
            st.subheader("📥 Экспорт")
            if all_l:
                df_ex = pd.DataFrame(all_l)
                bx = io.BytesIO()
                with pd.ExcelWriter(bx, engine='xlsxwriter') as wr: df_ex.to_excel(wr, index=False)
                st.download_button("📥 Excel (.xlsx)", data=bx.getvalue(), file_name=f"leads_{date.today()}.xlsx")
                st.download_button("📥 CSV (.csv)", data=df_ex.to_csv(index=False).encode('utf-8-sig'), file_name=f"leads_{date.today()}.csv")
                st.divider()
                if st.button("🤖 Бэкап в Telegram"):
                    ok, msg = send_telegram_backup(df_ex)
                    if ok: st.success(msg)
                    else: st.error(msg)
        with c2:
            st.subheader("📦 Архивация")
            if user_role == "superadmin" and st.button("📦 ВСЁ В АРХИВ"):
                set_archive_threshold(); st.rerun()
        with c3:
            st.subheader("🔥 Очистка")
            if user_role == "superadmin" and st.button("🔥 УДАЛИТЬ ВСЁ"):
                clear_all_leads(); st.rerun()

    elif choice == "🔑 Администрирование" and user_role == "superadmin":
        st.header("🔑 Доступы")
        c1, c2 = st.columns([3, 1])
        new_mail = c1.text_input("Новый email:")
        # Здесь мы пока просто добавляем мейл. Если хочешь хранить роли в БД, 
        # нужно обновить database.py (добавить колонку role в allowed_emails)
        if st.button("Добавить доступ"):
            add_allowed_email(new_mail); st.success("Добавлено!"); st.rerun()
        st.divider()
        for email in get_allowed_emails():
            col1, col2 = st.columns([4, 1])
            col1.write(f"• {email}")
            if col2.button("Удалить", key=f"del_{email}"):
                delete_allowed_email(email); st.rerun()

if __name__ == "__main__": main()