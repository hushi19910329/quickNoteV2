from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Tag:
    id: int
    name: str
    color: str = "#4A90E2"
    sort_order: int = 0
    created_at: str = ""

