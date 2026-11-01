"""Integration tests use temporary, synthetic SQLite databases only."""
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from database import DatabaseManager


class DatabaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = DatabaseManager(str(Path(self.folder.name) / 'test.db'))
        self.db.setup_admin('review_admin', 'this-is-a-demo-only-password')
        self.guest = self.db.add_guest('Test Guest', '', '', '', '', '', '')
        self.db.add_room('101', 'Standard', 3, 50, 1, False, False, False)
        self.db.add_room('102', 'Standard', 3, 70, 1, False, False, False)
        self.rooms = [r['id'] for r in self.db.fetch_rooms()]

    def items(self, room, price='50.00'):
        return [{'room_id': room, 'room_price': price, 'room_notes': ''}]

    def booking(self, room, cin='2027-07-01', cout='2027-07-03', **kwargs):
        return self.db.add_reservation(self.guest, cin, cout, 1, 0,
                                       room_items=self.items(room), **kwargs)

    def test_credentials_hash_first_run_no_default_users(self):
        with self.db.connect() as conn:
            rows = conn.execute('SELECT username, password FROM users').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['username'], 'review_admin')
        self.assertNotIn('this-is-a-demo-only-password', rows[0]['password'])
        self.assertTrue(rows[0]['password'].startswith('pbkdf2_sha256$'))
        self.assertIsNotNone(self.db.validate_login('review_admin', 'this-is-a-demo-only-password'))
        self.assertIsNone(self.db.validate_login('review_admin', 'wrong-password'))
        with self.assertRaises(ValueError):
            self.db.setup_admin('another_admin', 'another-safe-password')

    def test_password_reset_and_change(self):
        user_id = self.db.list_users()[0]['id']
        self.db.reset_user_password(user_id, 'a-new-strong-password')
        self.assertIsNotNone(self.db.validate_login('review_admin', 'a-new-strong-password'))
        self.db.change_user_password('review_admin', 'a-new-strong-password', 'yet-another-password')
        self.assertIsNone(self.db.validate_login('review_admin', 'a-new-strong-password'))
        self.assertIsNotNone(self.db.validate_login('review_admin', 'yet-another-password'))
        with self.assertRaises(ValueError):
            self.db.delete_user(user_id)

    def test_overlapping_and_adjacent_reservations(self):
        first = self.booking(self.rooms[0])
        self.assertGreater(first, 0)
        with self.assertRaises(ValueError):
            self.booking(self.rooms[0], '2027-07-02', '2027-07-04')
        second = self.booking(self.rooms[0], '2027-07-03', '2027-07-05')
        self.assertGreater(second, first)

    def test_duplicate_room_and_invalid_dates(self):
        with self.assertRaises(ValueError):
            self.db.add_reservation(self.guest, '2027-07-01', '2027-07-02', 1, 0,
                                    room_items=self.items(self.rooms[0]) * 2)
        with self.assertRaises(ValueError):
            self.booking(self.rooms[0], '2027-07-03', '2027-07-03')
        with self.assertRaises(ValueError):
            self.booking(self.rooms[0], '2027-07-03', '2027-07-01')

    def test_failed_update_is_rolled_back(self):
        first = self.booking(self.rooms[0])
        second = self.booking(self.rooms[1])
        with self.assertRaises(ValueError):
            self.db.update_reservation(second, self.guest, '2027-07-01', '2027-07-03',
                                       1, 0, room_items=self.items(self.rooms[0]))
        rows = self.db.fetch_reservation_rooms(second)
        self.assertEqual(rows[0]['room_id'], self.rooms[1])
        self.assertEqual(self.db.get_reservation(second)['status'], 'Reserved')

    def test_single_transaction_prevents_concurrent_double_booking(self):
        barrier = threading.Barrier(2)
        def race(_):
            barrier.wait()
            try:
                return self.booking(self.rooms[0])
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(race, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)

    def test_cancel_releases_room(self):
        rid = self.booking(self.rooms[0])
        self.db.cancel_reservation(rid)
        self.assertTrue(self.db.room_is_available(self.rooms[0], '2027-07-01', '2027-07-03'))
        self.booking(self.rooms[0])

    def test_money_validation_and_rounding(self):
        rid = self.db.add_reservation(self.guest, '2027-07-01', '2027-07-04', 1, 0,
                                      room_items=self.items(self.rooms[0], '0.335'))
        self.assertEqual(self.db.get_reservation(rid)['total_price'], 1.02)
        self.db.add_payment(rid, '0.335', 'Cash', '')
        self.assertEqual(self.db.reservation_paid_total(rid), 0.34)
        for bad in ('NaN', '-1', 'Infinity', '0'):
            with self.assertRaises(ValueError):
                self.db.add_payment(rid, bad, 'Cash', '')

    def test_prevent_guest_and_room_history_deletion(self):
        self.booking(self.rooms[0])
        with self.assertRaises(ValueError):
            self.db.delete_guest(self.guest)
        with self.assertRaises(ValueError):
            self.db.delete_room(self.rooms[0])


if __name__ == '__main__':
    unittest.main()
