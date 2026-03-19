from __future__ import annotations

from datetime import datetime
from typing import Callable

from src.services.reminder_service import ReminderService


class ReminderController:
    def __init__(self, reminder_service: ReminderService) -> None:
        self._reminder_service = reminder_service

    def initialize(self) -> None:
        self._reminder_service.load_and_schedule_all()

    def shutdown(self) -> None:
        self._reminder_service.shutdown()

    def set_notify_callback(self, callback: Callable[[str], None]) -> None:
        self._reminder_service.set_notify_callback(callback)

    def on_set_reminder(
        self, note_id: int, remind_at: datetime, repeat_rule: str | None = None
    ) -> int:
        return self._reminder_service.set_reminder(note_id, remind_at, repeat_rule)

    def on_clear_reminder(self, note_id: int) -> None:
        self._reminder_service.clear_reminder(note_id)

    def on_snooze(self, note_id: int, minutes: int) -> bool:
        return self._reminder_service.snooze_note(note_id, minutes)

    def get_note_reminder(self, note_id: int):
        return self._reminder_service.get_note_reminder(note_id)

