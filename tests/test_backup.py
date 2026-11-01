import tempfile
import sqlite3
import unittest
from pathlib import Path
from database import DatabaseManager

class BackupTests(unittest.TestCase):
    def test_consistent_backup_restore(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            db = DatabaseManager(str(folder / 'test.db'))
            db.setup_admin('admin', 'a-long-local-password')
            db.add_guest('Synthetic Guest', '', '', '', '', '', '')
            path = db.backup_database(str(folder / 'backups'))
            with sqlite3.connect(path) as backed:
                self.assertEqual(backed.execute('SELECT COUNT(*) FROM guests').fetchone()[0], 1)
            db.add_guest('Temporary Guest', '', '', '', '', '', '')
            db.restore_database(path)
            self.assertEqual(len(db.fetch_guests()), 1)
            self.assertIsNotNone(db.validate_login('admin', 'a-long-local-password'))
