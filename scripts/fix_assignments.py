import sqlite3

def create_assignments_table():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

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
    print("Success: 'assignments' table created.")

if __name__ == "__main__":
    create_assignments_table()