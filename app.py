import os
import psycopg2
import smtplib
import random
import traceback
from email.mime.text import MIMEText
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db_path, init_db, get_db_connection

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
init_db()


def get_conn():
    return get_db_connection()


def get_user(username, password):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password)
    )

    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def store_next_url():
    next_url = request.full_path if request.method == "GET" else request.path
    if next_url.endswith("?"):
        next_url = next_url[:-1]
    session["next_url"] = next_url


@app.before_request
def ensure_guest_role():
    if not session.get("authenticated"):
        session["role"] = "guest"
        session["username"] = None
        session["authenticated"] = False


def is_admin():
    return session.get("role", "guest").lower() == "admin"


def is_student():
    return session.get("role", "guest").lower() == "student"


app.secret_key = os.getenv("APP_SECRET_KEY", "change-me")
app.config["SESSION_PERMANENT"] = False


UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# Ensure upload folder exists (use absolute path based on this file)
uploads_abs = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER)
os.makedirs(uploads_abs, exist_ok=True)

SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_email(to_email, subject, body):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False, "SMTP credentials are not configured. Set SMTP_EMAIL and SMTP_PASSWORD in your environment."

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD.replace(" ", ""))
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        print(f"Email Error: {e}")
        return False, str(e)


def send_email_otp(to_email, otp):
    return send_email(
        to_email,
        "Password Reset OTP - College Portal",
        f"Your OTP for password reset is: {otp}"
    )


def send_verification_email(to_email, otp):
    return send_email(
        to_email,
        "Verify Your College Portal Account",
        f"Your verification OTP is: {otp}. Enter this code on the verification page to complete your registration."
    )


# Global error handler to log unexpected exceptions to the server logs
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.exception("Unhandled exception occurred: %s", e)
    return "Internal Server Error", 500


# Redirect root to dashboard and force a fresh guest session on app open
@app.route("/")
def index():
    session.clear()
    session["role"] = "guest"
    session["username"] = None
    session["authenticated"] = False
    return redirect(url_for("dashboard"))

# Shared portal login for student and admin users
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_username and admin_password and username == admin_username and password == admin_password:
            session["username"] = username
            session["role"] = "admin"
            session["authenticated"] = True
            next_url = session.pop("next_url", None)
            return redirect(next_url or url_for("dashboard"))

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, is_verified FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return "Invalid portal credentials."

        role, is_verified = user
        if role is None:
            return "Invalid portal credentials."

        role_upper = role.upper().strip()
        if role_upper not in ("STUDENT", "ADMIN"):
            return "Invalid role. Please contact support."

        if role_upper == "STUDENT" and not is_verified:
            return "Email not verified. Please verify your account before logging in."

        session["username"] = username
        session["role"] = role_upper.lower()
        session["authenticated"] = True

        next_url = session.pop("next_url", None)
        return redirect(next_url or url_for("dashboard"))

    return render_template("login.html")


#logout page
@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("role", None)
    session.pop("authenticated", None)
    session.pop("next_url", None)
    return redirect(url_for("login"))

#register page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        conn = get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password, email, role, is_verified) VALUES (%s, %s, %s, %s, %s)",
                (username, password, email, "student", 0)
            )
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            cursor.close()
            conn.close()
            return "Username already exists"

        otp = str(random.randint(100000, 999999))
        session["verification_otp"] = otp
        session["verification_email"] = email
        session["verification_username"] = username

        success, error_msg = send_verification_email(email, otp)
        if success:
            cursor.close()
            conn.close()
            return redirect(url_for("verify_email"))
        else:
            cursor.close()
            conn.close()
            return f"Error sending verification email: {error_msg}"

    return render_template("register.html")


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    if "verification_otp" not in session:
        return redirect(url_for("register"))

    message = None
    if request.method == "POST":
        if "resend" in request.form:
            email = session.get("verification_email")
            if not email:
                return redirect(url_for("register"))

            otp = str(random.randint(100000, 999999))
            session["verification_otp"] = otp
            success, error_msg = send_verification_email(email, otp)
            if success:
                message = "Verification code resent to your email."
            else:
                message = f"Error resending verification email: {error_msg}"
            return render_template("verify_email.html", message=message)

        user_otp = request.form["otp"]
        if user_otp == session["verification_otp"]:
            email = session.get("verification_email")
            username = session.get("verification_username")

            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_verified=1 WHERE username=%s AND email=%s",
                (username, email)
            )
            conn.commit()
            cursor.close()
            conn.close()

            session.pop("verification_otp", None)
            session.pop("verification_email", None)
            session.pop("verification_username", None)

            return redirect(url_for("login"))
        else:
            message = "Invalid verification code"

    return render_template("verify_email.html", message=message)


# --- FORGOT PASSWORD LOGIC ---

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
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
        
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
        conn.commit()
        cursor.close()
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
    username = session.get("username")
    role = session.get("role")
    pending_count = 0

    if role and role.upper() == "ADMIN":
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM help_requests WHERE status='pending'")
            pending_count = cursor.fetchone()[0]
        except Exception:
            pass
        cursor.close()
        conn.close()

    return render_template("dashboard.html", pending_count=pending_count, username=username, role=role)

#notes page
@app.route("/notes", methods=["GET", "POST"])
def notes():
    conn = get_conn()
    cursor = conn.cursor()

    if request.method == "POST":
        if not is_admin():
            cursor.close()
            conn.close()
            return redirect(url_for("notes"))

        file = request.files["note"]
        subject = request.form["subject"]

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            
            cursor.execute("INSERT INTO notes (filename, subject, upload_date) VALUES (%s, %s, %s)",
                           (filename, subject, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for("notes"))

    cursor.execute("SELECT id, filename, subject, upload_date FROM notes ORDER BY subject")
    notes_data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("notes.html", notes=notes_data)

@app.route("/delete-note/<int:id>")
def delete_note(id):
    if session.get("role") != "admin":
        return redirect(url_for("notes"))

    conn = get_conn()
    cursor = conn.cursor()

    # Get filename to delete from disk
    cursor.execute("SELECT filename FROM notes WHERE id=%s", (id,))
    row = cursor.fetchone()
    
    if row:
        filename = row[0]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        cursor.execute("DELETE FROM notes WHERE id=%s", (id,))
        conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("notes"))

from flask import send_from_directory

@app.route("/download/<filename>")
def download(filename):
    if "username" not in session:
        return redirect(url_for("login"))
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


#timetable page
@app.route("/timetable", methods=["GET", "POST"])
def timetable():
     

     timetable_data = {}   # ✅ ALWAYS defined

     if request.method == "POST":
        branch = request.form["branch"]
        year = request.form["year"]
        semester = request.form["semester"]

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM timetable_meta WHERE branch=%s AND year=%s AND semester=%s",
            (branch, year, semester))

        row = cursor.fetchone()

        if row:
            timetable_id = row[0]

            cursor.execute("SELECT day, period, subject FROM timetable_slots WHERE timetable_id=%s", (timetable_id,))

            for day, period, subject in cursor.fetchall():
                timetable_data[(day, period)] = subject

        cursor.close()
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
    if not is_admin():
        return redirect(url_for("login"))

    message = ""
    if request.method == "POST":
        branch = request.form["branch"]
        year = request.form["year"]
        semester = request.form["semester"]
        day = request.form["day"]
        period = int(request.form["period"])
        subject = request.form["subject"]

        conn = get_conn()
        cursor = conn.cursor()

        # 1️⃣ Get or create timetable_meta
        cursor.execute("SELECT id FROM timetable_meta WHERE branch=%s AND year=%s AND semester=%s", (branch, year, semester))

        row = cursor.fetchone()

        if row:
            timetable_id = row[0]
        else:
            cursor.execute("INSERT INTO timetable_meta (branch, year, semester) VALUES (%s, %s, %s)", (branch, year, semester))
            # fetch the id we just created
            cursor.execute("SELECT id FROM timetable_meta WHERE branch=%s AND year=%s AND semester=%s", (branch, year, semester))
            timetable_id = cursor.fetchone()[0]

        # 2️⃣ Check if slot exists
        cursor.execute("SELECT id FROM timetable_slots WHERE timetable_id=%s AND day=%s AND period=%s", (timetable_id, day, period))

        slot = cursor.fetchone()

        if slot:
            cursor.execute("UPDATE timetable_slots SET subject=%s WHERE id=%s", (subject, slot[0]))
            message = "Timetable updated successfully"
        else:
            cursor.execute("INSERT INTO timetable_slots (timetable_id, day, period, subject) VALUES (%s, %s, %s, %s)", (timetable_id, day, period, subject))
            message = "Subject added successfully"

        conn.commit()
        cursor.close()
        conn.close()

    return render_template("admin_timetable.html", message=message)



@app.route("/assignments")
def assignments():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, title, deadline, filename FROM assignments ORDER BY deadline ASC")
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("assignments.html", assignments=assignments)

@app.route("/add-assignment", methods=["GET", "POST"])
def add_assignment():
    if not is_admin():
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

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO assignments (subject, title, deadline, filename) VALUES (%s, %s, %s, %s)", 
                       (subject, title, deadline, filename))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("assignments"))

    return render_template("add_assignment.html")

@app.route("/delete-assignment/<int:id>")
def delete_assignment(id):
    if not is_admin():
        return redirect(url_for("assignments"))

    conn = get_conn()
    cursor = conn.cursor()
    
    # Delete the file from the folder first
    cursor.execute("SELECT filename FROM assignments WHERE id=%s", (id,))
    row = cursor.fetchone()
    if row and row[0]:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], row[0])
        if os.path.exists(file_path):
            os.remove(file_path)
            
    cursor.execute("DELETE FROM assignments WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("assignments"))


#Notices    
@app.route("/notices")
def notices():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content, date FROM notices ORDER BY id DESC")
    notices = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("notices.html", notices=notices)

#add notices
@app.route("/add-notice", methods=["GET", "POST"])
def add_notice():
    if not is_admin():
        return redirect(url_for("notices"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = datetime.now().strftime("%d-%m-%Y")

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO notices (title, content, date) VALUES (%s, %s, %s)",
            (title, content, date)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("notices"))

    return render_template("add_notice.html")

@app.route("/delete-notice/<int:notice_id>")
def delete_notice(notice_id):
    if not is_admin():
        return redirect(url_for("notices"))

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM notices WHERE id = %s", (notice_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("notices"))

@app.route("/help", methods=["GET", "POST"])
def help_page():
    user = session.get("username")
    role = session.get("role")

    conn = get_conn()
    cursor = conn.cursor()

    # Handle Submission (Student)
    if request.method == "POST":
        if not user:
            cursor.close()
            conn.close()
            return redirect(url_for("login"))

        req_type = request.form.get("type") # complaint or request
        message = request.form.get("message")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("INSERT INTO help_requests (username, type, message, created_at) VALUES (%s, %s, %s, %s)",
                       (user, req_type, message, created_at))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("help_page"))

    # View Logic
    requests_list = []
    if role == "admin":
        cursor.execute("SELECT id, username, type, message, created_at, status FROM help_requests ORDER BY id DESC")
        requests_list = cursor.fetchall()
    elif user:
        cursor.execute("SELECT id, username, type, message, created_at, status FROM help_requests WHERE username=%s ORDER BY id DESC", (user,))
        requests_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Check for mode query param (for pre-selecting radio button)
    mode = request.args.get("mode", "complaint")
    
    return render_template("help.html", requests=requests_list, mode=mode, user=user, role=role)

@app.route("/help/resolve/<int:id>")
def resolve_help(id):
    if not is_admin():
        return redirect(url_for("dashboard"))
        
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE help_requests SET status='solved' WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("help_page"))

@app.route("/manage-students")
def manage_students():
    if not is_admin():
        return redirect(url_for("dashboard"))
    
    conn = get_conn()
    cursor = conn.cursor()
    # Fetch all users who are NOT admins
    cursor.execute("SELECT id, username, password, email, role, is_verified FROM users WHERE role != 'admin'")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("manage_students.html", users=users)

@app.route("/student/<int:user_id>")
def student_details(user_id):
    if not is_admin():
        return redirect(url_for("dashboard"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, email, role, is_verified FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return "Student not found"

    return render_template("student_details.html", user=user)

@app.route("/delete-user/<int:id>")
def delete_user(id):
    if not is_admin():
        return redirect(url_for("dashboard"))
        
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("manage_students"))




# Run the app (ONLY ONCE)
if __name__ == "__main__":
    app.run(debug=True)
