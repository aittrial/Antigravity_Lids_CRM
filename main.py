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
COLOR_KEYS = ["white", "blue", "yellow", "red", "green", "purple"]
FILTER_COLOR_MAP = ["Все", "Белый", "Синий", "Желтый", "Красный", "Зеленый", "Фиолетовый"]

def get_status_color(status):
    colors = {"blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", "green": "#C8E6C9", "purple": "#E1BEE7", "white": "#F0F2F6"}
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1):
    if not leads_data:
        st.info("По заданным фильтрам ничего не найдено.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        pref_time = row.get('preferred_time', '---')
        st.markdown(f'<div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: black !important;"><b style="color: black !important; font-size: 14px;">#{start_order+i} | 📅 {date_s} | 🕒 {pref_time} | {row["full_name"]} | {row["phone"]}</b></div>', unsafe_allow_html=True)
        with st.expander("Управление"):
            col_wa, col_copy = st.columns([1, 1])
            p_clean = ''.join(filter(str.isdigit, str(row['phone'])))
            with col_wa: st.markdown(f'''<a href="https://wa.me/{p_clean}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            with col_copy:
                txt = f"--- ДАННЫЕ ЛИДА ---\nФИО: {row['full_name']}\nТелефон: {row['phone']}\nEmail: {row['email']}\nКурс: {row['course_name']}"
                st.code(txt, language=None)
            st.divider()
            c1, c2, c3 = st.columns(3)
            n, p, e = c1.text_input("ФИО", row['full_name'], key=f"n_{row['id']}"), c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}"), c3.text_input("Email", row['email'], key=f"e_{row['id']}")
            c4, c5, c6 = st.columns(3)
            cur_c_idx = COURSE_OPTIONS.index(row['course_name']) if row['course_name'] in COURSE_OPTIONS else COURSE_OPTIONS.index("Other")
            curr_c_sel = c4.selectbox("Курс", COURSE_OPTIONS, index=cur_c_idx, key=f"cs_{row['id']}")
            curr_c = c4.text_input("Уточните", row['course_name'], key=f"c_man_{row['id']}") if curr_c_sel == "Other" else curr_c_sel
            curr_t = c5.text_input("Время", row.get('preferred_time', ''), key=f"t_{row['id']}")
            curr_s = c6.selectbox("Статус", COLOR_KEYS, index=COLOR_KEYS.index(row['status_color']), key=f"s_{row['id']}")
            c7, c8 = st.columns(2)
            src_val = row.get('source', 'Other')
            cur_src_idx = SOURCE_OPTIONS.index(src_val) if src_val in SOURCE_OPTIONS else SOURCE_OPTIONS.index("Other")
            curr_src_sel = c7.selectbox("Источник", SOURCE_OPTIONS, index=cur_src_idx, key=f"srcs_{row['id']}")
            curr_src = c7.text_input("Уточните источник", src_val, key=f"srcm_{row['id']}") if curr_src_sel == "Other" else curr_src_sel
            curr_comm = c8.text_area("Комментарий", row['comment'] if row['comment'] else "", key=f"com_{row['id']}", height=100)
            bs, bd = st.columns([1, 5])
            if bs.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=n, phone=p, email=e, course_name=curr_c, preferred_time=curr_t, status_color=curr_s, comment=curr_comm, source=curr_src); st.rerun()
            if st.session_state.get("role") == "superadmin" and bd.button("🗑️ Удалить", key=f"del_{row['id']}"):
                delete_lead(row['id']); st.rerun()

def main():
    if not check_password(): return
    st.sidebar.markdown(f"### {APP_TITLE}")
    menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
    if st.session_state.get("role") == "superadmin": menu.append("🔑 Администрирование")
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()
    today, d_start = date.today(), date.today() - timedelta(days=30)

    if choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        dr = st.date_input("Период", value=(d_start, today))
        st_d, en_d = (dr[0], dr[1]) if len(dr) == 2 else (d_start, today)
        data = get_leads(None, st_d, en_d, mode="active") + get_leads(None, st_d, en_d, mode="archive")
        if data:
            df = pd.DataFrame(data)
            m = st.columns(6)
            m[0].metric("Всего", len(df)); m[1].metric("🔵 Работа", len(df[df['status_color']=='blue'])); m[2].metric("🟡 Ждут", len(df[df['status_color']=='yellow']))
            m[3].metric("🔴 Отказ", len(df[df['status_color']=='red'])); m[4].metric("🟢 Возврат", len(df[df['status_color']=='green'])); m[5].metric("🟣 Офис", len(df[df['status_color']=='purple']))
            st.divider(); cl, cr = st.columns(2)
            st_c = df['status_color'].value_counts().reset_index()
            cl.plotly_chart(px.bar(st_c, x='count', y='status_color', orientation='h', title="Статусы", color='status_color', color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','white':'#E0E0E0','green':'#C8E6C9','purple':'#E1BEE7'}, template="plotly_white"), use_container_width=True)
            df['day'] = pd.to_datetime(df['created_at']).dt.date
            cr.plotly_chart(px.area(df.groupby('day').size().reset_index(name='leads'), x='day', y='leads', title="Динамика", template="plotly_white"), use_container_width=True)

    elif choice == "👥 Список лидов":
        st.header("👥 Лиды")
        f1, f2, f3 = st.columns([2, 1.5, 1.2])
        search, dr, color_f = f1.text_input("🔍 Поиск"), f2.date_input("📅 Дата", value=(d_start, today)), f3.selectbox("🎨 Статус", FILTER_COLOR_MAP)
        st_d, en_d = (dr[0], dr[1]) if len(dr) == 2 else (None, None)
        t1, t2 = st.tabs(["🔥 Активные", "📦 Архив"])
        with t1: render_leads_list(get_leads(search, st_d, en_d, mode="active", status_filter=color_f))
        with t2:
            arch = get_leads(search, st_d, en_d, mode="archive", status_filter=color_f)
            if arch:
                pg = st.number_input("Страница", 1, max(1, len(arch)//50 + 1))
                render_leads_list(arch[(pg-1)*50 : pg*50])

    elif choice == "➕ Новый лид":
        st.header("➕ Добавить лид")
        with st.form("add_f", clear_on_submit=True):
            c1, c2 = st.columns(2); n, p = c1.text_input("ФИО"), c2.text_input("Телефон")
            c3, c4 = st.columns(2); e, t = c3.text_input("Email"), c4.text_input("Время созвона")
            c5, c6 = st.columns(2); cur, src = c5.selectbox("Курс", COURSE_OPTIONS), c6.selectbox("Источник", SOURCE_OPTIONS)
            s, comm = st.selectbox("Статус", COLOR_KEYS), st.text_area("Комментарий")
            if st.form_submit_button("Создать"):
                if n and p: add_lead(n, p, e, cur, t, src, comm, s); st.success("Готово!"); st.rerun()
                else: st.error("Имя и Телефон!")

    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("📥 Экспорт")
            all_l = get_leads(mode="active") + get_leads(mode="archive")
            if all_l:
                df = pd.DataFrame(all_l)
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
                st.download_button("📥 Скачать Excel", data=buf.getvalue(), file_name=f"leads_{date.today()}.xlsx")
        with c2:
            st.subheader("📦 Архивация")
            if st.session_state.get("role") == "superadmin":
                if st.button("📦 ПЕРЕМЕСТИТЬ ВСЁ В АРХИВ"): set_archive_threshold(); st.rerun()
        with c3:
            st.subheader("🔥 Очистка")
            if st.session_state.get("role") == "superadmin":
                if st.button("🔥 УДАЛИТЬ ВСЁ"): clear_all_leads(); st.rerun()
        st.divider(); st.subheader("🚀 Импорт")
        up = st.file_uploader("XLSX", type=["xlsx"])
        if up and st.button("Загрузить"):
            df_up = pd.read_excel(up, header=None)
            for _, r in df_up.iterrows():
                v = list(r.values)
                if len(v) >= 3: add_lead(str(v[1]), str(v[2]), str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', str(v[5]) if len(v)>5 else '', str(v[6]) if len(v)>6 else '', "Excel")
            st.success("Импортировано!"); st.rerun()

    elif choice == "🔑 Администрирование" and st.session_state.get("role") == "superadmin":
        st.header("🔑 Доступы"); new_m = st.text_input("Email:")
        if st.button("Добавить"): add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1]); c1.write(f"• {e}")
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__": main()