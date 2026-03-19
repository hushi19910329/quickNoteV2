from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from src.models.tag import Tag


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TagRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_tag(self, name: str, color: str = "#4A90E2") -> int:
        cur = self._conn.execute(
            "INSERT INTO tags(name, color, created_at) VALUES(?, ?, ?)",
            (name.strip(), color, _now_iso()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_tag(self, tag_id: int, *, name: str | None = None, color: str | None = None) -> None:
        row = self._conn.execute(
            "SELECT name, color FROM tags WHERE id = ?",
            (tag_id,),
        ).fetchone()
        if row is None:
            return
        self._conn.execute(
            "UPDATE tags SET name = ?, color = ? WHERE id = ?",
            (name or row["name"], color or row["color"], tag_id),
        )
        self._conn.commit()

    def delete_tag(self, tag_id: int) -> None:
        self._conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self._conn.commit()

    def list_tags(self) -> list[Tag]:
        rows = self._conn.execute(
            "SELECT * FROM tags ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [
            Tag(
                id=row["id"],
                name=row["name"],
                color=row["color"],
                sort_order=row["sort_order"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_note_tag_ids(self, note_id: int) -> list[int]:
        rows = self._conn.execute(
            "SELECT tag_id FROM note_tags WHERE note_id = ? ORDER BY tag_id ASC",
            (note_id,),
        ).fetchall()
        return [int(r["tag_id"]) for r in rows]

    def set_note_tags(self, note_id: int, tag_ids: list[int]) -> None:
        self._conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        if tag_ids:
            now = _now_iso()
            self._conn.executemany(
                "INSERT INTO note_tags(note_id, tag_id, created_at) VALUES(?, ?, ?)",
                [(note_id, tag_id, now) for tag_id in sorted(set(tag_ids))],
            )
        self._conn.commit()

