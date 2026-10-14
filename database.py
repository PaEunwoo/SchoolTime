import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str | Path = "bot.db") -> None:
        self.path = str(path)
        self._connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                school_name TEXT NOT NULL,
                school_type TEXT NOT NULL,
                office_code TEXT NOT NULL,
                school_code TEXT NOT NULL,
                grade INTEGER NOT NULL,
                class_num INTEGER NOT NULL
            )
            """
        )
        self._connection.commit()

    def _db(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다.")
        return self._connection

    def save_settings(
        self,
        user_id: int,
        school_name: str,
        school_type: str,
        office_code: str,
        school_code: str,
        grade: int,
        class_num: int,
    ) -> None:
        self._db().execute(
            """
            INSERT INTO user_settings
                (user_id, school_name, school_type, office_code, school_code, grade, class_num)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                school_name = excluded.school_name,
                school_type = excluded.school_type,
                office_code = excluded.office_code,
                school_code = excluded.school_code,
                grade = excluded.grade,
                class_num = excluded.class_num
            """,
            (
                str(user_id),
                school_name,
                school_type,
                office_code,
                school_code,
                grade,
                class_num,
            ),
        )
        self._db().commit()

    def get_settings(self, user_id: int) -> dict[str, Any] | None:
        row = self._db().execute(
            "SELECT * FROM user_settings WHERE user_id = ?", (str(user_id),)
        ).fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
