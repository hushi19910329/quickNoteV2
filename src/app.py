from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.config.constants import APP_DATA_DIR, APP_NAME, DB_PATH
from src.controllers.note_controller import NoteController
from src.controllers.reminder_controller import ReminderController
from src.controllers.settings_controller import SettingsController
from src.db.connection import DatabaseConnection
from src.db.repositories.note_repo import NoteRepository
from src.db.repositories.reminder_repo import ReminderRepository
from src.db.repositories.tag_repo import TagRepository
from src.db.schema import init_schema
from src.services.note_service import NoteService
from src.services.reminder_service import ReminderService
from src.services.search_service import SearchService
from src.services.window_service import WindowService
from src.ui.main_window import MainWindow


class QuickNoteApp:
    def __init__(self) -> None:
        self._qt_app: QApplication | None = None
        self._db = DatabaseConnection(DB_PATH)
        self._reminder_controller: ReminderController | None = None

    def bootstrap(self) -> MainWindow:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = self._db.connect()
        init_schema(conn)

        note_repo = NoteRepository(conn)
        tag_repo = TagRepository(conn)
        reminder_repo = ReminderRepository(conn)

        note_service = NoteService(note_repo, tag_repo)
        reminder_service = ReminderService(reminder_repo, note_repo)
        search_service = SearchService(note_service)

        note_controller = NoteController(note_service, search_service)
        self._reminder_controller = ReminderController(reminder_service)
        self._reminder_controller.initialize()

        self._qt_app = QApplication.instance() or QApplication(sys.argv)
        self._qt_app.setApplicationName(APP_NAME)
        self._qt_app.aboutToQuit.connect(self._on_about_to_quit)
        self._apply_style()

        window = MainWindow(note_controller)
        settings_controller = SettingsController(WindowService(window))
        window.set_settings_controller(settings_controller)
        window.set_reminder_controller(self._reminder_controller)
        return window

    def run(self) -> int:
        window = self.bootstrap()
        window.show()
        assert self._qt_app is not None
        return self._qt_app.exec()

    def _on_about_to_quit(self) -> None:
        if self._reminder_controller is not None:
            self._reminder_controller.shutdown()
        self._db.close()

    def _apply_style(self) -> None:
        assert self._qt_app is not None
        qss = _read_text_if_exists(_style_path())
        if qss:
            self._qt_app.setStyleSheet(qss)


def main() -> int:
    app = QuickNoteApp()
    return app.run()


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _style_path() -> Path:
    return Path(__file__).parent / "ui" / "styles" / "light_theme.qss"

