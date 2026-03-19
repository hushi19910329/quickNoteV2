from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Note:
    id: int
    title: str
    content_html: str
    plain_text: str
    color: str = "yellow"
    emoji_icon: str = "📝"
    is_pinned: int = 0
    is_archived: int = 0
    is_deleted: int = 0
    created_at: str = ""
    updated_at: str = ""

