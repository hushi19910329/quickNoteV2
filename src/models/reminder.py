from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Reminder:
    id: int
    note_id: int
    remind_at: str
    repeat_rule: str | None = None
    is_enabled: int = 1
    last_triggered_at: str | None = None

