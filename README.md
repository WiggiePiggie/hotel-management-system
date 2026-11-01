# Hotel Management & Reservation System

A modular **Python desktop application** that demonstrates hotel operations workflows, relational database design, and practical business logic. Prepared as a **software engineering portfolio project** using anonymized source code (no client or financial records).

> **Portfolio / educational use only.** The application is not audited for production use and does not replace professional hotel management software.

## Main features

- Room and guest management; room status, capacity and price settings
- **Multi-room reservations** with date-overlap checks and total capacity validation
- Check-in / check-out workflows, cancellations, a calendar view and audit logs
- Payments, optional services, balances and occupancy/revenue dashboards
- Export to CSV, Excel and PDF invoices; local SQLite backups
- Desktop interface in English and Albanian, using CustomTkinter
- Local multi-user roles with first-run administrator setup

## Screenshots

The screenshots below show a **local demonstration** of the desktop interface. Names, room data and payment amounts are for demonstration only; no production database is committed to this repository.

### Dashboard
![Hotel operations dashboard](docs/screenshots/Screenshot%202026-11-01%20170558.png)

### Reservations
![Multi-room reservation management](docs/screenshots/Screenshot%202026-11-01%20171104.png)

### Availability calendar
![Calendar showing room occupancy by date](docs/screenshots/Screenshot%202026-11-01%20171115.png)

### Reports
![Daily income and reporting](docs/screenshots/Screenshot%202026-11-01%20171134.png)

## Tech stack

**Python 3.11+**, CustomTkinter, SQLite, tkcalendar, Matplotlib, OpenPyXL, ReportLab. The core DB integration tests use Python's built-in `unittest` and temporary databases.

## Run locally

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
pythonmain.py
```

On first launch, the application asks you to create an administrator account with a password of at least 10 characters. **No default usernames or passwords are shipped.** The local database is created only when you start the program; it is excluded from Git.

This is a desktop GUI and needs an environment with a display server. A compiled Windows installer is not included.

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite exercises password storage and login, reservation collisions, simultaneous bookings, rollback on failed updates, money validation, guest/room history safeguards, SQLite backup/restore, and date utilities. Passing tests does **not** mean the GUI has been fully tested.

## Structure

```text
main.py               CustomTkinter entry point and navigation
database.py          Schema, SQLite access, business operations
pages/               Reservations, rooms, guests, payment and report screens
ui/                  Login, translations and reusable widgets
utils.py             Date and price helper functions
tests/               Automated utility and integration tests
.github/workflows/   Continuous integration
```

## Technical safeguards and limitations

- Passwords are salted and hashed using **PBKDF2-HMAC-SHA256** (390,000 iterations). On trusted legacy databases, plaintext passwords are hashed on first startup; existing weak passwords should then be changed.
- New administrator credentials are created on first launch rather than embedding demo credentials.
- A reservation's availability checks and database writes share a **`BEGIN IMMEDIATE` SQLite transaction**, preventing concurrent double-bookings by cooperating application instances using the same DB.
- Currency amounts are checked using `Decimal` and rounded to two decimal places before saving. **SQLite storage still uses `REAL`**, so an integer-cent migration is required for production-grade accounting.
- Guests/rooms with linked reservation history cannot be deleted, and the last administrator cannot be removed or demoted.
- Backups use SQLite's backup API rather than copying the live SQLite file.

**Not production-hardened:** role authorization is mainly enforced through the desktop UI, not a centralized service authorization layer; the GUI and all operational paths have not been end-to-end tested; and business-specific policies and data retention still need validation. See [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

## Portfolio demo notes

- The four screenshots above demonstrate the dashboard, multi-room reservations, availability calendar and reporting screens.
- For additional demonstrations, use a **fresh test database and fictitious guests** only.
- Explain the atomic booking transaction and related regression tests in technical interviews.

## Privacy and intellectual property

The repository package **does not include** any original `.db` files, backups, exports, compiled executables, customer information or production screenshots. If the original project was developed for a business, obtain permission before publishing source code or business assets. This repository intentionally contains **no public-use software license** until the rights holder decides how it may be licensed.
