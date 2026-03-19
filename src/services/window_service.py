from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow


class WindowService:
    def __init__(self, window: QMainWindow) -> None:
        self._window = window

    def set_always_on_top(self, enabled: bool) -> None:
        flags = self._window.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self._window.setWindowFlags(flags)
        self._window.show()

    def set_transparency(self, alpha: float) -> None:
        self._window.setWindowOpacity(max(0.2, min(1.0, alpha)))

