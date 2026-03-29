import os
import psycopg2
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_connection():
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
        st.error(f"❌ Ошибка базы: {e}")
        return None

def init_db():
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS allowed_emails (email VARCHAR(255) PRIMARY KEY);")
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            course_name TEXT,
            preferred_time TEXT,
            source TEXT,
            comment TEXT,
            status_color VARCHAR(50) DEFAULT 'white',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS preferred_time TEXT;")
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS source TEXT;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_id_desc ON leads (id DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at);")
        conn.commit()
    finally:
        conn.close()

def set_archive_threshold():
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        now = datetime.now().isoformat()
        cur.execute("INSERT INTO settings (key, value) VALUES ('archive_date', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (now, now))
        conn.commit()
    finally:
        conn.close()

def get_archive_threshold():
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'archive_date'")
        res = cur.fetchone()
        return res[0] if res else None
    finally:
        conn.close()

def add_lead(full_name, phone, email='', course_name='', preferred_time='', source='', comment='', status_color='white'):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (full_name, phone, email, course_name, preferred_time, source, comment, status_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (str(full_name or ""), str(phone or ""), str(email or ""), 
              str(course_name or ""), str(preferred_time or ""), str(source or ""), str(comment or ""), str(status_color or "white")))
        conn.commit()
    finally:
        conn.close()

def get_leads(search_query=None, start_date=None, end_date=None, mode="active", status_filter=None):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        threshold = get_archive_threshold()
        query = "SELECT * FROM leads WHERE 1=1"
        params = []
        
        if mode == "active":
            if threshold:
                query += " AND created_at > %s"
                params.append(threshold)
            limit_sql = " LIMIT 50"
        else:
            if threshold:
                query += " AND (created_at <= %s OR id NOT IN (SELECT id FROM leads WHERE created_at > %s ORDER BY id DESC LIMIT 50))"
                params.extend([threshold, threshold])
            else:
                query += " AND id NOT IN (SELECT id FROM leads ORDER BY id DESC LIMIT 50)"
            limit_sql = ""

        if status_filter and status_filter != "Все":
            status_map = {
                "Белый": "white", "Синий": "blue", "Желтый": "yellow", 
                "Красный": "red", "Зеленый": "green", "Фиолетовый": "purple"
            }
            query += " AND status_color = %s"
            params.append(status_map.get(status_filter, "white"))

        if search_query:
            query += " AND (full_name ILIKE %s OR phone ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= %s"
            params.append(datetime.combine(end_date, datetime.max.time()))

        query += " ORDER BY id DESC" + limit_sql
        
        cur.execute(query, params)
        colnames = [desc[0] for desc in cur.description]
        return [dict(zip(colnames, row)) for row in cur.fetchall()]
    finally:
        conn.close()

def update_lead(lead_id, **kwargs):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        params = list(kwargs.values()) + [lead_id]
        cur.execute(f"UPDATE leads SET {set_clause} WHERE id = %s", params)
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

def get_allowed_emails():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM allowed_emails")
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def add_allowed_email(email):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO allowed_emails (email) VALUES (%s) ON CONFLICT DO NOTHING", (email,))
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