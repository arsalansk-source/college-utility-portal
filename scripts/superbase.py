import os
import sqlite3
from pathlib import Path
import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent

def load_env_file(env_path: Path):
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    load_env_file(BASE_DIR / ".env")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set in .env")

    sqlite_path = BASE_DIR / "database.db"
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Local SQLite database not found at: {sqlite_path}")

    with sqlite3.connect(sqlite_path) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        src_cursor = sqlite_conn.cursor()
        src_cursor.execute("SELECT username, password, role, email, is_verified FROM users")
        users = src_cursor.fetchall()

    dest_conn = psycopg2.connect(db_url)
    dest_cursor = dest_conn.cursor()

    inserted = 0
    skipped = 0
    for row in users:
        username = row["username"]
        password = row["password"]
        role = row["role"] or "student"
        email = row["email"]
        is_verified = row["is_verified"] or 0

        try:
            dest_cursor.execute(
                """
                INSERT INTO users (username, password, role, email, is_verified)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                (username, password, role, email, is_verified),
            )
            if dest_cursor.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        except Exception as exc:
            print(f"Failed to insert {username}: {exc}")

    dest_conn.commit()
    dest_cursor.close()
    dest_conn.close()

    print(f"Migration complete. Inserted: {inserted}, skipped: {skipped}.")
    print("If you need to preserve old IDs, improve the script to insert id values explicitly.")


if __name__ == "__main__":
    main()
