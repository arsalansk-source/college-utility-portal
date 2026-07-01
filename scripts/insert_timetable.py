import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# 1️⃣ Create timetable meta
cursor.execute("""
INSERT INTO timetable_meta (branch, year, semester)
VALUES ('CSE', 2, 4)
""")

timetable_id = cursor.lastrowid

# 2️⃣ Insert subjects
slots = [
    ("Monday", 1, "OS"),
    ("Monday", 2, "DBMS"),
    ("Monday", 3, "CN"),
    ("Tuesday", 1, "DBMS"),
    ("Tuesday", 2, "OS"),
    ("Wednesday", 4, "SE"),
    ("Friday", 6, "AI"),
]

for day, period, subject in slots:
    cursor.execute("""
        INSERT INTO timetable_slots (timetable_id, day, period, subject)
        VALUES (?, ?, ?, ?)
    """, (timetable_id, day, period, subject))

conn.commit()
conn.close()

print("Sample timetable inserted")
