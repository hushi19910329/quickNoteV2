from __future__ import annotations

from src.models.note import Note
from src.services.note_service import NoteService


class SearchService:
    def __init__(self, note_service: NoteService) -> None:
        self._note_service = note_service

    def search_notes(self, keyword: str) -> list[Note]:
        keyword_lower = keyword.strip().lower()
        if not keyword_lower:
            return self._note_service.list_notes()
        return [
            n
            for n in self._note_service.list_notes()
            if keyword_lower in n.title.lower() or keyword_lower in n.plain_text.lower()
        ]

