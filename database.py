import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def get_db_path():
    configured_path = os.getenv("DATABASE_PATH")
    if configured_path:
        if os.path.isabs(configured_path):
            return configured_path
        return str(BASE_DIR / configured_path)
    return str(BASE_DIR / "database.db")


def get_db_connection():
    db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table_name, column_name, column_definition):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            email TEXT,
            is_verified INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            year TEXT,
            semester TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timetable_id INTEGER,
            day TEXT,
            period INTEGER,
            subject TEXT,
            FOREIGN KEY(timetable_id) REFERENCES timetable_meta(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            filename TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            subject TEXT NOT NULL,
            upload_date TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)

    ensure_column(conn, "users", "role", "role TEXT DEFAULT 'student'")
    ensure_column(conn, "users", "email", "email TEXT")
    ensure_column(conn, "users", "is_verified", "is_verified INTEGER DEFAULT 0")
    ensure_column(conn, "assignments", "filename", "filename TEXT DEFAULT ''")
    ensure_column(conn, "help_requests", "status", "status TEXT DEFAULT 'pending'")

    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {get_db_path()}.")


if __name__ == "__main__":
    init_db()