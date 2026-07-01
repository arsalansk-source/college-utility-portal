import os
import sqlite3
import smtplib
import random
from email.mime.text import MIMEText
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)


def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def get_user(username, password):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    )

    user = cursor.fetchone()
    conn.close()
    return user

app.secret_key = os.getenv("APP_SECRET_KEY", "change-me")


UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if admin_username and admin_password and username == admin_username and password == admin_password:
            session["username"] = "Admin"
            session["role"] = "admin"
            return redirect(url_for("dashboard"))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT role FROM users
            WHERE username=? AND password=?
        """, (username, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = username
            session["role"] = user[0]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Login"

    return render_template("login.html")


#logout page
@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("role", None)
    return redirect(url_for("login"))

#register page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                (username, password, email, "student")
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# --- FORGOT PASSWORD LOGIC ---

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_email_otp(to_email, otp):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, "SMTP credentials are not configured. Set SMTP_EMAIL and SMTP_PASSWORD in your environment."

    try:
        msg = MIMEText(f"Your OTP for password reset is: {otp}")
        msg['Subject'] = 'Password Reset OTP - College Portal'
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email

        # Connect to Gmail SMTP Server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD.replace(" ", "")) # Removes spaces if you copied them
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        print(f"Email Error: {e}")
        return False, str(e)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = str(random.randint(100000, 999999))
            session["reset_otp"] = otp
            session["reset_email"] = email
            success, error_msg = send_email_otp(email, otp)
            if success:
                return redirect(url_for("verify_otp"))
            else:
                return f"Error sending email: {error_msg}"
        else:
            return "Email not found."
    return render_template("forgot_password.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if "reset_otp" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        user_otp = request.form["otp"]
        if user_otp == session["reset_otp"]:
            session["otp_verified"] = True
            return redirect(url_for("reset_password"))
        else:
            return "Invalid OTP"
    return render_template("verify_otp.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("otp_verified"):
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form["password"]
        email = session["reset_email"]
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
        conn.commit()
        conn.close()
        
        # Clear session
        session.pop("reset_otp", None)
        session.pop("reset_email", None)
        session.pop("otp_verified", None)
        
        return redirect(url_for("login"))
    return render_template("reset_password.html")


# Dashboard Page
@app.route("/dashboard")
def dashboard():
     if "username" not in session:
        return redirect(url_for("login"))
     
     pending_count = 0
     if session.get("role") == "admin":
         conn = sqlite3.connect("database.db")
         cursor = conn.cursor()
         try:
             cursor.execute("SELECT COUNT(*) FROM help_requests WHERE status='pending'")
             pending_count = cursor.fetchone()[0]
         except sqlite3.OperationalError:
             pass 
         conn.close()

     return render_template("dashboard.html", pending_count=pending_count)

#notes page
@app.route("/notes", methods=["GET", "POST"])
def notes():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        if session.get("role") != "admin":
            return redirect(url_for("notes"))

        file = request.files["note"]
        subject = request.form["subject"]

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            
            cursor.execute("INSERT INTO notes (filename, subject, upload_date) VALUES (?, ?, ?)",
                           (filename, subject, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

        conn.close()
        return redirect(url_for("notes"))

    cursor.execute("SELECT * FROM notes ORDER BY subject")
    notes_data = cursor.fetchall()
    conn.close()

    return render_template("notes.html", notes=notes_data)

@app.route("/delete-note/<int:id>")
def delete_note(id):
    if session.get("role") != "admin":
        return redirect(url_for("notes"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get filename to delete from disk
    cursor.execute("SELECT filename FROM notes WHERE id=?", (id,))
    row = cursor.fetchone()
    
    if row:
        filename = row[0]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        cursor.execute("DELETE FROM notes WHERE id=?", (id,))
        conn.commit()

    conn.close()
    return redirect(url_for("notes"))

from flask import send_from_directory

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


#timetable page
@app.route("/timetable", methods=["GET", "POST"])
def timetable():
     

     timetable_data = {}   # ✅ ALWAYS defined

     if request.method == "POST":
        branch = request.form["branch"]
        year = request.form["year"]
        semester = request.form["semester"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM timetable_meta
            WHERE branch=? AND year=? AND semester=?
        """, (branch, year, semester))

        row = cursor.fetchone()

        if row:
            timetable_id = row[0]

            cursor.execute("""
                SELECT day, period, subject
                FROM timetable_slots
                WHERE timetable_id=?
            """, (timetable_id,))

            for day, period, subject in cursor.fetchall():
                timetable_data[(day, period)] = subject

        conn.close()

        return render_template(
            "timetable.html",
            timetable_data=timetable_data,
            branch=branch,
            year=year,
            semester=semester
        )

     # ✅ IMPORTANT: EVEN ON GET, SEND timetable_data
     return render_template(
        "timetable.html",
        timetable_data=timetable_data
    )

@app.route("/admin/timetable", methods=["GET", "POST"])
def admin_timetable():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        branch = request.form["branch"]
        year = request.form["year"]
        semester = request.form["semester"]
        day = request.form["day"]
        period = int(request.form["period"])
        subject = request.form["subject"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # 1️⃣ Get or create timetable_meta
        cursor.execute("""
            SELECT id FROM timetable_meta
            WHERE branch=? AND year=? AND semester=?
        """, (branch, year, semester))

        row = cursor.fetchone()

        if row:
            timetable_id = row[0]
        else:
            cursor.execute("""
                INSERT INTO timetable_meta (branch, year, semester)
                VALUES (?, ?, ?)
            """, (branch, year, semester))
            timetable_id = cursor.lastrowid

        # 2️⃣ Check if slot exists
        cursor.execute("""
            SELECT id FROM timetable_slots
            WHERE timetable_id=? AND day=? AND period=?
        """, (timetable_id, day, period))

        slot = cursor.fetchone()

        if slot:
            cursor.execute("""
                UPDATE timetable_slots
                SET subject=?
                WHERE id=?
            """, (subject, slot[0]))
            message = "Timetable updated successfully"
        else:
            cursor.execute("""
                INSERT INTO timetable_slots (timetable_id, day, period, subject)
                VALUES (?, ?, ?, ?)
            """, (timetable_id, day, period, subject))
            message = "Subject added successfully"

        conn.commit()
        conn.close()

    return render_template("admin_timetable.html", message=message)



@app.route("/assignments")
def assignments():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assignments ORDER BY deadline ASC")
    assignments = cursor.fetchall()
    conn.close()
    
    return render_template("assignments.html", assignments=assignments)

@app.route("/add-assignment", methods=["GET", "POST"])
def add_assignment():
    if session.get("role") != "admin":
        return redirect(url_for("assignments"))

    if request.method == "POST":
        subject = request.form["subject"]
        title = request.form["title"]
        deadline = request.form["deadline"]
        
        # Handle File Upload
        file = request.files["assignment_file"]
        filename = ""
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO assignments (subject, title, deadline, filename) VALUES (?, ?, ?, ?)", 
                       (subject, title, deadline, filename))
        conn.commit()
        conn.close()
        return redirect(url_for("assignments"))

    return render_template("add_assignment.html")

@app.route("/delete-assignment/<int:id>")
def delete_assignment(id):
    if session.get("role") != "admin":
        return redirect(url_for("assignments"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Delete the file from the folder first
    cursor.execute("SELECT filename FROM assignments WHERE id=?", (id,))
    row = cursor.fetchone()
    if row and row[0]:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], row[0])
        if os.path.exists(file_path):
            os.remove(file_path)
            
    cursor.execute("DELETE FROM assignments WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("assignments"))


#Notices    
@app.route("/notices")
def notices():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content, date FROM notices ORDER BY id DESC")
    notices = cursor.fetchall()

    conn.close()
    return render_template("notices.html", notices=notices)

#add notices
@app.route("/add-notice", methods=["GET", "POST"])
def add_notice():
    if session.get("role") != "admin":
        return redirect(url_for("notices"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%d-%m-%Y")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO notices (title, content, date) VALUES (?, ?, ?)",
            (title, content, date)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("notices"))

    return render_template("add_notice.html")

@app.route("/delete-notice/<int:notice_id>")
def delete_notice(notice_id):
    if session.get("role") != "admin":
        return redirect(url_for("notices"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("notices"))

@app.route("/help", methods=["GET", "POST"])
def help_page():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Handle Submission (Student)
    if request.method == "POST":
        req_type = request.form.get("type") # complaint or request
        message = request.form.get("message")
        username = session["username"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("INSERT INTO help_requests (username, type, message, created_at) VALUES (?, ?, ?, ?)",
                       (username, req_type, message, created_at))
        conn.commit()
        conn.close()
        return redirect(url_for("help_page"))

    # View Logic
    requests_list = []
    if session.get("role") == "admin":
        cursor.execute("SELECT * FROM help_requests ORDER BY id DESC")
        requests_list = cursor.fetchall()
    else:
        # Student sees their own history
        cursor.execute("SELECT * FROM help_requests WHERE username=? ORDER BY id DESC", (session["username"],))
        requests_list = cursor.fetchall()
    
    conn.close()
    
    # Check for mode query param (for pre-selecting radio button)
    mode = request.args.get("mode", "complaint")
    
    return render_template("help.html", requests=requests_list, mode=mode)

@app.route("/help/resolve/<int:id>")
def resolve_help(id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
        
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE help_requests SET status='solved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("help_page"))

@app.route("/manage-students")
def manage_students():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Fetch all users who are NOT admins
    cursor.execute("SELECT * FROM users WHERE role != 'admin'")
    users = cursor.fetchall()
    conn.close()
    
    return render_template("manage_students.html", users=users)

@app.route("/delete-user/<int:id>")
def delete_user(id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
        
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage_students"))




# Run the app (ONLY ONCE)
if __name__ == "__main__":
    app.run(debug=True)
