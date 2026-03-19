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
            (name, color, _now_iso()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

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

