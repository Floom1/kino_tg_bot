import sqlite3
import os
import datetime
from bot.config import settings
from bot.utils.time_utils import is_date_in_future

# Создаем директорию для базы данных, если ее нет
os.makedirs(os.path.dirname(settings.EVENTS_DB_PATH), exist_ok=True)

class DatabaseError(Exception):
    """Пользовательское исключение для ошибок базы данных"""
    pass

def init_db():
    """Инициализирует базу данных, создавая необходимые таблицы"""
    conn = None  # Инициализируем conn как None
    try:
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)  # Исправлено: settings.EVENTS_DB_PATH вместо EVENTS_DB_PATH
        cursor = conn.cursor()

        # Создаем таблицу событий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                event_date DATE NOT NULL,
                group_chat_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создаем таблицу настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Добавляем дефолтное значение для default_group, если его нет
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('default_group', '0')
        ''')

        conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Ошибка инициализации БД: {e}")
    finally:
        if conn:
            conn.close()

def add_event(name: str, event_date_str: str, group_chat_id: int):
    """Добавляет новое событие в базу данных с валидацией"""
    try:
        # Валидация даты с учетом часового пояса
        if not is_date_in_future(event_date_str):
            raise ValueError("Дата не может быть в прошлом или сегодняшней")

        # Подключение к БД
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (name, event_date, group_chat_id)
            VALUES (?, ?, ?)
        ''', (name, event_date_str, group_chat_id))
        conn.commit()
    except (sqlite3.Error, ValueError) as e:
        raise DatabaseError(f"Ошибка при добавлении события: {e}")
    finally:
        if conn:
            conn.close()

def get_all_events():
    """Получает все события из базы данных"""
    try:
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, event_date, group_chat_id FROM events')
        events = cursor.fetchall()
        return events
    except sqlite3.Error as e:
        raise DatabaseError(f"Ошибка при получении событий: {e}")
    finally:
        if conn:
            conn.close()

def delete_event(event_id: int):
    """Удаляет событие по ID"""
    try:
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Ошибка при удалении события: {e}")
    finally:
        if conn:
            conn.close()

def set_default_group(chat_id: int):
    """Устанавливает группу по умолчанию"""
    try:
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES ('default_group', ?)
        ''', (str(chat_id),))
        conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Ошибка при установке группы: {e}")
    finally:
        if conn:
            conn.close()

def get_default_group():
    """Получает ID группы по умолчанию"""
    try:
        conn = sqlite3.connect(settings.EVENTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = "default_group"')
        result = cursor.fetchone()
        return int(result[0]) if result else 0
    except sqlite3.Error as e:
        raise DatabaseError(f"Ошибка при получении группы: {e}")
    finally:
        if conn:
            conn.close()

init_db()