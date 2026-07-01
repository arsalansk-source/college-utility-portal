import sqlite3

def add_email():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        # Add email column to users table
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()
        print("Success: Column 'email' added to users table.")
    except sqlite3.OperationalError:
        print("Info: Column 'email' might already exist.")
    conn.close()

if __name__ == "__main__":
    add_email()