import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import logging
from typing import List, Dict, Optional
from bot_config import DATABASE_URL

logger = logging.getLogger(__name__)
_pool: Optional[SimpleConnectionPool] = None


def _get_pool() -> Optional[SimpleConnectionPool]:
    global _pool
    if _pool is not None:
        return _pool

    if not DATABASE_URL:
        logger.error("DATABASE_URL is not configured.")
        return None

    try:
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=8,
            dsn=DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=10,
        )
        return _pool
    except Exception as e:
        logger.error(f"Database pool initialization failed: {e}")
        return None

def _get_connection():
    """Establishes a connection to the PostgreSQL database."""
    pool = _get_pool()
    if not pool:
        return None

    try:
        return pool.getconn()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def _put_connection(conn):
    pool = _get_pool()
    if not pool or not conn:
        return
    try:
        pool.putconn(conn)
    except Exception as e:
        logger.error(f"Failed to return connection to pool: {e}")

def initialize_database():
    """Sets up the PostgreSQL tables for events and configuration."""
    conn = _get_connection()
    if not conn:
        return
    cursor = None
    try:
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
        row = cursor.fetchone()
        if row and row['data_type'] == 'timestamp without time zone':
            cursor.execute("ALTER TABLE events ALTER COLUMN deadline TYPE TIMESTAMPTZ")
            logger.info("Changed deadline column to TIMESTAMPTZ.")

        conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def get_setting(key: str, default: str = None) -> Optional[str]:
    """Retrieves a value from the system_settings table."""
    conn = _get_connection()
    if not conn:
        return default
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM system_settings WHERE key = %s', (key,))
        row = cursor.fetchone()
        return row['value'] if row else default
    except Exception as e:
        logger.error(f"Failed to get setting {key}: {e}")
        return default
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def set_setting(key: str, value: str):
    """Sets or updates a value in the system_settings table."""
    conn = _get_connection()
    if not conn:
        return
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value
        ''', (key, value))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to set setting {key}: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def insert_event(event_id: str, title: str, deadline, event_type: str):
    """Inserts or updates an assignment/quiz event."""
    conn = _get_connection()
    if not conn:
        return
    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO events (id, title, deadline, type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                title=EXCLUDED.title,
                deadline=EXCLUDED.deadline,
                type=EXCLUDED.type,
                notified_3d=CASE WHEN events.deadline IS DISTINCT FROM EXCLUDED.deadline THEN FALSE ELSE events.notified_3d END,
                notified_24h=CASE WHEN events.deadline IS DISTINCT FROM EXCLUDED.deadline THEN FALSE ELSE events.notified_24h END,
                notified_8h=CASE WHEN events.deadline IS DISTINCT FROM EXCLUDED.deadline THEN FALSE ELSE events.notified_8h END,
                notified_1h=CASE WHEN events.deadline IS DISTINCT FROM EXCLUDED.deadline THEN FALSE ELSE events.notified_1h END
        ''', (event_id, title, deadline, event_type))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to insert/update event {event_id}: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def get_pending_events() -> List[Dict]:
    """Retrieves all events that haven't passed and still need notifications."""
    conn = _get_connection()
    if not conn:
        return []
    cursor = None
    try:
        cursor = conn.cursor()
        # In Postgres, we use NOW() for current timestamp comparison
        cursor.execute("SELECT * FROM events WHERE deadline > NOW() ORDER BY deadline ASC")
        events = cursor.fetchall()
        # RealDictCursor return objects that behave like dicts, but we'll cast to list[dict] for safety
        return [dict(e) for e in events]
    except Exception as e:
        logger.error(f"Failed to fetch pending events: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def get_next_deadline() -> Optional[Dict]:
    """Returns the single closest upcoming event."""
    conn = _get_connection()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE deadline > NOW() ORDER BY deadline ASC LIMIT 1")
        event = cursor.fetchone()
        return dict(event) if event else None
    except Exception as e:
        logger.error(f"Failed to fetch next deadline: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)

def mark_notification_sent(event_id: str, column: str):
    """Flags a specific notification window as completed for an event."""
    valid_cols = ['notified_3d', 'notified_24h', 'notified_8h', 'notified_1h']
    if column not in valid_cols:
        return

    conn = _get_connection()
    if not conn:
        return
    cursor = None
    try:
        cursor = conn.cursor()
        # Standard SQL update with column name formatted in (safe due to whitelist)
        query = f"UPDATE events SET {column} = TRUE WHERE id = %s"
        cursor.execute(query, (event_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to mark notification sent for {event_id}: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        _put_connection(conn)
