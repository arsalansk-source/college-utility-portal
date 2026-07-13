import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load .env without overwriting existing system environment variables
load_dotenv(override=False)


def get_db_path():
    configured_path = os.getenv("DATABASE_PATH")
    if configured_path:
        if os.path.isabs(configured_path):
            return configured_path
        return str(BASE_DIR / configured_path)
    return None


def get_db_connection():
    # Production connection using your exact, explicit Supabase hardware targets
    return psycopg2.connect(
        host="aws-0-ap-northeast-1.pooler.supabase.com",
        port=6543,
        database="postgres",
        user="postgres.hefdjjpgijuanqkdspor",
        password="Arsalan_9848__",
        sslmode="require"
    )


def ensure_column(conn, table_name, column_name, column_definition):
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_definition}")
    cursor.close()


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            email TEXT,
            is_verified INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_meta (
            id SERIAL PRIMARY KEY,
            branch TEXT,
            year TEXT,
            semester TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_slots (
            id SERIAL PRIMARY KEY,
            timetable_id INTEGER REFERENCES timetable_meta(id),
            day TEXT,
            period INTEGER,
            subject TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            filename TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            subject TEXT NOT NULL,
            upload_date TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS help_requests (
            id SERIAL PRIMARY KEY,
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

    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if admin_user and admin_pass:
        cursor.execute("SELECT id FROM users WHERE username=%s", (admin_user,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, role, email, is_verified) VALUES (%s, %s, 'admin', %s, 1)",
                (admin_user, admin_pass, f"{admin_user}@example.local")
            )
            conn.commit()

    cursor.close()
    conn.close()
    print("Database initialized successfully (PostgreSQL).")


if __name__ == "__main__":
    init_db()
