COMPESA 3.0 — One-package Event Portal
=======================================
Requirements: Python 3.10+ only. No pip installs. SQLite is built into Python.

Run:
  python app.py
Open:
  http://localhost:8000

Admin:
  username: admin
  password: admin123

Student:
  Sign up from Student Login.

Included:
- Separate student panel; students never see other students/registrations.
- Unique Student ID and unique event Registration ID.
- Student profile and private registration history.
- Private digital event pass.
- Bookmarks/favourites.
- Search/filter events.
- Notifications and announcement badges.
- Cash/Online payment choice and payment reference.
- Admin can add/edit event name, date, time, venue, rules, eligibility, prizes, deadlines, status and payment details.
- Admin can paste a payment QR image as a data:image/...;base64,... value in the event editor.
- Public event page displays admin's payment QR.
- Google Calendar button.
- Live published results.
- Private certificates + public certificate verification URL: /verify?id=COMPESA-2026-XXXXX
- Print/Save as PDF for pass/certificate from browser.
- Admin participant list, attendance, results and CSV export.
- Registration confirmation email integration.

REAL EMAIL:
The app can send real email through SMTP, but an email server/account is necessarily required. Configure before running:
  Windows PowerShell:
    $env:SMTP_HOST="smtp.example.com"
    $env:SMTP_PORT="587"
    $env:SMTP_USER="your@email.com"
    $env:SMTP_PASSWORD="your-app-password"
    $env:SMTP_FROM="your@email.com"
  python app.py

If SMTP is not configured, registration still succeeds and the student gets an in-panel notification; the app does not pretend an email was sent.

SECURITY NOTE:
For production deployment, use HTTPS, stronger admin authentication, CSRF protection, and a real QR scanner/service. This package is designed to run locally with zero external software.
