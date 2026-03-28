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
        cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            course_name TEXT,
            source TEXT,
            comment TEXT,
            status_color VARCHAR(50) DEFAULT 'white',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Индексы для быстрой фильтрации по датам и статусам
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status_color);")
        conn.commit()
    finally:
        conn.close()

def add_lead(full_name, phone, email='', course_name='', source='', comment='', status_color='white'):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (full_name, phone, email, course_name, source, comment, status_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (str(full_name or ""), str(phone or ""), str(email or ""), 
              str(course_name or ""), str(source or ""), str(comment or ""), str(status_color or "white")))
        conn.commit()
    except Exception as e:
        st.error(f"Ошибка при добавлении: {e}")
    finally:
        conn.close()

def get_leads(search_query=None, start_date=None, end_date=None):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        query = "SELECT * FROM leads WHERE 1=1"
        params = []
        if search_query:
            query += " AND (full_name ILIKE %s OR phone ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= %s"
            params.append(datetime.combine(end_date, datetime.max.time()))
        query += " ORDER BY id DESC"
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