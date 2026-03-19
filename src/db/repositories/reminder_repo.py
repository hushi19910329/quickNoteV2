from __future__ import annotations

import sqlite3


class ReminderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_active_reminders(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM reminders WHERE is_enabled = 1 ORDER BY remind_at ASC"
        ).fetchall()

