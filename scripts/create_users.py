import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Insert default admin (only once)
cursor.execute("""
INSERT OR IGNORE INTO users (username, password, role)
VALUES ('admin', 'admin123', 'admin')
""")

conn.commit()
conn.close()

print("Users table created and admin added")
