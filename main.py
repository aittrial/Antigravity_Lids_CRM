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

def get_status_color(status):
    colors = {"blue": "#B3D7FF", "yellow": "#FFF59D", "red": "#FFAB91", "white": "#F0F2F6"}
    return colors.get(status, "#F0F2F6")

def render_leads_list(leads_data, start_order=1):
    if not leads_data:
        st.info("В этом разделе пока пусто.")
        return
    for i, row in enumerate(leads_data):
        color = get_status_color(row['status_color'])
        date_s = row['created_at'].strftime("%d.%m.%Y %H:%M")
        st.markdown(f"""
            <div style="background-color:{color}; border-radius:10px; padding:12px; margin-bottom:10px; border:2px solid #444; color: #000000 !important;">
                <b style="color: #000000 !important; font-size: 14px;">
                    #{start_order+i} | 📅 {date_s} | {row['full_name']} | {row['phone']}
                </b>
            </div>
        """, unsafe_allow_html=True)
        with st.expander("Управление лидом"):
            phone_num = ''.join(filter(str.isdigit, str(row['phone'])))
            st.markdown(f'''<a href="https://wa.me/{phone_num}" target="_blank">
                <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">
                💬 WhatsApp</button></a>''', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("ФИО", row['full_name'], key=f"n_{row['id']}")
            p = c2.text_input("Телефон", row['phone'], key=f"p_{row['id']}")
            e = c3.text_input("Email", row['email'], key=f"e_{row['id']}")
            c4, c5, c6 = st.columns(3)
            curr_c = c4.text_input("Курс", row['course_name'], key=f"c_{row['id']}")
            curr_s = c5.selectbox("Статус", ["white", "blue", "yellow", "red"], index=["white", "blue", "yellow", "red"].index(row['status_color']), key=f"s_{row['id']}")
            curr_src = c6.text_input("Источник", row['source'], key=f"src_{row['id']}")
            curr_comm = st.text_area("Комментарии", row['comment'] if row['comment'] else "", key=f"cm_{row['id']}")
            bs, bd = st.columns([1, 5])
            if bs.button("💾 Сохранить", key=f"sv_{row['id']}"):
                update_lead(row['id'], full_name=n, phone=p, email=e, course_name=curr_c, status_color=curr_s, comment=curr_comm, source=curr_src)
                st.rerun()
            if st.session_state.get("role") == "superadmin" and bd.button("🗑️ Удалить", key=f"del_{row['id']}"):
                delete_lead(row['id']); st.rerun()

def main():
    if not check_password(): return

    st.sidebar.markdown(f"### {APP_TITLE}")
    menu = ["📊 Аналитика", "👥 Список лидов", "➕ Новый лид", "📂 База данных"]
    if st.session_state.get("role") == "superadmin":
        menu.append("🔑 Администрирование")
    
    choice = st.sidebar.selectbox("Навигация", menu)
    if st.sidebar.button("🚪 Выход"): logout()

    today = date.today()
    default_start = today - timedelta(days=30)

    # --- АНАЛИТИКА ---
    if choice == "📊 Аналитика":
        st.header("📊 Аналитический дашборд")
        d_range = st.date_input("Период", value=(default_start, today))
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (default_start, today)
        data = get_leads(None, st_d, en_d, mode="active") + get_leads(None, st_d, en_d, mode="archive")
        if data:
            df = pd.DataFrame(data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Всего", len(df)); m2.metric("🔵 В работе", len(df[df['status_color'] == 'blue']))
            m3.metric("🟡 Ожидание", len(df[df['status_color'] == 'yellow'])); m4.metric("🔴 Отказы", len(df[df['status_color'] == 'red']))
            st.divider()
            cl, cr = st.columns(2)
            st_counts = df['status_color'].value_counts().reset_index()
            st_counts.columns = ['Статус', 'Количество']
            fig_bar = px.bar(st_counts, x='Количество', y='Статус', orientation='h', title="Статусы", template="plotly_white", color='Статус', color_discrete_map={'blue':'#B3D7FF','yellow':'#FFF59D','red':'#FFAB91','white':'#E0E0E0'})
            cl.plotly_chart(fig_bar, use_container_width=True)
            df['Дата'] = df['created_at'].dt.date
            daily = df.groupby('Дата').size().reset_index(name='Лидов')
            fig_area = px.area(daily, x='Дата', y='Лидов', title="Динамика поступления", template="plotly_white")
            cr.plotly_chart(fig_area, use_container_width=True)

    # --- СПИСОК ЛИДОВ (ПОИСК ВВЕРХУ) ---
    elif choice == "👥 Список лидов":
        st.header("👥 Работа с лидами")
        
        # ПОИСК В САМОМ ВЕРХУ
        with st.container():
            f_col1, f_col2 = st.columns([2, 2])
            search = f_col1.text_input("🔍 Быстрый поиск (Имя или телефон)", "", key="main_search")
            d_range = f_col2.date_input("📅 Фильтр по дате", value=(default_start, today), key="main_date")
        
        st_d, en_d = (d_range[0], d_range[1]) if len(d_range) == 2 else (None, None)
        st.divider()

        tab_active, tab_archive = st.tabs(["🔥 Главная (Активные)", "📦 Весь Архив"])
        
        with tab_active:
            leads_active = get_leads(search if search else None, st_d, en_d, mode="active")
            st.info(f"Активных лидов: **{len(leads_active)}** (ТОП-50 последних)")
            render_leads_list(leads_active, start_order=1)

        with tab_archive:
            leads_archive = get_leads(search if search else None, st_d, en_d, mode="archive")
            total_arch = len(leads_archive)
            st.warning(f"Всего в архиве: **{total_arch}**")
            if total_arch > 0:
                ipp = 50
                num_p = max(1, (total_arch // ipp) + (1 if total_arch % ipp > 0 else 0))
                page = st.number_input("Страница архива", min_value=1, max_value=num_p, key="arch_page")
                render_leads_list(leads_archive[(page-1)*ipp : page*ipp], start_order=1)

    # --- НОВЫЙ ЛИД ---
    elif choice == "➕ Новый лид":
        st.header("➕ Добавление записи")
        with st.form("manual_add", clear_on_submit=True):
            f_n, f_p, f_e, f_c = st.text_input("ФИО"), st.text_input("Телефон"), st.text_input("Email"), st.text_input("Курс")
            f_cm = st.text_area("Комментарий")
            if st.form_submit_button("Создать запись"):
                if f_n and f_p:
                    add_lead(f_n, f_p, f_e, f_c, "Manual", f_cm); st.success("Лид добавлен!"); st.rerun()
                else: st.error("Имя и Телефон обязательны")

    # --- БАЗА ДАННЫХ (РУЧНАЯ АРХИВАЦИЯ) ---
    elif choice == "📂 База данных":
        st.header("📂 Управление базой")
        c_ex, c_arch, c_clr = st.columns(3)
        
        with c_ex:
            st.subheader("📥 Экспорт")
            all_l = get_leads(mode="active") + get_leads(mode="archive")
            if all_l:
                df_ex = pd.DataFrame(all_l)
                if 'id' in df_ex.columns: df_ex = df_ex.drop(columns=['id'])
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                    df_ex.to_excel(wr, index=False, sheet_name='Leads')
                st.download_button("📥 Скачать Excel", data=buf.getvalue(), file_name=f"export_{date.today()}.xlsx")
        
        with c_arch:
            st.subheader("📦 Архивация")
            if st.session_state.get("role") == "superadmin":
                st.write("Очистить Главную?")
                if 'confirm_arch' not in st.session_state: st.session_state.confirm_arch = False
                
                if not st.session_state.confirm_arch:
                    if st.button("📦 ВСЁ В АРХИВ"):
                        st.session_state.confirm_clear = False # Сброс другой кнопки
                        st.session_state.confirm_arch = True; st.rerun()
                else:
                    st.warning("Вы уверены? Главная страница станет пустой!")
                    ca_y, ca_n = st.columns(2)
                    if ca_y.button("✅ Да, архивировать"):
                        set_archive_threshold(); st.session_state.confirm_arch = False; st.success("Успех!"); st.rerun()
                    if ca_n.button("❌ Отмена"):
                        st.session_state.confirm_arch = False; st.rerun()
            else: st.error("Доступ только для суперадмина")

        with c_clr:
            st.subheader("🔥 Очистка")
            if st.session_state.get("role") == "superadmin":
                if 'confirm_clear' not in st.session_state: st.session_state.confirm_clear = False
                if not st.session_state.confirm_clear:
                    if st.button("🔥 УДАЛИТЬ ВСЁ"):
                        st.session_state.confirm_arch = False # Сброс другой кнопки
                        st.session_state.confirm_clear = True; st.rerun()
                else:
                    st.error("ВЫ УВЕРЕНЫ? Это удалит базу полностью!")
                    cc_y, cc_n = st.columns(2)
                    if cc_y.button("✅ Да, Стереть"):
                        clear_all_leads(); st.session_state.confirm_clear = False; st.rerun()
                    if cc_n.button("❌ Нет, Отмена"):
                        st.session_state.confirm_clear = False; st.rerun()

        st.divider()
        st.subheader("🚀 Импорт")
        up = st.file_uploader("Загрузить XLSX", type=["xlsx"])
        if up and st.button("Начать импорт"):
            df_up = pd.read_excel(up, header=None)
            for _, r in df_up.iterrows():
                v = list(r.values)
                if len(v) >= 3: add_lead(str(v[1]), str(v[2]), str(v[3]) if len(v)>3 else '', str(v[4]) if len(v)>4 else '', "Excel")
            st.success("Данные загружены!"); st.rerun()

    # --- АДМИНИСТРИРОВАНИЕ ---
    elif choice == "🔑 Администрирование" and st.session_state.get("role") == "superadmin":
        st.header("🔑 Управление доступом")
        new_m = st.text_input("Email:")
        if st.button("Добавить"):
            if new_m: add_allowed_email(new_m); st.rerun()
        for e in get_allowed_emails():
            c1, c2 = st.columns([4, 1]); c1.write(f"• {e}")
            if c2.button("Удалить", key=e): delete_allowed_email(e); st.rerun()

if __name__ == "__main__":
    main()