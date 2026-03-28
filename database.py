import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "lids_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "yourpassword")

try:
    connection_pool = pool.SimpleConnectionPool(
        1, 20,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print("Database connection pool established.")
except Exception as e:
    print(f"Error connecting to database: {e}")
    connection_pool = None

def get_connection():
    if connection_pool:
        return connection_pool.getconn()
    return None

def release_connection(conn):
    if connection_pool and conn:
        connection_pool.putconn(conn)

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
        release_connection(conn)

def add_lead(full_name, phone, email='', course_name='', source='', callback_time='', comment='', status_color='white'):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (full_name, phone, email, course_name, source, callback_time, comment, status_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (str(full_name), str(phone), str(email), str(course_name), str(source), str(callback_time), str(comment), str(status_color)))
        lead_id = cur.fetchone()[0]
        conn.commit()
        return lead_id
    finally:
        release_connection(conn)

def get_leads():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads ORDER BY id DESC")
        colnames = [desc[0] for desc in cur.description]
        return [dict(zip(colnames, row)) for row in cur.fetchall()]
    finally:
        release_connection(conn)

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
        release_connection(conn)

def delete_lead(lead_id):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
        conn.commit()
    finally:
        release_connection(conn)

def get_allowed_emails():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM allowed_emails")
        return [row[0] for row in cur.fetchall()]
    finally:
        release_connection(conn)

def add_allowed_email(email):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO allowed_emails (email) VALUES (%s) ON CONFLICT DO NOTHING", (email,))
        conn.commit()
    finally:
        release_connection(conn)

def delete_allowed_email(email):
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM allowed_emails WHERE email = %s", (email,))
        conn.commit()
    finally:
        release_connection(conn)