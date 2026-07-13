# 🎓 College Utility Portal

A functional Flask web application designed to streamline student life by managing schedules, assignments, and campus notices.

## 🚀 Features
- **Dashboard:** Centralized hub for student updates.
- **Timetable & Schedule:** Dynamic tracking of daily classes.
- **Assignment Tracker:** Keep tabs on upcoming academic deadlines.
- **File Uploads:** Secure portal for sharing notes and resources.

## 🛠️ Tech Stack
- **Backend:** Python, Flask
- **Database:** Supabase PostgreSQL
- **Frontend:** HTML5, CSS3, Flask templates

## 💻 Local Setup Instructions
1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate the environment and install dependencies.
4. Create a `.env` file based on `.env.example` and fill in your Supabase database URL and credentials.
5. Run the app: `python app.py`

## 🗂️ Local archive and security
- `database.db` is a local SQLite archive only and should not be committed to GitHub.
- `.env` is also excluded from version control.
- Archived SQLite helper scripts are stored in `archive_sqlite_scripts/` and are not part of the active app.
- Use `scripts/superbase.py` only for one-time migration of old SQLite user data into Supabase.

## 🚀 Deployment
- Your live app should connect to Supabase using `DATABASE_URL` in `.env`.
- Do not store secrets or local database files in the repository.
