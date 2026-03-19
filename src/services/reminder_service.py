from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from plyer import notification

from src.db.repositories.note_repo import NoteRepository
from src.db.repositories.reminder_repo import ReminderRepository


class ReminderService:
    def __init__(self, reminder_repo: ReminderRepository, note_repo: NoteRepository) -> None:
        self._reminder_repo = reminder_repo
        self._note_repo = note_repo
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._notify_callback: Callable[[str], None] | None = None

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def set_notify_callback(self, callback: Callable[[str], None]) -> None:
        self._notify_callback = callback

    def load_and_schedule_all(self) -> None:
        for row in self._reminder_repo.list_active_reminders():
            self._schedule_row(row)

    def set_reminder(self, note_id: int, remind_at: datetime, repeat_rule: str | None) -> int:
        reminder_id = self._reminder_repo.upsert_note_reminder(
            note_id=note_id,
            remind_at=remind_at.isoformat(),
            repeat_rule=repeat_rule,
        )
        row = self._reminder_repo.get_reminder(reminder_id)
        if row is not None:
            self._schedule_row(row)
        return reminder_id

    def clear_reminder(self, note_id: int) -> None:
        row = self._reminder_repo.get_reminder_by_note(note_id)
        self._reminder_repo.disable_reminder_by_note(note_id)
        if row is not None:
            self._remove_job(int(row["id"]))

    def get_note_reminder(self, note_id: int):
        return self._reminder_repo.get_reminder_by_note(note_id)

    def snooze_note(self, note_id: int, minutes: int) -> bool:
        row = self._reminder_repo.get_reminder_by_note(note_id)
        if row is None:
            return False
        reminder_id = int(row["id"])
        new_time = datetime.now().astimezone() + timedelta(minutes=minutes)
        self._reminder_repo.update_remind_at(reminder_id, new_time.isoformat(), enabled=True)
        updated = self._reminder_repo.get_reminder(reminder_id)
        if updated is not None:
            self._schedule_row(updated)
        return True

    def _schedule_row(self, row) -> None:
        if int(row["is_enabled"]) != 1:
            return
        run_at = datetime.fromisoformat(str(row["remind_at"]))
        job_id = self._job_id(int(row["id"]))
        self._remove_job(int(row["id"]))
        self._scheduler.add_job(
            self._handle_trigger,
            trigger=DateTrigger(run_date=run_at),
            args=[int(row["id"])],
            id=job_id,
            replace_existing=True,
        )

    def _remove_job(self, reminder_id: int) -> None:
        job_id = self._job_id(reminder_id)
        job = self._scheduler.get_job(job_id)
        if job is not None:
            self._scheduler.remove_job(job_id)

    def _handle_trigger(self, reminder_id: int) -> None:
        row = self._reminder_repo.get_reminder(reminder_id)
        if row is None or int(row["is_enabled"]) != 1:
            return
        note_id = int(row["note_id"])
        note = self._note_repo.get_note(note_id)
        title = note.title.strip() if note else f"Note #{note_id}"
        content = (note.plain_text.strip()[:120] if note else "") or "Reminder reached."
        self._notify(title=title or "QuickNote Reminder", message=content)
        self._reminder_repo.mark_triggered(reminder_id, datetime.now().astimezone().isoformat())

        repeat_rule = row["repeat_rule"]
        if repeat_rule == "daily":
            next_time = datetime.fromisoformat(str(row["remind_at"])) + timedelta(days=1)
            self._reminder_repo.update_remind_at(reminder_id, next_time.isoformat(), enabled=True)
            updated = self._reminder_repo.get_reminder(reminder_id)
            if updated is not None:
                self._schedule_row(updated)
        else:
            self._reminder_repo.disable_reminder(reminder_id)
            self._remove_job(reminder_id)

    def _notify(self, title: str, message: str) -> None:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="QuickNote V2",
                timeout=8,
            )
        except Exception:
            pass
        if self._notify_callback is not None:
            self._notify_callback(f"提醒触发: {title}")

    @staticmethod
    def _job_id(reminder_id: int) -> str:
        return f"reminder:{reminder_id}"

