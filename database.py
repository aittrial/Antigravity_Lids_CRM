import os
import psycopg2
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Прямое подключение к базе данных."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"❌ Ошибка подключения: {e}")
        return None

def init_db():
    """Инициализация таблиц с явной проверкой каждой колонки."""
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        
        # Создаем таблицы
        cur.execute("CREATE TABLE IF NOT EXISTS allowed_emails (email VARCHAR(255) PRIMARY KEY, role TEXT DEFAULT 'admin');")
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                full_name TEXT,
                phone TEXT,
                whatsapp TEXT,
                email TEXT,
                course_name TEXT,
                preferred_time TEXT,
                source TEXT,
                comment TEXT,
                status_color VARCHAR(50) DEFAULT 'white',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived_at TIMESTAMP DEFAULT NULL
            );
        """)
        
        # Добавляем колонки по одной (развернуто)
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NULL;")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS preferred_time TEXT;")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS source TEXT;")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS whatsapp TEXT;")
        cur.execute("ALTER TABLE allowed_emails ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'admin';")
        
        # Создаем индексы для ускорения работы
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_archived ON leads (archived_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_created ON leads (created_at);")
        
        # Защита от пустых ролей
        cur.execute("UPDATE allowed_emails SET role = 'admin' WHERE role IS NULL;")
        
        conn.commit()
    finally:
        conn.close()

def get_leads(search_query=None, start_date=None, end_date=None, mode="active", status_filter=None, source_filter=None):
    """Поиск лидов. Развернутая логика без жестких лимитов для архива."""
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if mode == "active":
            query += " AND archived_at IS NULL"
        elif mode == "archive":
            query += " AND archived_at IS NOT NULL"

        if status_filter and status_filter != "Все":
            status_map = {
                "Белый": "white", "Синий": "blue", "Желтый": "yellow", 
                "Красный": "red", "Зеленый": "green", "Фиолетовый": "purple", "Розовый": "pink"
            }
            query += " AND status_color = %s"
            params.append(status_map.get(status_filter, "white"))

        if source_filter and source_filter != "Все":
            query += " AND source = %s"
            params.append(source_filter)

        if search_query:
            query += " AND (full_name ILIKE %s OR phone ILIKE %s)"
            params.append(f"%{search_query}%")
            params.append(f"%{search_query}%")
        
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
            
        if end_date:
            query += " AND created_at <= %s"
            params.append(datetime.combine(end_date, datetime.max.time()))

        query += " ORDER BY id DESC"
        
        # Лимит только для активных, чтобы страница не висла при первом входе
        if mode == "active" and not search_query:
            query += " LIMIT 100"

        cur.execute(query, params)
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        leads = []
        for row in rows:
            leads.append(dict(zip(colnames, row)))
        return leads
    finally:
        conn.close()

def add_lead(full_name, phone, email='', course_name='', preferred_time='', source='', comment='', status_color='white', whatsapp=''):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (full_name, phone, whatsapp, email, course_name, preferred_time, source, comment, status_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (full_name, phone, whatsapp, email, course_name, preferred_time, source, comment, status_color))
        conn.commit()
    finally:
        conn.close()

def update_lead(lead_id, **kwargs):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        if not kwargs: return
        for key, value in kwargs.items():
            cur.execute(f"UPDATE leads SET {key} = %s WHERE id = %s", (value, lead_id))
        conn.commit()
    finally:
        conn.close()

def delete_lead(lead_id):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
        conn.commit()
    finally:
        conn.close()

def get_allowed_emails():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, role FROM allowed_emails")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({'email': row[0], 'role': row[1]})
        return result
    finally:
        conn.close()

def add_allowed_email(email, role='admin'):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO allowed_emails (email, role) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET role = %s", (email, role, role))
        conn.commit()
    finally:
        conn.close()

def delete_allowed_email(email):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM allowed_emails WHERE email = %s", (email,))
        conn.commit()
    finally:
        conn.close()

def set_archive_threshold():
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        now = datetime.now()
        cur.execute("INSERT INTO settings (key, value) VALUES ('archive_date', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (now.isoformat(), now.isoformat()))
        cur.execute("UPDATE leads SET archived_at = %s WHERE archived_at IS NULL", (now,))
        conn.commit()
    finally:
        conn.close()

def archive_single_lead(lead_id):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE leads SET archived_at = %s WHERE id = %s", (datetime.now(), lead_id))
        conn.commit()
    finally:
        conn.close()

def clear_all_leads():
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE leads RESTART IDENTITY")
        cur.execute("DELETE FROM settings WHERE key = 'archive_date'")
        conn.commit()
    finally:
        conn.close()