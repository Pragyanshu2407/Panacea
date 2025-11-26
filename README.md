# College ERP – Minor Project

An end‑to‑end campus management system built with Django. It provides dashboards for Admin, Staff, and Students, covering attendance, timetables, notifications, MCQ tests, results, fees, and more.

## Demo Accounts

Use these sample credentials after seeding your data or on the current demo:

- Admin: create via `python manage.py createsuperuser` (example used: email `admin@cms.local`, password `admin123`)
- Teacher: email `bhuvana@gmail.com`, password `bhuvana`
- Student: email `pragyanshu@gmail.com`, password `pragyanshum`

## Screenshots

Dashboard and UI are based on AdminLTE. Sample images:

![Dashboard](main_app/static/dist/img/virusx.png)

> Replace/append with your own screenshots as needed.

## Key Features

- Role‑based dashboards for Admin, Staff, and Students
- Notifications panel with 7‑day trends
- Attendance, feedback, leave analytics (Admin)
- Timetable management with rooms and capacities
- MCQ tests creation, scheduling, and submissions
- Notes upload and student access
- Leave requests with attachments (visible to Proctor and HOD)
- Results entry with components:
  - Test 1, Test 2, Quiz, Experiential Learning, SEE
  - Student view shows the breakdown and total

## Requirements

- Python 3.10+
- Django 3.1.1
- Recommended: virtualenv
- Optional: MySQL connector (`mysql-connector==2.2.9`) if using MySQL
- See `requirements.txt` for full list

## Quick Start (Local)

```bash
python3 -m venv .venv310
source .venv310/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # set your admin email/password
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000/` and log in with the accounts above.

## Environment & Configuration

- Default DB: SQLite (suitable for local dev). For MySQL, configure `DATABASES` in `college_management_system/settings.py` and install `mysql-connector`.
- Static and media files:
  - Static assets under `main_app/static/`
  - Uploaded media under `media/`
- Recommended OS: macOS/Linux; Windows also works with equivalent commands.

## Project Structure (Highlights)

- `main_app/models.py` – core data models (Users, Attendance, Timetable, Results, etc.)
- `main_app/hod_views.py` – admin views and dashboards
- `main_app/staff_views.py` – staff views (attendance, tests, results, notes)
- `main_app/student_views.py` – student views (results, notes, tests)
- `main_app/templates/` – role‑specific pages (`hod_template/`, `staff_template/`, `student_template/`)

## Results Entry – Teachers

Teachers can add results per student and subject with fields:

- Test 1
- Test 2
- Quiz
- Experiential Learning
- SEE

Students can view the detailed breakdown and total on their “View Results” page.

## Timetable & Rooms

Under Manage Timetable, rooms can be added with capacity, and an “Existing Rooms” table lists current rooms for quick reference.

## Notes & MCQ Tests

Staff can upload notes per subject, create MCQ tests, add questions, and manage schedules. Students can access notes and take available tests.