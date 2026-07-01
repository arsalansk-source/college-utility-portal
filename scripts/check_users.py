import sqlite3

def view_users():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Force all users to be students (fixes NULL roles and enforces rule)
    try:
        cursor.execute("UPDATE users SET role = 'student'")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    print(f"{'ID':<5} {'Username':<20} {'Password':<20} {'Role':<10} {'Email':<25}")
    print("-" * 85)

    try:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            # user tuple is (id, username, password, role, email)
            role = user[3] if user[3] else "student"
            email = user[4] if len(user) > 4 and user[4] else "N/A"
            print(f"{user[0]:<5} {user[1]:<20} {user[2]:<20} {role:<10} {email:<25}")
    except sqlite3.OperationalError:
        print("The 'users' table does not exist yet.")

    conn.close()

if __name__ == "__main__":
    view_users()