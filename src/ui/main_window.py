from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.constants import APP_NAME, AUTOSAVE_INTERVAL_MS
from src.controllers.note_controller import NoteController
from src.controllers.settings_controller import SettingsController
from src.models.note import Note
from src.utils.html_utils import first_line_from_plain_text

COLOR_MAP: dict[str, str] = {
    "yellow": "#FFF3B0",
    "green": "#D8F3DC",
    "blue": "#D9EAFD",
    "pink": "#FADADD",
    "gray": "#E5E7EB",
}

EMOJI_CHOICES = ["📝", "💡", "✅", "📌", "📚", "🧠"]


class MainWindow(QMainWindow):
    def __init__(self, note_controller: NoteController) -> None:
        super().__init__()
        self._note_controller = note_controller
        self._settings_controller: SettingsController | None = None
        self._current_note_id: int | None = None
        self._loading_note = False

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._save_current_note)

        self.setWindowTitle(APP_NAME)
        self.resize(1080, 700)
        self._setup_ui()
        self._bind_events()
        self._bind_shortcuts()
        self._refresh_note_list()

    def set_settings_controller(self, settings_controller: SettingsController) -> None:
        self._settings_controller = settings_controller

    def _setup_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        self.title_label = QLabel("QuickNote V2")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title/content...")
        self.search_input.setFixedHeight(25)
        self.show_archived_checkbox = QCheckBox("Archived")
        self.new_btn = QPushButton("New")
        self.archive_btn = QPushButton("Archive")
        self.delete_btn = QPushButton("Delete")
        for btn in (self.new_btn, self.archive_btn, self.delete_btn):
            btn.setFixedHeight(25)

        top_bar.addWidget(self.title_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(self.show_archived_checkbox)
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.archive_btn)
        top_bar.addWidget(self.delete_btn)
        layout.addLayout(top_bar)

        control_bar = QHBoxLayout()
        control_bar.setSpacing(6)
        self.color_combo = QComboBox()
        self.color_combo.addItems(list(COLOR_MAP.keys()))
        self.color_combo.setFixedHeight(25)
        self.emoji_combo = QComboBox()
        self.emoji_combo.addItems(EMOJI_CHOICES)
        self.emoji_combo.setFixedHeight(25)
        self.pin_checkbox = QCheckBox("Pin")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(40, 100)
        self.opacity_slider.setValue(95)
        self.opacity_slider.setFixedHeight(25)
        self.opacity_label = QLabel("Opacity: 95%")

        control_bar.addWidget(QLabel("Color"))
        control_bar.addWidget(self.color_combo)
        control_bar.addWidget(QLabel("Icon"))
        control_bar.addWidget(self.emoji_combo)
        control_bar.addSpacing(10)
        control_bar.addWidget(self.pin_checkbox)
        control_bar.addWidget(self.opacity_label)
        control_bar.addWidget(self.opacity_slider, 1)
        layout.addLayout(control_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.note_list = QListWidget()
        self.note_list.setMinimumWidth(320)
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select or create a note to start editing.")
        splitter.addWidget(self.note_list)
        splitter.addWidget(self.note_editor)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        self._update_action_state()

    def _bind_events(self) -> None:
        self.new_btn.clicked.connect(self._on_create_note)
        self.archive_btn.clicked.connect(self._on_toggle_archive)
        self.delete_btn.clicked.connect(self._on_delete_note)
        self.note_list.currentItemChanged.connect(self._on_note_selected)
        self.note_editor.textChanged.connect(self._on_editor_changed)
        self.search_input.textChanged.connect(self._refresh_note_list)
        self.show_archived_checkbox.stateChanged.connect(self._on_archived_filter_changed)
        self.color_combo.currentTextChanged.connect(self._on_color_changed)
        self.emoji_combo.currentTextChanged.connect(self._on_emoji_changed)
        self.pin_checkbox.toggled.connect(self._on_pin_toggled)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_create_note)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_current_note)
        QShortcut(QKeySequence("Delete"), self, activated=self._on_delete_note)

    def _on_create_note(self) -> None:
        note = self._note_controller.on_create_note()
        self._refresh_note_list()
        self._select_note_in_list(note.id)
        self.status_label.setText("Created a new note.")

    def _on_toggle_archive(self) -> None:
        if self._current_note_id is None:
            return
        archived_view = self.show_archived_checkbox.isChecked()
        self._note_controller.on_set_archived(self._current_note_id, not archived_view)
        self._current_note_id = None
        self.note_editor.clear()
        self._refresh_note_list()
        self.status_label.setText("Archive status updated.")

    def _on_delete_note(self) -> None:
        if self._current_note_id is None:
            return
        self._note_controller.on_delete_note(self._current_note_id)
        self._current_note_id = None
        self.note_editor.clear()
        self._refresh_note_list()
        self.status_label.setText("Note deleted.")

    def _on_note_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._current_note_id = None
            self._update_action_state()
            return

        note_id = int(current.data(Qt.ItemDataRole.UserRole))
        note = self._note_controller.on_select_note(note_id)
        if note is None:
            return

        self._current_note_id = note.id
        self._loading_note = True
        self.note_editor.setHtml(note.content_html or "")
        self._set_combo_value(self.color_combo, note.color, "yellow")
        self._set_combo_value(self.emoji_combo, note.emoji_icon, "📝")
        self._loading_note = False
        self._update_action_state()

    def _on_editor_changed(self) -> None:
        if self._loading_note or self._current_note_id is None:
            return
        self.status_label.setText("Editing... autosave pending")
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
            self._note_controller.on_note_title_changed(self._current_note_id, first_line)
        self._refresh_note_list()
        self._select_note_in_list(self._current_note_id)
        self.status_label.setText("Saved")

    def _on_archived_filter_changed(self) -> None:
        self._current_note_id = None
        self.note_editor.clear()
        self._refresh_note_list()
        self._update_action_state()

    def _on_color_changed(self, color_name: str) -> None:
        if self._loading_note or self._current_note_id is None:
            return
        self._note_controller.on_update_note_appearance(
            self._current_note_id, color=color_name
        )
        self._refresh_note_list()
        self._select_note_in_list(self._current_note_id)

    def _on_emoji_changed(self, emoji_icon: str) -> None:
        if self._loading_note or self._current_note_id is None:
            return
        self._note_controller.on_update_note_appearance(
            self._current_note_id, emoji_icon=emoji_icon
        )
        self._refresh_note_list()
        self._select_note_in_list(self._current_note_id)

    def _on_pin_toggled(self, enabled: bool) -> None:
        if self._settings_controller is None:
            return
        self._settings_controller.on_toggle_pin(enabled)

    def _on_opacity_changed(self, value: int) -> None:
        alpha = value / 100
        self.opacity_label.setText(f"Opacity: {value}%")
        if self._settings_controller is not None:
            self._settings_controller.on_change_transparency(alpha)

    def _refresh_note_list(self, *_args) -> None:
        archived = self.show_archived_checkbox.isChecked()
        keyword = self.search_input.text().strip().lower()
        notes = self._note_controller.list_notes(archived=archived)
        if keyword:
            notes = [
                n
                for n in notes
                if keyword in n.title.lower() or keyword in n.plain_text.lower()
            ]

        selected_id = self._current_note_id
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in notes:
            title = note.title.strip() or "(Untitled)"
            preview = note.plain_text.strip().replace("\n", " ")[:40]
            text = f"{note.emoji_icon} {title}"
            if preview:
                text = f"{text} - {preview}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            item.setBackground(QColor(COLOR_MAP.get(note.color, COLOR_MAP["gray"])))
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)

        if selected_id is not None and not self._select_note_in_list(selected_id):
            self._current_note_id = None
            self.note_editor.clear()
        self._update_action_state()

    def _select_note_in_list(self, note_id: int) -> bool:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                return True
        return False

    def _update_action_state(self) -> None:
        has_selection = self._current_note_id is not None
        self.delete_btn.setEnabled(has_selection)
        self.archive_btn.setEnabled(has_selection)
        self.color_combo.setEnabled(has_selection)
        self.emoji_combo.setEnabled(has_selection)
        self.archive_btn.setText(
            "Restore" if self.show_archived_checkbox.isChecked() else "Archive"
        )

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str, default: str) -> None:
        idx = combo.findText(value)
        combo.setCurrentText(default if idx < 0 else value)
