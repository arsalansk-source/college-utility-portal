import sqlite3
import os

def fix_notes():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            subject TEXT NOT NULL,
            upload_date TEXT
        )
    """)
    
    # Migrate existing files (if any) so they don't disappear
    upload_folder = "static/uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    existing_files = os.listdir(upload_folder)
    for filename in existing_files:
        # Check if already in DB
        cursor.execute("SELECT id FROM notes WHERE filename=?", (filename,))
        if not cursor.fetchone():
            print(f"Migrating {filename}...")
            cursor.execute("INSERT INTO notes (filename, subject, upload_date) VALUES (?, ?, ?)", 
                           (filename, "General", "2023-01-01"))

    conn.commit()
    conn.close()
    print("Notes table created and existing files migrated.")

if __name__ == "__main__":
    fix_notes()