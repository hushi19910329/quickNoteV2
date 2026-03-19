from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from src.models.note import Note


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NoteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_note(
        self,
        title: str = "",
        content_html: str = "",
        plain_text: str = "",
        color: str = "yellow",
        emoji_icon: str = "📝",
    ) -> int:
        now = _now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO notes(title, content_html, plain_text, color, emoji_icon, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, content_html, plain_text, color, emoji_icon, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_note_content(self, note_id: int, content_html: str, plain_text: str) -> None:
        self._conn.execute(
            """
            UPDATE notes
            SET content_html = ?, plain_text = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (content_html, plain_text, _now_iso(), note_id),
        )
        self._conn.commit()

    def update_note_meta(
        self,
        note_id: int,
        *,
        title: str | None = None,
        color: str | None = None,
        emoji_icon: str | None = None,
    ) -> None:
        row = self._conn.execute(
            "SELECT title, color, emoji_icon FROM notes WHERE id = ? AND is_deleted = 0",
            (note_id,),
        ).fetchone()
        if row is None:
            return
        self._conn.execute(
            """
            UPDATE notes
            SET title = ?, color = ?, emoji_icon = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (
                title if title is not None else row["title"],
                color if color is not None else row["color"],
                emoji_icon if emoji_icon is not None else row["emoji_icon"],
                _now_iso(),
                note_id,
            ),
        )
        self._conn.commit()

    def get_note(self, note_id: int) -> Note | None:
        row = self._conn.execute(
            "SELECT * FROM notes WHERE id = ? AND is_deleted = 0",
            (note_id,),
        ).fetchone()
        return self._row_to_note(row) if row else None

    def list_notes(self, archived: bool = False, tag_ids: list[int] | None = None) -> list[Note]:
        if not tag_ids:
            rows = self._conn.execute(
                """
                SELECT * FROM notes
                WHERE is_deleted = 0 AND is_archived = ?
                ORDER BY updated_at DESC
                """,
                (1 if archived else 0,),
            ).fetchall()
            return [self._row_to_note(row) for row in rows]

        placeholders = ",".join("?" for _ in tag_ids)
        params: list[object] = [1 if archived else 0, *tag_ids, len(set(tag_ids))]
        rows = self._conn.execute(
            f"""
            SELECT n.*
            FROM notes n
            JOIN note_tags nt ON n.id = nt.note_id
            WHERE n.is_deleted = 0
              AND n.is_archived = ?
              AND nt.tag_id IN ({placeholders})
            GROUP BY n.id
            HAVING COUNT(DISTINCT nt.tag_id) = ?
            ORDER BY n.updated_at DESC
            """,
            params,
        ).fetchall()
        return [self._row_to_note(row) for row in rows]

    def set_archived(self, note_id: int, archived: bool) -> None:
        self._conn.execute(
            "UPDATE notes SET is_archived = ?, updated_at = ? WHERE id = ? AND is_deleted = 0",
            (1 if archived else 0, _now_iso(), note_id),
        )
        self._conn.commit()

    def soft_delete_note(self, note_id: int) -> None:
        self._conn.execute(
            "UPDATE notes SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (_now_iso(), note_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> Note:
        return Note(
            id=row["id"],
            title=row["title"],
            content_html=row["content_html"],
            plain_text=row["plain_text"],
            color=row["color"],
            emoji_icon=row["emoji_icon"],
            is_pinned=row["is_pinned"],
            is_archived=row["is_archived"],
            is_deleted=row["is_deleted"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

