from __future__ import annotations

import sqlite3

from src.db.repositories.note_repo import NoteRepository
from src.db.repositories.tag_repo import TagRepository
from src.models.note import Note
from src.models.tag import Tag


class NoteService:
    def __init__(self, note_repo: NoteRepository, tag_repo: TagRepository) -> None:
        self._note_repo = note_repo
        self._tag_repo = tag_repo

    def create_quick_note(self, title: str = "New note", color: str = "yellow") -> Note:
        note_id = self._note_repo.create_note(title=title, color=color)
        note = self._note_repo.get_note(note_id)
        if note is None:
            raise RuntimeError("Failed to create note.")
        return note

    def list_notes(self, archived: bool = False, tag_ids: list[int] | None = None) -> list[Note]:
        return self._note_repo.list_notes(archived=archived, tag_ids=tag_ids)

    def get_note(self, note_id: int) -> Note | None:
        return self._note_repo.get_note(note_id)

    def save_note_content(self, note_id: int, content_html: str, plain_text: str) -> None:
        self._note_repo.update_note_content(note_id, content_html, plain_text)

    def update_note_title(self, note_id: int, title: str) -> None:
        self._note_repo.update_note_meta(note_id, title=title)

    def update_note_appearance(
        self, note_id: int, *, color: str | None = None, emoji_icon: str | None = None
    ) -> None:
        self._note_repo.update_note_meta(note_id, color=color, emoji_icon=emoji_icon)

    def set_archived(self, note_id: int, archived: bool) -> None:
        self._note_repo.set_archived(note_id, archived)

    def soft_delete(self, note_id: int) -> None:
        self._note_repo.soft_delete_note(note_id)

    def list_tags(self) -> list[Tag]:
        return self._tag_repo.list_tags()

    def create_tag(self, name: str, color: str = "#4A90E2") -> Tag | None:
        name = name.strip()
        if not name:
            return None
        try:
            tag_id = self._tag_repo.create_tag(name=name, color=color)
        except sqlite3.IntegrityError:
            return None
        for tag in self._tag_repo.list_tags():
            if tag.id == tag_id:
                return tag
        return None

    def delete_tag(self, tag_id: int) -> None:
        self._tag_repo.delete_tag(tag_id)

    def get_note_tag_ids(self, note_id: int) -> list[int]:
        return self._tag_repo.get_note_tag_ids(note_id)

    def set_note_tags(self, note_id: int, tag_ids: list[int]) -> None:
        self._tag_repo.set_note_tags(note_id, tag_ids)

