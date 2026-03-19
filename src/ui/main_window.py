from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.constants import APP_NAME, AUTOSAVE_INTERVAL_MS
from src.controllers.note_controller import NoteController
from src.models.note import Note
from src.utils.html_utils import first_line_from_plain_text


class MainWindow(QMainWindow):
    def __init__(self, note_controller: NoteController) -> None:
        super().__init__()
        self._note_controller = note_controller
        self._current_note_id: int | None = None
        self._loading_note = False
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._save_current_note)

        self.setWindowTitle(APP_NAME)
        self.resize(980, 640)
        self._setup_ui()
        self._bind_events()
        self.refresh_note_list()

    def _setup_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        self.title_label = QLabel("QuickNote V2")
        self.new_btn = QPushButton("New")
        self.new_btn.setFixedHeight(25)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedHeight(25)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.setFixedHeight(25)

        top_bar.addWidget(self.title_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.delete_btn)
        layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.note_list = QListWidget()
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select or create a note.")
        self.note_list.setMinimumWidth(280)
        splitter.addWidget(self.note_list)
        splitter.addWidget(self.note_editor)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter, 1)

    def _bind_events(self) -> None:
        self.new_btn.clicked.connect(self._on_create_note)
        self.delete_btn.clicked.connect(self._on_delete_note)
        self.note_list.currentItemChanged.connect(self._on_note_selected)
        self.note_editor.textChanged.connect(self._on_editor_changed)
        self.search_input.textChanged.connect(self._on_search_text_changed)

    def refresh_note_list(self, notes: list[Note] | None = None) -> None:
        notes = notes if notes is not None else self._note_controller.list_notes()
        current_id = self._current_note_id
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in notes:
            title = note.title.strip() or "(Untitled)"
            preview = note.plain_text.strip().replace("\n", " ")[:30]
            text = f"{note.emoji_icon} {title}"
            if preview:
                text = f"{text} - {preview}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)
        if current_id is not None:
            self._select_note_in_list(current_id)

    def _select_note_in_list(self, note_id: int) -> None:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                break

    def _on_create_note(self) -> None:
        note = self._note_controller.on_create_note()
        self.refresh_note_list()
        self._select_note_in_list(note.id)

    def _on_delete_note(self) -> None:
        if self._current_note_id is None:
            return
        self._note_controller.on_delete_note(self._current_note_id)
        self._current_note_id = None
        self.note_editor.clear()
        self.refresh_note_list()

    def _on_note_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        note_id = int(current.data(Qt.ItemDataRole.UserRole))
        note = self._note_controller.on_select_note(note_id)
        if note is None:
            return
        self._current_note_id = note.id
        self._loading_note = True
        self.note_editor.setHtml(note.content_html or "")
        self._loading_note = False

    def _on_editor_changed(self) -> None:
        if self._loading_note or self._current_note_id is None:
            return
        self._autosave_timer.start()

    def _save_current_note(self) -> None:
        if self._current_note_id is None:
            return
        self._note_controller.on_note_content_changed(
            self._current_note_id,
            self.note_editor.toHtml(),
            self.note_editor.toPlainText(),
        )
        first_line = first_line_from_plain_text(self.note_editor.toPlainText())
        if first_line:
            self._note_controller.on_note_title_changed(
                self._current_note_id, first_line
            )
        self.refresh_note_list()

    def _on_search_text_changed(self, text: str) -> None:
        notes = self._note_controller.on_search(text)
        self.refresh_note_list(notes=notes)
