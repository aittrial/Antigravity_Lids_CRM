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

# ТОКЕНЫ И ID (ТВОИ ДАННЫЕ)
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"

SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS

COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def send_telegram_backup(df):
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
        files = {'document': (f"leads_backup_{date.today()}.xlsx", output)}
        data = {'chat_id': TELE_CHAT_ID, 'caption': f"📦 CRM FULL BACKUP\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n👥 Лидов: {len(df)}"}
        res = requests.post(url, data=data, files=files)
        return (True, "✅ Бэкап отправлен!") if res.status_code == 200 else (False, f"❌ Ошибка: {res.text}")
    except Exception as e: return False, f"❌ Ошибка: {e}"

def get_status_color(status):
    colors = {
        "blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", 
        "green": "#C8E6C9", "purple": "#E1BEE7", "pink": "#F8BBD0", "white": "#F0F2F6"
    }
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
            p_cl = ''.join(filter(str.isdigit, str(row['phone'])))
            with c_wa: st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c_co: st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}\nEmail: {row['email']}\nКурс: {row['course_name']}", language=None)
            with c_ar:
                if can_archive and st.button("📦 В архив", key=f"arch_{row['id']}"):
                    archive_single_lead(row['id']); st.rerun()
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            n, p, e = c1.text_input("ФИО", row['full_name'], key=f"n_{row['id']}"), c2.text_input("Тел", row['phone'], key=f"p_{row['id']}"), c3.text_input("Email", row['email'], key=f"e_{row['id']}")
            c4, c5, c6 = st.columns(3)
            cur_idx = COURSE_OPTIONS.index(row['course_name']) if row['course_name'] in COURSE_OPTIONS else COURSE_OPTIONS.index("Other")
            c_sel = c4.selectbox("Курс", COURSE_OPTIONS, index=cur_idx, key=f"cs_{row['id']}")
            curr_c = c4.text_input("Уточните", row['course_name'], key=f"c_m_{row['id']}") if c_sel == "Other" else c_sel
            curr_t, curr_s = c5.text_input("Время", row.get('preferred_time',''), key=f"t_{row['id']}"), c6.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"s_{row['id']}")
            c7, c8 = st.columns(2)
            src_val = row.get('source', 'Other')
            src_idx = SOURCE_OPTIONS.index(src_val) if src_val in SOURCE_OPTIONS else SOURCE_OPTIONS.index("Other")
            src_sel = c7.selectbox("Источник", SOURCE_OPTIONS, index=src_idx, key=f"srcs_{row['id']}")
            curr_src = c7.text_input("Уточните источник", src_val, key=f"srcm_{row['id']}") if src_sel == "Other" else src_sel
            curr_com = c8.text_area("Комментарий", row['comment'] or "", key=f"com_{row['id']}", height=100)
            if st.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=n, phone=p, email=e, course_name=curr_c, preferred_time=curr_t, status_color=curr_s, comment=curr_com, source=curr_src); st.rerun()

def main():
    if not check_password(): return
    st.sidebar.markdown(f"### {APP_TITLE}")
    menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
    if st.session_state.get("role") == "superadmin": menu.append("🔑 Администрирование")
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    # --- АНАЛИТИКА (v6.8 Улучшенная) ---
    if choice == "📊 Аналитика":
        st.header("📊 Точечная аналитика (за 7 дней)")
        last_week = date.today() - timedelta(days=7)
        
        # 1. Данные для ДИНАМИКИ (только ТОП-50 активных)
        active_top_50 = get_leads(mode="active")
        df_active = pd.DataFrame(active_top_50)
        
        # 2. Данные для СТАТУСОВ (все за неделю)
        all_leads_week = get_leads(start_date=last_week, mode="all")
        df_week = pd.DataFrame(all_leads_week)

        c_left, c_right = st.columns(2)

        with c_left:
            st.subheader("📈 Динамика (Активные ТОП-50)")
            if not df_active.empty:
                df_active['day'] = pd.to_datetime(df_active['created_at']).dt.date
                # Фильтруем активные только за последнюю неделю
                df_active_week = df_active[df_active['day'] >= last_week]
                dynamic_data = df_active_week.groupby('day').size().reset_index(name='лидов')
                fig_dyn = px.area(dynamic_data, x='day', y='лидов', title="Поступление активных", template="plotly_white")
                st.plotly_chart(fig_dyn, use_container_width=True)
            else: st.info("Нет активных лидов")

        with c_right:
            st.subheader("🎨 Распределение статусов (Неделя)")
            if not df_week.empty:
                # Исключаем белых
                df_colored = df_week[df_week['status_color'] != 'white']
                status_counts = df_colored['status_color'].value_counts().reset_index()
                status_counts.columns = ['Статус', 'Кол-во']
                
                fig_stat = px.bar(status_counts, x='Кол-во', y='Статус', orientation='h', color='Статус',
                                  color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'},
                                  template="plotly_white")
                st.plotly_chart(fig_stat, use_container_width=True)
                
                # Показываем белых числом
                white_count = len(df_week[df_week['status_color'] == 'white'])
                st.markdown(f"⚪ **Необработанные (белые) за неделю:** `{white_count}`")
            else: st.info("Нет данных за неделю")

    # --- СПИСОК ЛИДОВ (v6.8 + Фильтр Источников) ---
    elif choice == "👥 Список лидов":
        st.header("👥 Работа с лидами")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        search = f1.text_input("🔍 Поиск")
        dr = f2.date_input("📅 Дата", value=(date.today()-timedelta(days=30), date.today()))
        color_f = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP)
        source_f = f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        
        st_d, en_d = (dr[0], dr[1]) if len(dr) == 2 else (None, None)
        st.divider()

        t1, t2 = st.tabs(["🔥 Активные (ТОП-50)", "📦 Весь Архив"])
        with t1: render_leads_list(get_leads(search, st_d, en_d, mode="active", status_filter=color_f, source_filter=source_f), can_archive=True)
        with t2:
            arch = get_leads(search, st_d, en_d, mode="archive", status_filter=color_f, source_filter=source_f)
            if arch:
                pg = st.number_input("Страница архива", 1, max(1, len(arch)//50 + 1))
                render_leads_list(arch[(pg-1)*50 : pg*50])

    # --- НОВЫЙ ЛИД (v6.8 + Розовый статус) ---
    elif choice == "➕ Новый лид":
        st.header("➕ Добавить лид")
        with st.form("add_f", clear_on_submit=True):
            c1, c2 = st.columns(2); n, p = c1.text_input("ФИО"), c2.text_input("Тел")
            c3, c4 = st.columns(2); e, t = c3.text_input("Email"), c4.text_input("Время")
            c5, c6 = st.columns(2); cur, src = c5.selectbox("Курс", COURSE_OPTIONS), c6.selectbox("Источник", SOURCE_OPTIONS)
            s = st.selectbox("Статус (Цвет)", COLOR_KEYS)
            comm = st.text_area("Комментарий")
            if st.form_submit_button("Создать"):
                if n and p: add_lead(n, p, e, cur, t, src, comm, s); st.success("Лид в базе!"); st.rerun()
                else: st.error("Имя и Телефон!")

    # --- БАЗА ДАННЫХ ---
    elif choice == "📂 База данных":
        st.header("📂 Управление")
        c1, c2, c3 = st.columns(3)
        all_data = get_leads(mode="all")
        with c1:
            st.subheader("📥 Экспорт")
            if all_data:
                df = pd.DataFrame(all_data)
                st.download_button("📥 Excel", data=io.BytesIO(pd.ExcelWriter(io.BytesIO(), engine='xlsxwriter').book.read()).getvalue(), file_name="leads.xlsx")
                if st.button("🤖 Бэкап в Telegram"):
                    ok, msg = send_telegram_backup(df)
                    st.success(msg) if ok else st.error(msg)
        with c2:
            st.subheader("📦 Архивация")
            if st.session_state.get("role") == "superadmin" and st.button("📦 ВСЁ В АРХИВ"):
                set_archive_threshold(); st.rerun()
        with c3:
            st.subheader("🔥 Очистка")
            if st.session_state.get("role") == "superadmin" and st.button("🔥 УДАЛИТЬ ВСЁ"):
                clear_all_leads(); st.rerun()

    # --- АДМИНЫ ---
    elif choice == "🔑 Администрирование" and st.session_state.get("role") == "superadmin":
        st.header("🔑 Доступы")
        new_m = st.text_input("Email:")
        if st.button("Добавить"): add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1]); c1.write(f"• {e}")
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__": main()