import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import datetime
from typing import List, Dict, Optional
from bot_config import DATABASE_URL

logger = logging.getLogger(__name__)

def _get_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def initialize_database():
    """Sets up the PostgreSQL tables for events and configuration."""
    conn = _get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    
    # Create events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            deadline TIMESTAMPTZ NOT NULL,
            type TEXT,
            notified_3d BOOLEAN DEFAULT FALSE,
            notified_24h BOOLEAN DEFAULT FALSE,
            notified_8h BOOLEAN DEFAULT FALSE,
            notified_1h BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Create system_settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Migration: Ensure notified_3d exists (for existing databases)
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='events' AND column_name='notified_3d'
    """)
    if not cursor.fetchone():
        cursor.execute('ALTER TABLE events ADD COLUMN notified_3d BOOLEAN DEFAULT FALSE')
        logger.info("Added notified_3d column to events table.")
    
    # Migration: Ensure deadline is TIMESTAMPTZ
    cursor.execute("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name='events' AND column_name='deadline'
    """)
    if cursor.fetchone()['data_type'] == 'timestamp without time zone':
        cursor.execute("ALTER TABLE events ALTER COLUMN deadline TYPE TIMESTAMPTZ")
        logger.info("Changed deadline column to TIMESTAMPTZ.")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def get_setting(key: str, default: str = None) -> Optional[str]:
    """Retrieves a value from the system_settings table."""
    conn = _get_connection()
    if not conn:
        return default
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_settings WHERE key = %s', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key: str, value: str):
    """Sets or updates a value in the system_settings table."""
    conn = _get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO system_settings (key, value)
        VALUES (%s, %s)
        ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value
    ''', (key, value))
    conn.commit()
    conn.close()

def insert_event(event_id: str, title: str, deadline, event_type: str):
    """Inserts or updates an assignment/quiz event."""
    conn = _get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    
    # Standardize deadline: Postgres driver handles aware datetime objects natively
    
    cursor.execute('''
        INSERT INTO events (id, title, deadline, type)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            title=EXCLUDED.title,
            deadline=EXCLUDED.deadline,
            type=EXCLUDED.type
    ''', (event_id, title, deadline, event_type))
    conn.commit()
    conn.close()

def get_pending_events() -> List[Dict]:
    """Retrieves all events that haven't passed and still need notifications."""
    conn = _get_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    # In Postgres, we use NOW() for current timestamp comparison
    cursor.execute("SELECT * FROM events WHERE deadline > NOW() ORDER BY deadline ASC")
    events = cursor.fetchall()
    conn.close()
    # RealDictCursor return objects that behave like dicts, but we'll cast to list[dict] for safety
    return [dict(e) for e in events]

def get_next_deadline() -> Optional[Dict]:
    """Returns the single closest upcoming event."""
    conn = _get_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE deadline > NOW() ORDER BY deadline ASC LIMIT 1")
    event = cursor.fetchone()
    conn.close()
    return dict(event) if event else None

def mark_notification_sent(event_id: str, column: str):
    """Flags a specific notification window as completed for an event."""
    valid_cols = ['notified_3d', 'notified_24h', 'notified_8h', 'notified_1h']
    if column not in valid_cols:
        return

    conn = _get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    # Standard SQL update with column name formatted in (safe due to whitelist)
    query = f"UPDATE events SET {column} = TRUE WHERE id = %s"
    cursor.execute(query, (event_id,))
    conn.commit()
    conn.close()
