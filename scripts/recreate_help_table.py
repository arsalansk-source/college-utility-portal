import sqlite3

def recreate_table():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    print("Dropping old table...")
    cursor.execute("DROP TABLE IF EXISTS help_requests")
    
    print("Creating new table...")
    cursor.execute("""
        CREATE TABLE help_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            type TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Success: 'help_requests' table recreated.")

if __name__ == "__main__":
    recreate_table()