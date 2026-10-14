import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_settings_persist_and_are_isolated_by_user(self):
        self.db.save_settings(123, "가학교", "초등학교", "B10", "12345", 4, 2)
        self.db.save_settings(456, "나학교", "중학교", "B10", "67890", 2, 1)

        first = self.db.get_settings(123)
        second = self.db.get_settings(456)
        self.assertEqual(first["school_name"], "가학교")
        self.assertEqual((first["grade"], first["class_num"]), (4, 2))
        self.assertEqual(second["school_name"], "나학교")
        self.assertEqual((second["grade"], second["class_num"]), (2, 1))
        self.assertIsNone(self.db.get_settings(999))

        self.db.save_settings(123, "다학교", "고등학교", "B10", "11111", 3, 5)
        self.assertEqual(self.db.get_settings(123)["school_name"], "다학교")
        self.assertEqual(self.db.get_settings(456)["school_name"], "나학교")
        self.db.close()
        self.db.initialize()
        self.assertEqual(
            self.db.get_settings(123)["school_name"],
            "다학교",
        )

    def test_legacy_guild_settings_are_preserved(self):
        self.db.close()
        connection = sqlite3.connect(self.db.path)
        connection.execute(
            """
            CREATE TABLE guild_settings (
                guild_id TEXT PRIMARY KEY,
                school_name TEXT NOT NULL,
                school_type TEXT NOT NULL,
                office_code TEXT NOT NULL,
                school_code TEXT NOT NULL,
                grade INTEGER,
                class_num INTEGER
            )
            """
        )
        connection.execute(
            "INSERT INTO guild_settings VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("99", "기존학교", "중학교", "B10", "99999", 2, 3),
        )
        connection.commit()
        connection.close()

        self.db.initialize()
        legacy = self.db._db().execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", ("99",)
        ).fetchone()
        self.assertEqual(legacy["school_name"], "기존학교")
        self.assertEqual((legacy["grade"], legacy["class_num"]), (2, 3))
        self.assertIsNone(self.db.get_settings(99))


if __name__ == "__main__":
    unittest.main()
