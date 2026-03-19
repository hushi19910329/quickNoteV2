from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReminderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_note_reminder(self, note_id: int, remind_at: str, repeat_rule: str | None) -> int:
        now = _now_iso()
        existing = self.get_reminder_by_note(note_id)
        if existing is None:
            cur = self._conn.execute(
                """
                INSERT INTO reminders(note_id, remind_at, repeat_rule, is_enabled, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (note_id, remind_at, repeat_rule, now, now),
            )
            self._conn.commit()
            return int(cur.lastrowid)
        self._conn.execute(
            """
            UPDATE reminders
            SET remind_at = ?, repeat_rule = ?, is_enabled = 1, updated_at = ?
            WHERE id = ?
            """,
            (remind_at, repeat_rule, now, int(existing["id"])),
        )
        self._conn.commit()
        return int(existing["id"])

    def get_reminder_by_note(self, note_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM reminders WHERE note_id = ? ORDER BY id DESC LIMIT 1",
            (note_id,),
        ).fetchone()

    def get_reminder(self, reminder_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM reminders WHERE id = ?",
            (reminder_id,),
        ).fetchone()

    def list_active_reminders(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM reminders WHERE is_enabled = 1 ORDER BY remind_at ASC"
        ).fetchall()

    def disable_reminder(self, reminder_id: int) -> None:
        self._conn.execute(
            "UPDATE reminders SET is_enabled = 0, updated_at = ? WHERE id = ?",
            (_now_iso(), reminder_id),
        )
        self._conn.commit()

    def disable_reminder_by_note(self, note_id: int) -> None:
        self._conn.execute(
            "UPDATE reminders SET is_enabled = 0, updated_at = ? WHERE note_id = ?",
            (_now_iso(), note_id),
        )
        self._conn.commit()

    def update_remind_at(self, reminder_id: int, remind_at: str, enabled: bool = True) -> None:
        self._conn.execute(
            "UPDATE reminders SET remind_at = ?, is_enabled = ?, updated_at = ? WHERE id = ?",
            (remind_at, 1 if enabled else 0, _now_iso(), reminder_id),
        )
        self._conn.commit()

    def mark_triggered(self, reminder_id: int, triggered_at: str) -> None:
        self._conn.execute(
            "UPDATE reminders SET last_triggered_at = ?, updated_at = ? WHERE id = ?",
            (triggered_at, _now_iso(), reminder_id),
        )
        self._conn.commit()

