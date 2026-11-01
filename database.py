import csv
import json
import os
import shutil
import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from secrets import token_bytes
import hashlib
import hmac
from datetime import datetime, timedelta

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from utils import DATE_FMT, parse_date


class DatabaseManager:
    def __init__(self, db_path='hotel_modern.db'):
        self.db_path = db_path
        self.create_tables()
        self.seed_settings()
        self.migrate_passwords()

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        return conn

    def create_tables(self):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_number TEXT UNIQUE NOT NULL,
                    room_type TEXT NOT NULL,
                    capacity INTEGER NOT NULL,
                    price_per_night REAL NOT NULL,
                    floor_no INTEGER DEFAULT 1,
                    breakfast_included INTEGER DEFAULT 0,
                    sea_view INTEGER DEFAULT 0,
                    smoking_allowed INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Available'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    id_number TEXT,
                    nationality TEXT,
                    address TEXT,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guest_id INTEGER NOT NULL,
                    room_id INTEGER,
                    check_in TEXT NOT NULL,
                    check_out TEXT NOT NULL,
                    adults INTEGER NOT NULL DEFAULT 1,
                    children INTEGER NOT NULL DEFAULT 0,
                    total_price REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Reserved',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE,
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
                )
            """)
            try:
                conn.execute("ALTER TABLE reservations ADD COLUMN notes TEXT")
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reservation_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reservation_id INTEGER NOT NULL,
                    room_id INTEGER NOT NULL,
                    room_price REAL NOT NULL,
                    room_notes TEXT,
                    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
                    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                INSERT INTO reservation_rooms (reservation_id, room_id, room_price, room_notes)
                SELECT r.id, r.room_id, COALESCE((SELECT price_per_night FROM rooms rm WHERE rm.id = r.room_id), 0), ''
                FROM reservations r
                WHERE r.room_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM reservation_rooms rr
                      WHERE rr.reservation_id = r.id AND rr.room_id = r.room_id
                  )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reservation_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    method TEXT NOT NULL,
                    paid_at TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reservation_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS form_drafts (
                    form_name TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    username TEXT,
                    action TEXT NOT NULL,
                    details TEXT
                )
            """)

    # Each hash has an individual salt; no demo accounts or passwords are embedded.
    HASH_PREFIX = 'pbkdf2_sha256'
    HASH_ITERATIONS = 390_000

    @classmethod
    def hash_password(cls, password):
        if not isinstance(password, str) or len(password) < 10:
            raise ValueError('Password must be at least 10 characters long.')
        salt = token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, cls.HASH_ITERATIONS)
        return f'{cls.HASH_PREFIX}${cls.HASH_ITERATIONS}${salt.hex()}${digest.hex()}'

    @classmethod
    def verify_password(cls, password, stored):
        if not isinstance(stored, str) or not stored.startswith(cls.HASH_PREFIX + '$'):
            return False
        try:
            alg, iterations, salt, digest = stored.split('$')
            count = int(iterations)
            if not 100_000 <= count <= 1_000_000:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), count)
            return hmac.compare_digest(actual, bytes.fromhex(digest))
        except (TypeError, ValueError, OverflowError):
            return False

    def migrate_passwords(self):
        """One-time local DB migration from the previous plaintext format.

        Use with a trusted local database only; original data is never published.
        """
        with closing(self.connect()) as conn, conn:
            rows = conn.execute('SELECT id, password FROM users').fetchall()
            for row in rows:
                if not row['password'].startswith(self.HASH_PREFIX + '$'):
                    # Existing short passwords are still usable after migration,
                    # but users should change them. New passwords require 10 chars.
                    raw = row['password']
                    salt = token_bytes(16)
                    digest = hashlib.pbkdf2_hmac('sha256', raw.encode('utf-8'), salt, self.HASH_ITERATIONS)
                    encoded = f'{self.HASH_PREFIX}${self.HASH_ITERATIONS}${salt.hex()}${digest.hex()}'
                    conn.execute('UPDATE users SET password=? WHERE id=?', (encoded, row['id']))

    def has_users(self):
        with closing(self.connect()) as conn:
            return bool(conn.execute('SELECT 1 FROM users LIMIT 1').fetchone())

    def setup_admin(self, username, password):
        if not username or not username.strip():
            raise ValueError('Username is required.')
        encoded = self.hash_password(password)
        with closing(self.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                if conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                    raise ValueError('An administrator account already exists.')
                conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                             (username.strip(), encoded, 'admin'))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        self.log_action('setup_admin', 'Initial admin account created', username.strip())

    def seed_settings(self):
        with closing(self.connect()) as conn, conn:
            default_settings = {
                'hotel_name': 'Hotel Reservation System',
                'hotel_address': '',
                'hotel_phone': '',
                'hotel_email': '',
                'hotel_logo_path': '',
                'invoice_footer': 'Thank you for staying with us.'
            }
            for key, value in default_settings.items():
                conn.execute('INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)', (key, value))

    @staticmethod
    def money(value, *, allow_zero=True):
        """Validate finite inputs and quantize to two decimal places.

        The legacy DB uses SQLite REAL; changing to integer cents needs a
        separate data migration and is outside this portfolio demonstration.
        """
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
                raise ValueError('Amount must be positive and finite.')
            return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError):
            raise ValueError('Enter a valid monetary amount.') from None

    def log_action(self, action, details='', username='system'):
        with closing(self.connect()) as conn, conn:
            conn.execute(
                'INSERT INTO audit_logs (created_at, username, action, details) VALUES (?, ?, ?, ?)',
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username, action, details)
            )

    def fetch_audit_logs(self, search_text=''):
        q = 'SELECT * FROM audit_logs'
        params = []
        if search_text:
            q += ' WHERE username LIKE ? OR action LIKE ? OR details LIKE ?'
            pat = f'%{search_text}%'
            params = [pat, pat, pat]
        q += ' ORDER BY id DESC LIMIT 500'
        with closing(self.connect()) as conn:
            return conn.execute(q, params).fetchall()

    def list_users(self):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT id, username, role FROM users ORDER BY username COLLATE NOCASE').fetchall()

    def create_user(self, username, password, role, actor='system'):
        if not username or not password:
            raise ValueError('Username and password are required.')
        if role not in ('admin', 'manager', 'reception'):
            raise ValueError('Invalid role.')
        encoded = self.hash_password(password)
        with closing(self.connect()) as conn, conn:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, encoded, role))
        self.log_action('create_user', f'Created user {username} ({role})', actor)

    def update_user(self, user_id, username, role, actor='system'):
        if not username:
            raise ValueError('Username is required.')
        if role not in ('admin', 'manager', 'reception'):
            raise ValueError('Invalid role.')
        with closing(self.connect()) as conn, conn:
            row = conn.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()
            if row is None:
                raise ValueError('User not found.')
            if row['role'] == 'admin' and role != 'admin':
                if conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
                    raise ValueError('Cannot demote the last administrator.')
            conn.execute('UPDATE users SET username=?, role=? WHERE id=?', (username, role, user_id))
        self.log_action('update_user', f'Updated user #{user_id} -> {username} ({role})', actor)

    def reset_user_password(self, user_id, new_password, actor='system'):
        if not new_password:
            raise ValueError('New password cannot be empty.')
        encoded = self.hash_password(new_password)
        with closing(self.connect()) as conn, conn:
            row = conn.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
            if not row:
                raise ValueError('User not found.')
            conn.execute('UPDATE users SET password=? WHERE id=?', (encoded, user_id))
        self.log_action('reset_user_password', f'Reset password for {row["username"]}', actor)

    def delete_user(self, user_id, actor='system'):
        with closing(self.connect()) as conn, conn:
            row = conn.execute('SELECT username FROM users WHERE id=?', (user_id,)).fetchone()
            if not row:
                raise ValueError('User not found.')
            admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            role = conn.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()['role']
            if role == 'admin' and admin_count <= 1:
                raise ValueError('Cannot delete the last administrator.')
            conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        self.log_action('delete_user', f'Deleted user {row["username"]}', actor)

    def restore_database(self, backup_path, actor='system'):
        if not os.path.isfile(backup_path):
            raise ValueError('Backup file not found.')
        # Restore using SQLite's backup API rather than copying a live WAL DB.
        with closing(sqlite3.connect(f'file:{os.path.abspath(backup_path)}?mode=ro', uri=True)) as source:
            with closing(self.connect()) as target:
                source.backup(target)
        self.migrate_passwords()
        self.log_action('restore_database', 'Restored local backup', actor)

    def validate_login(self, username, password):
        with closing(self.connect()) as conn:
            row = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if row and self.verify_password(password, row['password']):
            self.log_action('login', 'Successful login', username)
        return row if row and self.verify_password(password, row['password']) else None

    def backup_database(self, backup_dir: str, actor='system'):
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        target = os.path.join(backup_dir, f'hotel_backup_{ts}.db')
        with closing(self.connect()) as source, closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
        self.log_action('backup_database', 'Created local database backup', actor)
        return target

    def save_form_draft(self, form_name, data_dict):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                INSERT INTO form_drafts (form_name, data)
                VALUES (?, ?)
                ON CONFLICT(form_name) DO UPDATE SET data=excluded.data
            """, (form_name, json.dumps(data_dict)))

    def load_form_draft(self, form_name):
        with closing(self.connect()) as conn:
            row = conn.execute('SELECT data FROM form_drafts WHERE form_name=?', (form_name,)).fetchone()
            if not row:
                return {}
            try:
                return json.loads(row['data'])
            except Exception:
                return {}

    def clear_form_draft(self, form_name):
        with closing(self.connect()) as conn, conn:
            conn.execute('DELETE FROM form_drafts WHERE form_name=?', (form_name,))

    # rooms
    def add_room(self, room_number, room_type, capacity, price_per_night, floor_no, breakfast_included, sea_view, smoking_allowed, status='Available'):
        if int(capacity) < 1:
            raise ValueError('Capacity must be at least one.')
        price_per_night = float(self.money(price_per_night))
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                INSERT INTO rooms (room_number, room_type, capacity, price_per_night, floor_no, breakfast_included, sea_view, smoking_allowed, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (room_number, room_type, capacity, price_per_night, floor_no, breakfast_included, sea_view, smoking_allowed, status))

    def update_room(self, room_id, room_number, room_type, capacity, price_per_night, floor_no, breakfast_included, sea_view, smoking_allowed, status):
        if int(capacity) < 1:
            raise ValueError('Capacity must be at least one.')
        price_per_night = float(self.money(price_per_night))
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                UPDATE rooms SET room_number=?, room_type=?, capacity=?, price_per_night=?, floor_no=?, breakfast_included=?, sea_view=?, smoking_allowed=?, status=?
                WHERE id=?
            """, (room_number, room_type, capacity, price_per_night, floor_no, breakfast_included, sea_view, smoking_allowed, status, room_id))

    def set_room_status(self, room_id, status):
        with closing(self.connect()) as conn, conn:
            conn.execute('UPDATE rooms SET status=? WHERE id=?', (status, room_id))

    def delete_room(self, room_id):
        with closing(self.connect()) as conn, conn:
            if conn.execute('SELECT 1 FROM reservation_rooms WHERE room_id=? LIMIT 1', (room_id,)).fetchone():
                raise ValueError('Cannot delete a room with reservation history.')
            conn.execute('DELETE FROM rooms WHERE id=?', (room_id,))

    def fetch_rooms(self, status_filter='', room_type_filter=''):
        q = 'SELECT * FROM rooms WHERE 1=1'
        params = []
        if status_filter:
            q += ' AND status=?'
            params.append(status_filter)
        if room_type_filter:
            q += ' AND room_type LIKE ?'
            params.append(f'%{room_type_filter}%')
        q += ' ORDER BY room_number COLLATE NOCASE'
        with closing(self.connect()) as conn:
            return conn.execute(q, params).fetchall()

    def get_room(self, room_id):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()

    def mark_room_clean(self, room_id):
        with closing(self.connect()) as conn, conn:
            active = conn.execute("SELECT COUNT(*) FROM reservations WHERE room_id=? AND status IN ('Reserved','Checked In')", (room_id,)).fetchone()[0]
            if active:
                status = 'Reserved'
            else:
                status = 'Available'
            conn.execute('UPDATE rooms SET status=? WHERE id=?', (status, room_id))

    # guests
    def add_guest(self, full_name, phone, email, id_number, nationality, address, notes):
        with closing(self.connect()) as conn, conn:
            cur = conn.execute("""
                INSERT INTO guests (full_name, phone, email, id_number, nationality, address, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (full_name, phone, email, id_number, nationality, address, notes))
            return cur.lastrowid

    def update_guest(self, guest_id, full_name, phone, email, id_number, nationality, address, notes):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                UPDATE guests SET full_name=?, phone=?, email=?, id_number=?, nationality=?, address=?, notes=? WHERE id=?
            """, (full_name, phone, email, id_number, nationality, address, notes, guest_id))

    def delete_guest(self, guest_id):
        with closing(self.connect()) as conn, conn:
            if conn.execute('SELECT 1 FROM reservations WHERE guest_id=? LIMIT 1', (guest_id,)).fetchone():
                raise ValueError('Cannot delete a guest with reservation/payment history.')
            conn.execute('DELETE FROM guests WHERE id=?', (guest_id,))

    def fetch_guests(self, search_text=''):
        q = 'SELECT * FROM guests'
        params = []
        if search_text:
            q += ' WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ? OR id_number LIKE ?'
            pat = f'%{search_text}%'
            params = [pat, pat, pat, pat]
        q += ' ORDER BY full_name COLLATE NOCASE'
        with closing(self.connect()) as conn:
            return conn.execute(q, params).fetchall()

    # reservations
    @staticmethod
    def _validate_stay(check_in, check_out):
        if parse_date(check_out) <= parse_date(check_in):
            raise ValueError('Check-out must be after check-in.')

    @staticmethod
    def _room_available_on_connection(conn, room_id, check_in, check_out, exclude_reservation_id=None):
        q = """
            SELECT COUNT(*) FROM reservation_rooms rr
            JOIN reservations r ON rr.reservation_id = r.id
            WHERE rr.room_id=? AND r.status IN ('Reserved','Checked In')
              AND NOT (r.check_out <= ? OR r.check_in >= ?)
        """
        params = [room_id, check_in, check_out]
        if exclude_reservation_id is not None:
            q += ' AND r.id != ?'
            params.append(exclude_reservation_id)
        return conn.execute(q, params).fetchone()[0] == 0

    def room_is_available(self, room_id, check_in, check_out, exclude_reservation_id=None):
        self._validate_stay(check_in, check_out)
        with closing(self.connect()) as conn:
            return self._room_available_on_connection(conn, room_id, check_in, check_out, exclude_reservation_id)

    def available_rooms_for_dates(self, check_in, check_out, room_type_filter=''):
        q = "SELECT * FROM rooms WHERE status NOT IN ('Maintenance', 'Cleaning')"
        params = []
        if room_type_filter:
            q += ' AND room_type LIKE ?'
            params.append(f'%{room_type_filter}%')
        q += ' ORDER BY room_number COLLATE NOCASE'
        with closing(self.connect()) as conn:
            rooms = conn.execute(q, params).fetchall()
        return [room for room in rooms if self.room_is_available(room['id'], check_in, check_out)]

    def _reservation_room_total(self, room_items, check_in, check_out):
        self._validate_stay(check_in, check_out)
        nights = (parse_date(check_out) - parse_date(check_in)).days
        return float(sum((self.money(item['room_price']) * nights for item in room_items), Decimal('0.00')))

    def _validate_booking_in_transaction(self, conn, room_items, check_in, check_out,
                                         adults, children, exclude_reservation_id=None):
        self._validate_stay(check_in, check_out)
        if not room_items:
            raise ValueError('Add at least one room to the reservation.')
        if int(adults) < 1 or int(children) < 0:
            raise ValueError('A booking needs at least one adult and no negative guest count.')
        room_ids = [int(item['room_id']) for item in room_items]
        if len(set(room_ids)) != len(room_ids):
            raise ValueError('A room can only be selected once per reservation.')
        capacity = 0
        for item in room_items:
            self.money(item['room_price'])
            room = conn.execute('SELECT * FROM rooms WHERE id=?', (item['room_id'],)).fetchone()
            if room is None:
                raise ValueError('One of the selected rooms does not exist.')
            if room['status'] in ('Maintenance', 'Cleaning'):
                raise ValueError(f"Room {room['room_number']} cannot currently be booked.")
            capacity += int(room['capacity'])
            if not self._room_available_on_connection(conn, item['room_id'], check_in, check_out,
                                                       exclude_reservation_id):
                raise ValueError(f"Room {room['room_number']} is not available for the selected dates.")
        if int(adults) + int(children) > capacity:
            raise ValueError(f'Selected rooms total capacity is {capacity}, but you entered {adults + children} guests.')
        return self._reservation_room_total(room_items, check_in, check_out)

    def fetch_reservation_rooms(self, reservation_id):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT rr.id, rr.reservation_id, rr.room_id, rr.room_price, rr.room_notes,
                       rm.room_number, rm.room_type, rm.capacity
                FROM reservation_rooms rr
                JOIN rooms rm ON rr.room_id = rm.id
                WHERE rr.reservation_id=?
                ORDER BY rm.room_number COLLATE NOCASE
            """, (reservation_id,)).fetchall()

    def add_reservation(self, guest_id, check_in, check_out, adults, children, status='Reserved', notes='', room_items=None):
        room_items = room_items or []
        if status not in ('Reserved', 'Checked In', 'Checked Out', 'Cancelled'):
            raise ValueError('Invalid reservation status.')
        with closing(self.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                total = self._validate_booking_in_transaction(conn, room_items, check_in, check_out, adults, children)
                cur = conn.execute("""
                    INSERT INTO reservations (guest_id, room_id, check_in, check_out, adults, children, total_price, status, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (guest_id, room_items[0]['room_id'], check_in, check_out, adults, children,
                      total, status, notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                reservation_id = cur.lastrowid
                for item in room_items:
                    conn.execute("""
                        INSERT INTO reservation_rooms (reservation_id, room_id, room_price, room_notes)
                        VALUES (?, ?, ?, ?)
                    """, (reservation_id, item['room_id'], float(self.money(item['room_price'])),
                          item.get('room_notes', '')))
                for item in room_items:
                    self.refresh_room_status(item['room_id'], conn)
                conn.commit()
                return reservation_id
            except Exception:
                conn.rollback()
                raise

    def update_reservation(self, reservation_id, guest_id, check_in, check_out, adults, children,
                           status='Reserved', notes='', room_items=None):
        room_items = room_items or []
        if status not in ('Reserved', 'Checked In', 'Checked Out', 'Cancelled'):
            raise ValueError('Invalid reservation status.')
        with closing(self.connect()) as conn:
            conn.execute('BEGIN IMMEDIATE')
            try:
                old = conn.execute('SELECT id FROM reservations WHERE id=?', (reservation_id,)).fetchone()
                if old is None:
                    raise ValueError('Reservation not found.')
                old_room_ids = [r['room_id'] for r in conn.execute(
                    'SELECT room_id FROM reservation_rooms WHERE reservation_id=?', (reservation_id,))]
                total = self._validate_booking_in_transaction(conn, room_items, check_in, check_out,
                                                               adults, children, reservation_id)
                conn.execute("""
                    UPDATE reservations
                    SET guest_id=?, room_id=?, check_in=?, check_out=?, adults=?, children=?, total_price=?, status=?, notes=?
                    WHERE id=?
                """, (guest_id, room_items[0]['room_id'], check_in, check_out, adults, children,
                      total, status, notes, reservation_id))
                conn.execute('DELETE FROM reservation_rooms WHERE reservation_id=?', (reservation_id,))
                for item in room_items:
                    conn.execute("""
                        INSERT INTO reservation_rooms (reservation_id, room_id, room_price, room_notes)
                        VALUES (?, ?, ?, ?)
                    """, (reservation_id, item['room_id'], float(self.money(item['room_price'])),
                          item.get('room_notes', '')))
                for room_id in set(old_room_ids + [item['room_id'] for item in room_items]):
                    self.refresh_room_status(room_id, conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def cancel_reservation(self, reservation_id):
        room_ids = [r['room_id'] for r in self.fetch_reservation_rooms(reservation_id)]
        with closing(self.connect()) as conn, conn:
            conn.execute("UPDATE reservations SET status='Cancelled' WHERE id=?", (reservation_id,))
            for room_id in room_ids:
                self.refresh_room_status(room_id, conn)

    def check_in_reservation(self, reservation_id):
        room_ids = [r['room_id'] for r in self.fetch_reservation_rooms(reservation_id)]
        with closing(self.connect()) as conn, conn:
            conn.execute("UPDATE reservations SET status='Checked In' WHERE id=?", (reservation_id,))
            for room_id in room_ids:
                conn.execute("UPDATE rooms SET status='Occupied' WHERE id=?", (room_id,))

    def check_out_reservation(self, reservation_id):
        room_ids = [r['room_id'] for r in self.fetch_reservation_rooms(reservation_id)]
        with closing(self.connect()) as conn, conn:
            conn.execute("UPDATE reservations SET status='Checked Out' WHERE id=?", (reservation_id,))
            for room_id in room_ids:
                conn.execute("UPDATE rooms SET status='Cleaning' WHERE id=?", (room_id,))

    def set_reservation_status(self, reservation_id, status):
        room_ids = [r['room_id'] for r in self.fetch_reservation_rooms(reservation_id)]
        with closing(self.connect()) as conn, conn:
            conn.execute('UPDATE reservations SET status=? WHERE id=?', (status, reservation_id))
            for room_id in room_ids:
                self.refresh_room_status(room_id, conn)

    def fetch_reservations(self, search_text='', status_filter='', date_from='', date_to=''):
        q = """
            SELECT
                r.id,
                r.guest_id,
                r.check_in,
                r.check_out,
                r.adults,
                r.children,
                r.total_price,
                r.status,
                r.notes,
                r.created_at,
                g.full_name,
                COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number,
                CASE
                    WHEN COUNT(rr.room_id) <= 1 THEN COALESCE(MAX(rm.room_type), '')
                    ELSE 'Multiple'
                END AS room_type,
                COUNT(rr.room_id) AS room_count
            FROM reservations r
            JOIN guests g ON r.guest_id = g.id
            LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
            LEFT JOIN rooms rm ON rr.room_id = rm.id
            WHERE 1=1
        """
        params = []

        if search_text:
            q += " AND (g.full_name LIKE ? OR rm.room_number LIKE ? OR r.check_in LIKE ? OR r.check_out LIKE ?)"
            pat = f"%{search_text}%"
            params.extend([pat, pat, pat, pat])

        if status_filter:
            q += " AND r.status=?"
            params.append(status_filter)

        if date_from:
            q += " AND r.check_in >= ?"
            params.append(date_from)

        if date_to:
            q += " AND r.check_in <= ?"
            params.append(date_to)

        q += """
            GROUP BY r.id
            ORDER BY r.check_in DESC, r.id DESC
        """

        with closing(self.connect()) as conn:
            return conn.execute(q, params).fetchall()

    def get_reservation(self, reservation_id):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT r.*, g.full_name, g.phone, g.email, g.id_number, g.nationality, g.address,
                       COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number,
                       CASE WHEN COUNT(rr.room_id) <= 1 THEN COALESCE(MAX(rm.room_type), '') ELSE 'Multiple' END AS room_type,
                       COUNT(rr.room_id) AS room_count
                FROM reservations r
                JOIN guests g ON r.guest_id = g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.id=?
                GROUP BY r.id
            """, (reservation_id,)).fetchone()

    def reservation_paid_total(self, reservation_id):
        with closing(self.connect()) as conn:
            return float(conn.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE reservation_id=?', (reservation_id,)).fetchone()[0] or 0)

    def reservation_services_total(self, reservation_id):
        with closing(self.connect()) as conn:
            return float(conn.execute('SELECT COALESCE(SUM(amount),0) FROM services WHERE reservation_id=?', (reservation_id,)).fetchone()[0] or 0)

    def reservation_balance(self, reservation_id):
        res = self.get_reservation(reservation_id)
        if not res:
            return 0.0
        grand = self.money(res['total_price']) + self.money(self.reservation_services_total(reservation_id))
        paid = self.money(self.reservation_paid_total(reservation_id))
        return float((grand - paid).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def refresh_room_status(self, room_id, conn=None):
        own = False
        if conn is None:
            conn = self.connect()
            own = True
        try:
            room = conn.execute('SELECT status FROM rooms WHERE id=?', (room_id,)).fetchone()
            if room and room['status'] == 'Cleaning':
                if own:
                    conn.commit()
                return
            checked_in = conn.execute("""
                SELECT COUNT(*)
                FROM reservation_rooms rr
                JOIN reservations r ON rr.reservation_id = r.id
                WHERE rr.room_id=? AND r.status='Checked In'
            """, (room_id,)).fetchone()[0]
            reserved = conn.execute("""
                SELECT COUNT(*)
                FROM reservation_rooms rr
                JOIN reservations r ON rr.reservation_id = r.id
                WHERE rr.room_id=? AND r.status='Reserved'
            """, (room_id,)).fetchone()[0]
            if checked_in:
                status = 'Occupied'
            elif reserved:
                status = 'Reserved'
            else:
                status = 'Available' if not room or room['status'] not in ('Cleaning', 'Maintenance') else room['status']
            conn.execute('UPDATE rooms SET status=? WHERE id=?', (status, room_id))
            if own:
                conn.commit()
        finally:
            if own:
                conn.close()

    # payments and services
    def add_payment(self, reservation_id, amount, method, note):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                INSERT INTO payments (reservation_id, amount, method, paid_at, note)
                VALUES (?, ?, ?, ?, ?)
            """, (reservation_id, float(self.money(amount, allow_zero=False)), method,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'), note))

    def fetch_payments(self, reservation_id):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT * FROM payments WHERE reservation_id=? ORDER BY id DESC', (reservation_id,)).fetchall()

    def add_service(self, reservation_id, service_name, amount):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                INSERT INTO services (reservation_id, service_name, amount, created_at)
                VALUES (?, ?, ?, ?)
            """, (reservation_id, service_name, float(self.money(amount, allow_zero=False)),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    def fetch_services(self, reservation_id):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT * FROM services WHERE reservation_id=? ORDER BY id DESC', (reservation_id,)).fetchall()

    # dashboard/reports
    def get_dashboard_stats(self):
        with closing(self.connect()) as conn:
            def c(q):
                return conn.execute(q).fetchone()[0]
            return {
                'total_rooms': c('SELECT COUNT(*) FROM rooms'),
                'available_rooms': c("SELECT COUNT(*) FROM rooms WHERE status='Available'"),
                'occupied_rooms': c("SELECT COUNT(*) FROM rooms WHERE status='Occupied'"),
                'reserved_rooms': c("SELECT COUNT(*) FROM rooms WHERE status='Reserved'"),
                'cleaning_rooms': c("SELECT COUNT(*) FROM rooms WHERE status='Cleaning'"),
                'maintenance_rooms': c("SELECT COUNT(*) FROM rooms WHERE status='Maintenance'"),
                'total_guests': c('SELECT COUNT(*) FROM guests'),
                'total_reservations': c('SELECT COUNT(*) FROM reservations'),
                'paid_revenue': round(float(c('SELECT COALESCE(SUM(amount),0) FROM payments') or 0), 2),
                'cancelled': c("SELECT COUNT(*) FROM reservations WHERE status='Cancelled'"),
            }

    def fetch_today_checkins(self, today):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT r.id, g.full_name, COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.check_in=? AND r.status='Reserved'
                GROUP BY r.id
                ORDER BY room_number
            """, (today,)).fetchall()

    def fetch_due_today_checkouts(self, today):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT r.id, g.full_name, COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.check_out=? AND r.status='Checked In'
                GROUP BY r.id
                ORDER BY room_number
            """, (today,)).fetchall()

    def fetch_completed_today_checkouts(self, today):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT r.id, g.full_name, COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.check_out=? AND r.status='Checked Out'
                GROUP BY r.id
                ORDER BY room_number
            """, (today,)).fetchall()


    def fetch_cleaning_rooms(self):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT *
                FROM rooms
                WHERE status='Cleaning'
                ORDER BY room_number COLLATE NOCASE
            """).fetchall()

    def fetch_tomorrow_arrivals(self, tomorrow):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT r.id, g.full_name, COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.check_in=? AND r.status='Reserved'
                GROUP BY r.id
                ORDER BY room_number
            """, (tomorrow,)).fetchall()

    def fetch_unpaid_reservations(self):
        with closing(self.connect()) as conn:
            rows = conn.execute("""
                SELECT r.id, g.full_name, COALESCE(GROUP_CONCAT(rm.room_number, ', '), '') AS room_number, r.total_price
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                LEFT JOIN reservation_rooms rr ON rr.reservation_id = r.id
                LEFT JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.status IN ('Reserved', 'Checked In')
                GROUP BY r.id
                ORDER BY r.check_in ASC, r.id ASC
            """).fetchall()
        unpaid=[]
        for row in rows:
            bal=self.reservation_balance(row['id'])
            if bal>0:
                unpaid.append((row, bal))
        return unpaid
    def occupancy_for_range(self, start_date, days=7, room_type_filter=''):
        start = parse_date(start_date)
        end = start + timedelta(days=days)
        with closing(self.connect()) as conn:
            q = 'SELECT * FROM rooms'
            params = []
            if room_type_filter:
                q += ' WHERE room_type LIKE ?'
                params.append(f'%{room_type_filter}%')
            q += ' ORDER BY room_number COLLATE NOCASE'
            rooms = conn.execute(q, params).fetchall()
            reservations = conn.execute("""
                SELECT r.*, g.full_name, rm.room_number
                FROM reservations r
                JOIN guests g ON r.guest_id=g.id
                JOIN reservation_rooms rr ON rr.reservation_id = r.id
                JOIN rooms rm ON rr.room_id = rm.id
                WHERE r.status IN ('Reserved', 'Checked In')
                  AND NOT (r.check_out <= ? OR r.check_in >= ?)
                ORDER BY rm.room_number
            """, (start.strftime(DATE_FMT), end.strftime(DATE_FMT))).fetchall()
        return rooms, reservations

    def daily_income(self):
        with closing(self.connect()) as conn:
            return conn.execute("""
                SELECT substr(paid_at,1,10) AS day, COALESCE(SUM(amount),0) AS total
                FROM payments GROUP BY substr(paid_at,1,10) ORDER BY day DESC LIMIT 30
            """).fetchall()

    # exports

    def get_setting(self, key, default=''):
        with closing(self.connect()) as conn:
            row = conn.execute('SELECT value FROM app_settings WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default

    def get_settings(self):
        with closing(self.connect()) as conn:
            rows = conn.execute('SELECT key, value FROM app_settings').fetchall()
            return {row['key']: row['value'] for row in rows}

    def set_settings(self, settings_dict):
        with closing(self.connect()) as conn, conn:
            for key, value in settings_dict.items():
                conn.execute(
                    'INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    (key, str(value))
                )

    def change_user_password(self, username, old_password, new_password):
        if not new_password:
            raise ValueError('New password cannot be empty.')
        with closing(self.connect()) as conn, conn:
            row = conn.execute('SELECT id, password FROM users WHERE username=?', (username,)).fetchone()
            if not row or not self.verify_password(old_password, row['password']):
                raise ValueError('Current password is incorrect.')
            encoded = self.hash_password(new_password)
            conn.execute('UPDATE users SET password=? WHERE username=?', (encoded, username))
        self.log_action('change_password', 'Changed own password', username)

    def export_reservations_csv(self, filepath):
        rows = self.fetch_reservations()
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Guest', 'Room', 'Type', 'Check In', 'Check Out', 'Adults', 'Children', 'Total', 'Status'])
            for r in rows:
                writer.writerow([r['id'], r['full_name'], r['room_number'], r['room_type'], r['check_in'], r['check_out'], r['adults'], r['children'], r['total_price'], r['status']])

    def export_excel_report(self, filepath):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Reservations'
        ws.append(['ID', 'Guest', 'Room', 'Type', 'Check In', 'Check Out', 'Adults', 'Children', 'Total', 'Status', 'Balance'])
        for r in self.fetch_reservations():
            ws.append([r['id'], r['full_name'], r['room_number'], r['room_type'], r['check_in'], r['check_out'], r['adults'], r['children'], float(r['total_price']), r['status'], self.reservation_balance(r['id'])])
        ws2 = wb.create_sheet('Income')
        ws2.append(['Day', 'Income'])
        for row in self.daily_income():
            ws2.append([row['day'], float(row['total'])])
        wb.save(filepath)

    def export_invoice_pdf(self, reservation_id, filepath, hotel_name=None, hotel_address='', hotel_phone='', hotel_email='', hotel_logo_path='', invoice_footer=''):
        res = self.get_reservation(reservation_id)
        room_rows = self.fetch_reservation_rooms(reservation_id)
        services = self.fetch_services(reservation_id)
        payments = self.fetch_payments(reservation_id)
        services_total = self.reservation_services_total(reservation_id)
        paid_total = self.reservation_paid_total(reservation_id)
        balance = self.reservation_balance(reservation_id)

        if hotel_name is None:
            hotel_name = self.get_setting('hotel_name', 'Hotel Reservation System')
        hotel_address = hotel_address or self.get_setting('hotel_address', '')
        hotel_phone = hotel_phone or self.get_setting('hotel_phone', '')
        hotel_email = hotel_email or self.get_setting('hotel_email', '')
        hotel_logo_path = hotel_logo_path or self.get_setting('hotel_logo_path', '')
        invoice_footer = invoice_footer or self.get_setting('invoice_footer', '')

        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        y = height - 50

        has_logo = hotel_logo_path and os.path.exists(hotel_logo_path)
        if has_logo:
            try:
                c.drawImage(hotel_logo_path, 40, y - 35, width=60, height=35, preserveAspectRatio=True, mask='auto')
            except Exception:
                has_logo = False

        title_x = 110 if has_logo else 40
        c.setFont('Helvetica-Bold', 18)
        c.drawString(title_x, y, hotel_name)
        y -= 20
        c.setFont('Helvetica', 10)
        for header_line in [hotel_address, hotel_phone, hotel_email]:
            if header_line:
                c.drawString(40, y, header_line)
                y -= 14
        y -= 8

        c.setFont('Helvetica-Bold', 14)
        c.drawString(40, y, 'Invoice')
        y -= 24
        c.setFont('Helvetica', 10)
        header_lines = [
            f'Invoice Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'Reservation ID: {res["id"]}',
            f'Guest: {res["full_name"]}',
            f'Phone: {res["phone"] or ""}',
            f'Email: {res["email"] or ""}',
            f'Stay: {res["check_in"]} to {res["check_out"]}',
            f'Adults: {res["adults"]}   Children: {res["children"]}',
        ]
        for line in header_lines:
            c.drawString(40, y, line)
            y -= 16

        y -= 6
        c.setFont('Helvetica-Bold', 11)
        c.drawString(40, y, 'Rooms')
        y -= 18
        c.setFont('Helvetica', 10)
        nights = max(1, (parse_date(res['check_out']) - parse_date(res['check_in'])).days)
        for rr in room_rows:
            line = f"- Room {rr['room_number']} ({rr['room_type']}) | ${float(rr['room_price']):.2f}/night x {nights} night(s)"
            c.drawString(50, y, line)
            y -= 14
            if rr['room_notes']:
                c.drawString(65, y, f"Note: {rr['room_notes']}")
                y -= 14

        y -= 6
        c.setFont('Helvetica-Bold', 11)
        c.drawString(40, y, f'Base Room Total: ${float(res["total_price"]):.2f}')
        y -= 18

        c.setFont('Helvetica-Bold', 11)
        c.drawString(40, y, 'Extras')
        y -= 16
        c.setFont('Helvetica', 10)
        if services:
            for s in services:
                c.drawString(50, y, f'- {s["service_name"]}: ${float(s["amount"]):.2f}')
                y -= 14
        else:
            c.drawString(50, y, '- None')
            y -= 14

        y -= 8
        c.setFont('Helvetica-Bold', 11)
        c.drawString(40, y, 'Payments')
        y -= 16
        c.setFont('Helvetica', 10)
        if payments:
            for p in payments:
                c.drawString(50, y, f'- {p["paid_at"]} | {p["method"]} | ${float(p["amount"]):.2f}')
                y -= 14
        else:
            c.drawString(50, y, '- None')
            y -= 14

        y -= 10
        grand = float(res['total_price']) + services_total
        c.setFont('Helvetica-Bold', 11)
        for line in [
            f'Extras Total: ${services_total:.2f}',
            f'Paid Total: ${paid_total:.2f}',
            f'Grand Total: ${grand:.2f}',
            f'Balance Due: ${balance:.2f}',
        ]:
            c.drawString(40, y, line)
            y -= 16
        if invoice_footer:
            y -= 12
            c.setFont('Helvetica-Oblique', 10)
            c.drawString(40, max(40, y), invoice_footer)
        c.save()
