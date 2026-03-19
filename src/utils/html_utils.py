from __future__ import annotations


def first_line_from_plain_text(text: str, max_len: int = 60) -> str:
    lines = text.strip().splitlines()
    return lines[0][:max_len] if lines else ""

