from __future__ import annotations

from src.db.repositories.note_repo import NoteRepository
from src.models.note import Note


class NoteService:
    def __init__(self, repo: NoteRepository) -> None:
        self._repo = repo

    def create_quick_note(self, title: str = "New note", color: str = "yellow") -> Note:
        note_id = self._repo.create_note(title=title, color=color)
        note = self._repo.get_note(note_id)
        if note is None:
            raise RuntimeError("Failed to create note.")
        return note

    def list_notes(self, archived: bool = False) -> list[Note]:
        return self._repo.list_notes(archived=archived)

    def get_note(self, note_id: int) -> Note | None:
        return self._repo.get_note(note_id)

    def save_note_content(self, note_id: int, content_html: str, plain_text: str) -> None:
        self._repo.update_note_content(note_id, content_html, plain_text)

    def update_note_title(self, note_id: int, title: str) -> None:
        self._repo.update_note_meta(note_id, title=title)

    def update_note_appearance(
        self, note_id: int, *, color: str | None = None, emoji_icon: str | None = None
    ) -> None:
        self._repo.update_note_meta(note_id, color=color, emoji_icon=emoji_icon)

    def set_archived(self, note_id: int, archived: bool) -> None:
        self._repo.set_archived(note_id, archived)

    def soft_delete(self, note_id: int) -> None:
        self._repo.soft_delete_note(note_id)
