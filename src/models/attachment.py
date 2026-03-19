from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Attachment:
    id: int
    note_id: int
    file_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    created_at: str = ""

