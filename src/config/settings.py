from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.constants import SETTINGS_PATH


class AppSettings:
    def __init__(self, settings_path: Path | None = None) -> None:
        self._path = settings_path or SETTINGS_PATH
        self._cache: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            self._cache = {}
            return self._cache
        self._cache = json.loads(self._path.read_text(encoding="utf-8"))
        return self._cache

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._cache = data

    def get(self, key: str, default: Any = None) -> Any:
        if not self._cache:
            self.load()
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not self._cache:
            self.load()
        self._cache[key] = value
        self.save(self._cache)

