from __future__ import annotations

from src.models.note import Note
from src.models.tag import Tag
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

    def on_set_archived(self, note_id: int, archived: bool) -> None:
        self._note_service.set_archived(note_id, archived)

    def on_update_note_appearance(
        self, note_id: int, *, color: str | None = None, emoji_icon: str | None = None
    ) -> None:
        self._note_service.update_note_appearance(
            note_id, color=color, emoji_icon=emoji_icon
        )

    def on_search(
        self, keyword: str, *, archived: bool = False, tag_ids: list[int] | None = None
    ) -> list[Note]:
        return self._search_service.search_notes(
            keyword, archived=archived, tag_ids=tag_ids
        )

    def list_notes(self, archived: bool = False, tag_ids: list[int] | None = None) -> list[Note]:
        return self._note_service.list_notes(archived=archived, tag_ids=tag_ids)

    def list_tags(self) -> list[Tag]:
        return self._note_service.list_tags()

    def on_create_tag(self, name: str, color: str = "#4A90E2") -> Tag | None:
        return self._note_service.create_tag(name=name, color=color)

    def on_delete_tag(self, tag_id: int) -> None:
        self._note_service.delete_tag(tag_id)

    def get_note_tag_ids(self, note_id: int) -> list[int]:
        return self._note_service.get_note_tag_ids(note_id)

    def on_set_note_tags(self, note_id: int, tag_ids: list[int]) -> None:
        self._note_service.set_note_tags(note_id, tag_ids)

