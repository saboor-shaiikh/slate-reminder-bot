import sqlite3
import datetime
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_NAME = "slate_bot.db"

def _get_connection():
    return sqlite3.connect(DB_NAME)

def initialize_database():
    """Initializes the events table and system_settings table."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            type TEXT,
            notified_24h BOOLEAN DEFAULT 0,
            notified_8h BOOLEAN DEFAULT 0,
            notified_1h BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized with events and system_settings tables.")

def get_setting(key: str, default: str = None) -> Optional[str]:
    """Retrieves a value from the system_settings table."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key: str, value: str):
    """Sets or updates a value in the system_settings table."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO system_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()


def insert_event(event_id: str, title: str, deadline, event_type: str):
    """Inserts a new event into the database safely."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Safely extract timezone-naive datetime string
    if hasattr(deadline, 'tzinfo') and deadline.tzinfo is not None:
        deadline = deadline.replace(tzinfo=None)
        
    if hasattr(deadline, 'isoformat'):
        deadline_str = deadline.isoformat()
    else:
        deadline_str = str(deadline)
    
    cursor.execute('''
        INSERT OR IGNORE INTO events (id, title, deadline, type)
        VALUES (?, ?, ?, ?)
    ''', (event_id, title, deadline_str, event_type))
    conn.commit()
    conn.close()

def get_pending_events() -> List[Dict]:
    """Returns all pending events that haven't passed yet."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now_str = datetime.datetime.now().isoformat()
    cursor.execute('''
        SELECT * FROM events 
        WHERE deadline > ? 
        ORDER BY deadline ASC
    ''', (now_str,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_next_deadline() -> Optional[Dict]:
    """Returns the single next pending deadline."""
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now_str = datetime.datetime.now().isoformat()
    cursor.execute('''
        SELECT * FROM events 
        WHERE deadline > ? 
        ORDER BY deadline ASC 
        LIMIT 1
    ''', (now_str,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def mark_notification_sent(event_id: str, notification_type: str):
    """Marks that a specific reminder interval has been sent for an event."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Prevent SQL injection by ensuring only legitimate columns are used
    if notification_type in ('notified_24h', 'notified_8h', 'notified_1h'):
        query = f"UPDATE events SET {notification_type} = 1 WHERE id = ?"
        cursor.execute(query, (event_id,))
        conn.commit()
    
    conn.close()
