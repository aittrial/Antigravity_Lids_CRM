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

# ТВОИ ДАННЫЕ TELEGRAM (Прописаны жестко для надежности)
TELE_TOKEN = "8500719540:AAG3KzK7aP3FyZoE-QmRPysKJKEO9KAHWwU"
TELE_CHAT_ID = "-1003793353079"

SOURCE_OPTIONS = ["Meta", "Google Landing", "Google Quiz", "Google", "Google leadform", "chatgpt.com", "Other"]
FILTER_SOURCE_MAP = ["Все"] + SOURCE_OPTIONS

COURSE_OPTIONS = ["QA testing", "Programming", "QA testing AIT", "Programming AIT", "Both", "Accounting", "Free course", "Other"]
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple", "pink"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый", "Розовый"]

def send_telegram_backup(df):
    try:
        # XLSX
        buf_xls = io.BytesIO()
        with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        buf_xls.seek(0)

        # CSV
        buf_csv = io.BytesIO()
        df.to_csv(buf_csv, index=False, encoding='utf-8-sig')
        buf_csv.seek(0)
        
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendDocument"
        caption = f"📦 CRM FULL BACKUP (XLSX + CSV)\n📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n👥 Лидов в базе: {len(df)}"
        
        # Отправка XLSX
        requests.post(url, data={'chat_id': TELE_CHAT_ID, 'caption': caption}, files={'document': (f"leads_backup_{date.today()}.xlsx", buf_xls)})
        # Отправка CSV
        res2 = requests.post(url, data={'chat_id': TELE_CHAT_ID}, files={'document': (f"leads_backup_{date.today()}.csv", buf_csv)})
        
        return (True, "✅ Оба файла отправлены в Telegram!") if res2.status_code == 200 else (False, "❌ Ошибка отправки.")
    except Exception as e: return False, f"❌ Ошибка бэкапа: {e}"

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
            p_cl = ''.join(filter(str.isdigit, str(row['phone'])))
            with c_wa: st.markdown(f'''<a href="https://wa.me/{p_cl}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with c_co: st.code(f"ФИО: {row['full_name']}\nТел: {row['phone']}\nКурс: {row['course_name']}", language=None)
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

    # --- АНАЛИТИКА ---
    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        all_leads = get_leads(mode="all")
        df_all = pd.DataFrame(all_leads)
        if not df_all.empty:
            m = st.columns(7)
            m[0].metric("Всего", len(df_all))
            m[1].metric("🔵 Работа", len(df_all[df_all['status_color']=='blue']))
            m[2].metric("🟡 Ждут", len(df_all[df_all['status_color']=='yellow']))
            m[3].metric("🔴 Отказ", len(df_all[df_all['status_color']=='red']))
            m[4].metric("🟢 Возврат", len(df_all[df_all['status_color']=='green']))
            m[5].metric("🟣 Офис", len(df_all[df_all['status_color']=='purple']))
            m[6].metric("💗 Работа 2", len(df_all[df_all['status_color']=='pink']))
            st.divider()
            last_week = date.today() - timedelta(days=7)
            c_l, c_r = st.columns(2)
            with c_l:
                df_act = pd.DataFrame(get_leads(mode="active"))
                if not df_act.empty:
                    df_act['day'] = pd.to_datetime(df_act['created_at']).dt.date
                    dyn = df_act[df_act['day'] >= last_week].groupby('day').size().reset_index(name='лидов')
                    st.plotly_chart(px.area(dyn, x='day', y='лидов', title="Динамика (Активные за 7 дней)"), use_container_width=True)
            with c_r:
                df_w = df_all[pd.to_datetime(df_all['created_at']).dt.date >= last_week]
                if not df_w.empty:
                    st_c = df_w[df_w['status_color'] != 'white']['status_color'].value_counts().reset_index()
                    st_c.columns = ['Статус', 'Кол-во']
                    st.plotly_chart(px.bar(st_c, x='Кол-во', y='Статус', orientation='h', color='Статус', color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','green':'#C8E6C9','purple':'#E1BEE7','pink':'#F8BBD0'}, template="plotly_white"), use_container_width=True)
                    st.markdown(f"⚪ **Новые (белые) за неделю:** `{len(df_w[df_w['status_color'] == 'white'])}`")
        else: st.info("База пуста")

    # --- СПИСОК ЛИДОВ ---
    elif choice == "👥 Список лидов":
        st.header("👥 Работа с лидами")
        f1, f2, f3, f4 = st.columns([2, 1.2, 1, 1])
        search, dr = f1.text_input("🔍 Поиск"), f2.date_input("📅 Дата", value=(date.today()-timedelta(days=30), date.today()))
        color_f, source_f = f3.selectbox("🎨 Статус", FILTER_COLOR_MAP), f4.selectbox("📡 Источник", FILTER_SOURCE_MAP)
        st_d, en_d = (dr[0], dr[1]) if len(dr) == 2 else (None, None)
        t1, t2 = st.tabs(["🔥 Активные (ТОП-50)", "📦 Архив"])
        with t1: render_leads_list(get_leads(search, st_d, en_d, mode="active", status_filter=color_f, source_filter=source_f), can_archive=True)
        with t2:
            arch = get_leads(search, st_d, en_d, mode="archive", status_filter=color_f, source_filter=source_f)
            if arch:
                pg = st.number_input("Страница", 1, max(1, len(arch)//50 + 1))
                render_leads_list(arch[(pg-1)*50 : pg*50])

    # --- НОВЫЙ ЛИД ---
    elif choice == "➕ Новый лид":
        st.header("➕ Новый лид")
        with st.form("add_f", clear_on_submit=True):
            c1, c2 = st.columns(2); n, p = c1.text_input("ФИО"), c2.text_input("Тел")
            c3, c4 = st.columns(2); e, t = c3.text_input("Email"), c4.text_input("Время")
            c5, c6 = st.columns(2); cur, src = c5.selectbox("Курс", COURSE_OPTIONS), c6.selectbox("Источник", SOURCE_OPTIONS)
            s, comm = st.selectbox("Статус", COLOR_KEYS), st.text_area("Комментарий")
            if st.form_submit_button("Создать"):
                if n and p: add_lead(n, p, e, cur, t, src, comm, s); st.success("Лид добавлен!"); st.rerun()

    # --- БАЗА ДАННЫХ ---
    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c1, c2, c3 = st.columns(3)
        all_data = get_leads(mode="all")
        with c1:
            st.subheader("📥 Экспорт")
            if all_data:
                df = pd.DataFrame(all_data)
                # XLSX
                buf_xls = io.BytesIO()
                with pd.ExcelWriter(buf_xls, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
                st.download_button("📥 Excel (.xlsx)", data=buf_xls.getvalue(), file_name=f"leads_{date.today()}.xlsx", mime="application/vnd.ms-excel")
                # CSV
                st.download_button("📥 CSV (.csv)", data=df.to_csv(index=False).encode('utf-8-sig'), file_name=f"leads_{date.today()}.csv", mime="text/csv")
                st.divider()
                if st.button("🤖 Бэкап в Telegram (XLSX + CSV)"):
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
        
        # --- ВОЗВРАЩЕННЫЙ БЛОК ИМПОРТА ---
        st.divider()
        st.subheader("🚀 Импорт из Excel")
        up = st.file_uploader("Выберите XLSX файл для загрузки", type=["xlsx"])
        if up and st.button("🚀 Загрузить данные в базу"):
            try:
                df_up = pd.read_excel(up, header=None)
                for _, r in df_up.iterrows():
                    v = list(r.values)
                    # Формат: ФИО(1), Тел(2), Email(3), Курс(4), Время(5), Источник(6), Коммент(7)
                    if len(v) >= 3:
                        add_lead(str(v[1]), str(v[2]), str(v[3]) if len(v)>3 else '', 
                                 str(v[4]) if len(v)>4 else '', str(v[5]) if len(v)>5 else '', 
                                 str(v[6]) if len(v)>6 else '', str(v[7]) if len(v)>7 else 'Excel Import')
                st.success("✅ Импорт завершен успешно!"); st.rerun()
            except Exception as e: st.error(f"❌ Ошибка импорта: {e}")

    elif choice == "🔑 Администрирование" and st.session_state.get("role") == "superadmin":
        st.header("🔑 Доступы")
        new_m = st.text_input("Email:")
        if st.button("Добавить"): add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1]); c1.write(f"• {e}")
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__": main()