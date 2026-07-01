import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 1. Users Table (with Role)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            email TEXT
        )
    """)

    # 2. Notices Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # 3. Timetable Meta (Branch/Year/Sem)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            year TEXT,
            semester TEXT
        )
    """)

    # 4. Timetable Slots
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

    # 5. Assignments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully with Role support.")

if __name__ == "__main__":
    init_db()