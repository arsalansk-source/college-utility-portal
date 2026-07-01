import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS timetable_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch TEXT,
    year INTEGER,
    semester INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS timetable_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_id INTEGER,
    day TEXT,
    period INTEGER,
    subject TEXT
)
""")

# Create Notices table (Missing in original file)
cursor.execute("""
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    date TEXT
)
""")

conn.commit()
conn.close()

print("Tables created successfully")
