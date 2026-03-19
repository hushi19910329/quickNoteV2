from __future__ import annotations

from src.models.note import Note
from src.services.note_service import NoteService
from src.services.search_service import SearchService


class NoteController:
    def __init__(self, note_service: NoteService, search_service: SearchService) -> None:
        self._note_service = note_service
        self._search_service = search_service

    def on_create_note(self) -> Note:
        return self._note_service.create_quick_note()

    def on_select_note(self, note_id: int) -> Note | None:
        return self._note_service.get_note(note_id)

    def on_note_content_changed(self, note_id: int, html: str, plain_text: str) -> None:
        self._note_service.save_note_content(note_id, html, plain_text)

    def on_note_title_changed(self, note_id: int, title: str) -> None:
        self._note_service.update_note_title(note_id, title)

    def on_delete_note(self, note_id: int) -> None:
        self._note_service.soft_delete(note_id)

    def on_search(self, keyword: str) -> list[Note]:
        return self._search_service.search_notes(keyword)

    def list_notes(self) -> list[Note]:
        return self._note_service.list_notes()
