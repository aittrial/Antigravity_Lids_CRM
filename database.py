import os
import psycopg2
import streamlit as st
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
        st.error(f"❌ Ошибка подключения: {e}")
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
            callback_time TEXT,
            comment TEXT,
            status_color VARCHAR(50) DEFAULT 'white',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
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
        """, (str(full_name), str(phone), str(email), str(course_name), str(source), str(comment), str(status_color)))
        conn.commit()
    finally:
        conn.close()

def get_leads():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads ORDER BY id DESC")
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