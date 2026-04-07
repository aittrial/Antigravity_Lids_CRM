import os
import psycopg2
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def get_connection():
    """
    Устанавливает прямое соединение с базой данных PostgreSQL.
    Использует SSL для безопасности Railway.
    """
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
        st.error(f"❌ Критическая ошибка подключения к базе данных: {e}")
        return None

def init_db():
    """
    Инициализация всех таблиц системы. 
    Проверяет наличие каждой колонки по отдельности для стабильности.
    """
    conn = get_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # 1. Создание таблицы разрешенных Email
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowed_emails (
                email VARCHAR(255) PRIMARY KEY, 
                role TEXT DEFAULT 'admin'
            );
        """)
        
        # 2. Создание таблицы системных настроек
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, 
                value TEXT
            );
        """)
        
        # 3. Создание основной таблицы лидов (развернутая структура)
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
        
        # Явное добавление колонок, если они отсутствуют (для старых баз)
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NULL;")
        
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS preferred_time TEXT;")
        
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS source TEXT;")
        
        cur.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS whatsapp TEXT;")
        
        cur.execute("ALTER TABLE allowed_emails ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'admin';")
        
        # Создание индексов для высокой скорости поиска и фильтрации
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_archived_status ON leads (archived_at);")
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_creation_date ON leads (created_at);")
        
        # Проверка и исправление пустых ролей
        cur.execute("UPDATE allowed_emails SET role = 'admin' WHERE role IS NULL;")
        
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"❌ Ошибка инициализации базы: {e}")
    finally:
        conn.close()

def get_leads(search_query=None, start_date=None, end_date=None, mode="active", status_filter=None, source_filter=None, limit=50, offset=0):
    """
    Загрузка лидов из базы. 
    Реализована постраничная навигация через LIMIT и OFFSET.
    """
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        # Начало формирования SQL запроса
        sql_query = "SELECT * FROM leads WHERE 1=1"
        query_params = []

        # Фильтр по режиму (Активные или Архив)
        if mode == "active":
            sql_query += " AND archived_at IS NULL"
        elif mode == "archive":
            sql_query += " AND archived_at IS NOT NULL"

        # Фильтр по цвету статуса
        if status_filter and status_filter != "Все":
            status_mapping = {
                "Белый": "white", 
                "Синий": "blue", 
                "Желтый": "yellow", 
                "Красный": "red", 
                "Зеленый": "green", 
                "Фиолетовый": "purple", 
                "Розовый": "pink"
            }
            color_val = status_mapping.get(status_filter, "white")
            sql_query += " AND status_color = %s"
            query_params.append(color_val)

        # Фильтр по источнику лида
        if source_filter and source_filter != "Все":
            sql_query += " AND source = %s"
            query_params.append(source_filter)

        # Поиск по ФИО или Телефону (Регистронезависимый)
        if search_query:
            sql_query += " AND (full_name ILIKE %s OR phone ILIKE %s)"
            search_val = f"%{search_query}%"
            query_params.append(search_val)
            query_params.append(search_val)
        
        # Фильтр по дате начала
        if start_date:
            sql_query += " AND created_at >= %s"
            query_params.append(start_date)
            
        # Фильтр по дате конца
        if end_date:
            sql_query += " AND created_at <= %s"
            full_end_date = datetime.combine(end_date, datetime.max.time())
            query_params.append(full_end_date)

        # Сортировка: новые сверху
        sql_query += " ORDER BY id DESC"
        
        # Применение пагинации
        sql_query += " LIMIT %s OFFSET %s"
        query_params.append(limit)
        query_params.append(offset)

        cur.execute(sql_query, query_params)
        
        # Получаем названия колонок для упаковки в словарь
        columns = [desc[0] for desc in cur.description]
        db_rows = cur.fetchall()
        
        final_leads_list = []
        for row in db_rows:
            lead_dict = dict(zip(columns, row))
            final_leads_list.append(lead_dict)
            
        cur.close()
        return final_leads_list
    except Exception as e:
        st.error(f"❌ Ошибка при получении лидов: {e}")
        return []
    finally:
        conn.close()

def add_lead(full_name, phone, email='', course_name='', preferred_time='', source='', comment='', status_color='white', whatsapp=''):
    """Добавление нового лида в базу данных."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        insert_sql = """
            INSERT INTO leads (
                full_name, phone, whatsapp, email, course_name, 
                preferred_time, source, comment, status_color
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_sql, (
            full_name, phone, whatsapp, email, course_name, 
            preferred_time, source, comment, status_color
        ))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def update_lead(lead_id, **kwargs):
    """Обновление полей лида по его ID."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        for column_name, new_value in kwargs.items():
            update_sql = f"UPDATE leads SET {column_name} = %s WHERE id = %s"
            cur.execute(update_sql, (new_value, lead_id))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def archive_single_lead(lead_id):
    """Перенос одного конкретного лида в архив."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        now_time = datetime.now()
        cur.execute("UPDATE leads SET archived_at = %s WHERE id = %s", (now_time, lead_id))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def get_allowed_emails():
    """Получение списка всех сотрудников с доступом."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, role FROM allowed_emails")
        email_rows = cur.fetchall()
        
        allowed_list = []
        for r in email_rows:
            allowed_list.append({'email': r[0], 'role': r[1]})
        
        cur.close()
        return allowed_list
    finally:
        conn.close()

def add_allowed_email(email, role='admin'):
    """Добавление нового Email в список разрешенных."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO allowed_emails (email, role) 
            VALUES (%s, %s) 
            ON CONFLICT (email) DO UPDATE SET role = %s
        """, (email, role, role))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def delete_allowed_email(email):
    """Удаление Email из списка доступа."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM allowed_emails WHERE email = %s", (email,))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def clear_all_leads():
    """Полная и безвозвратная очистка таблицы лидов."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE leads RESTART IDENTITY CASCADE;")
        cur.execute("DELETE FROM settings WHERE key = 'archive_date';")
        conn.commit()
        cur.close()
    finally:
        conn.close()

def set_archive_threshold():
    """Архивация всех текущих активных лидов."""
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        current_now = datetime.now()
        # Сохраняем дату архивации в настройки
        cur.execute("""
            INSERT INTO settings (key, value) 
            VALUES ('archive_date', %s) 
            ON CONFLICT (key) DO UPDATE SET value = %s
        """, (current_now.isoformat(), current_now.isoformat()))
        # Массово обновляем статус всех активных лидов
        cur.execute("UPDATE leads SET archived_at = %s WHERE archived_at IS NULL", (current_now,))
        conn.commit()
        cur.close()
    finally:
        conn.close()