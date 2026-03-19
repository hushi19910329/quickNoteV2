from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.constants import APP_NAME, AUTOSAVE_INTERVAL_MS
from src.controllers.note_controller import NoteController
from src.controllers.reminder_controller import ReminderController
from src.controllers.settings_controller import SettingsController
from src.models.tag import Tag
from src.ui.widgets.reminder_dialog import ReminderDialog
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
        self._reminder_controller: ReminderController | None = None
        self._current_note_id: int | None = None
        self._loading_note = False
        self._updating_note_tags = False
        self._tags: list[Tag] = []

        self._manual_collapsed = False
        self._dock_mode_enabled = False
        self._dock_collapsed = False
        self._dock_collapsed_width = 72
        self._dock_expanded_width = 520
        self._dock_internal_move = False

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._save_current_note)

        self._dock_collapse_timer = QTimer(self)
        self._dock_collapse_timer.setSingleShot(True)
        self._dock_collapse_timer.setInterval(550)
        self._dock_collapse_timer.timeout.connect(self._collapse_to_dock_if_needed)

        self.setWindowTitle(APP_NAME)
        self.resize(1240, 780)
        self._setup_ui()
        self._bind_events()
        self._bind_shortcuts()
        self._refresh_tags()
        self._refresh_note_list()

    def set_settings_controller(self, settings_controller: SettingsController) -> None:
        self._settings_controller = settings_controller

    def set_reminder_controller(self, reminder_controller: ReminderController) -> None:
        self._reminder_controller = reminder_controller
        self._reminder_controller.set_notify_callback(self._on_reminder_event)

    def _setup_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title/content...")
        self.search_input.setFixedHeight(25)
        self.show_archived_checkbox = QCheckBox("Archived")
        self.new_btn = QPushButton("New")
        self.archive_btn = QPushButton("Archive")
        self.delete_btn = QPushButton("Delete")
        self.reminder_btn = QPushButton("Set Reminder")
        self.clear_reminder_btn = QPushButton("Clear Reminder")
        self.snooze_btn = QPushButton("Snooze")
        self.snooze_combo = QComboBox()
        self.snooze_combo.addItem("5 min", userData=5)
        self.snooze_combo.addItem("15 min", userData=15)
        self.snooze_combo.addItem("60 min", userData=60)
        self.collapse_btn = QPushButton("List Mode")
        self.dock_btn = QPushButton("Dock Right")
        for btn in (
            self.new_btn,
            self.archive_btn,
            self.delete_btn,
            self.reminder_btn,
            self.clear_reminder_btn,
            self.snooze_btn,
            self.collapse_btn,
            self.dock_btn,
        ):
            btn.setFixedHeight(25)
        self.snooze_combo.setFixedHeight(25)

        top_bar.addWidget(QLabel("QuickNote V2"))
        top_bar.addStretch(1)
        top_bar.addWidget(self.search_input, 1)
        top_bar.addWidget(self.show_archived_checkbox)
        top_bar.addWidget(self.new_btn)
        top_bar.addWidget(self.archive_btn)
        top_bar.addWidget(self.delete_btn)
        top_bar.addWidget(self.reminder_btn)
        top_bar.addWidget(self.clear_reminder_btn)
        top_bar.addWidget(self.snooze_combo)
        top_bar.addWidget(self.snooze_btn)
        top_bar.addWidget(self.collapse_btn)
        top_bar.addWidget(self.dock_btn)
        layout.addLayout(top_bar)

        self.control_bar_widget = QWidget()
        control_bar = QHBoxLayout(self.control_bar_widget)
        control_bar.setContentsMargins(0, 0, 0, 0)
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
        control_bar.addSpacing(12)
        control_bar.addWidget(self.pin_checkbox)
        control_bar.addWidget(self.opacity_label)
        control_bar.addWidget(self.opacity_slider, 1)
        layout.addWidget(self.control_bar_widget)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel_widget = self._build_left_panel()
        self.center_panel_widget = self._build_center_panel()
        self.main_splitter.addWidget(self.left_panel_widget)
        self.main_splitter.addWidget(self.center_panel_widget)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 5)
        layout.addWidget(self.main_splitter, 1)

        self.status_label = QLabel("Ready")
        self.reminder_info_label = QLabel("Reminder: none")
        layout.addWidget(self.status_label)
        layout.addWidget(self.reminder_info_label)
        self._update_action_state()
        self._apply_view_mode()

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filter_group = QGroupBox("Tag Filter")
        filter_layout = QVBoxLayout(filter_group)
        self.tag_filter_list = QListWidget()
        self.tag_filter_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        filter_layout.addWidget(self.tag_filter_list)

        manage_group = QGroupBox("Tag Management")
        manage_layout = QVBoxLayout(manage_group)
        input_row = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("New tag name...")
        self.new_tag_input.setFixedHeight(25)
        self.add_tag_btn = QPushButton("Add")
        self.add_tag_btn.setFixedHeight(25)
        input_row.addWidget(self.new_tag_input, 1)
        input_row.addWidget(self.add_tag_btn)
        manage_layout.addLayout(input_row)
        self.delete_tag_btn = QPushButton("Delete Selected Filter Tags")
        self.delete_tag_btn.setFixedHeight(25)
        manage_layout.addWidget(self.delete_tag_btn)

        note_group = QGroupBox("Current Note Tags")
        note_layout = QVBoxLayout(note_group)
        self.note_tag_list = QListWidget()
        note_layout.addWidget(self.note_tag_list)

        layout.addWidget(filter_group, 3)
        layout.addWidget(manage_group, 1)
        layout.addWidget(note_group, 3)
        return container

    def _build_center_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.note_list = QListWidget()
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Select or create a note to start editing.")
        layout.addWidget(self.note_list, 2)
        layout.addWidget(self.note_editor, 5)
        return container

    def _bind_events(self) -> None:
        self.new_btn.clicked.connect(self._on_create_note)
        self.archive_btn.clicked.connect(self._on_toggle_archive)
        self.delete_btn.clicked.connect(self._on_delete_note)
        self.reminder_btn.clicked.connect(self._on_set_reminder)
        self.clear_reminder_btn.clicked.connect(self._on_clear_reminder)
        self.snooze_btn.clicked.connect(self._on_snooze)
        self.collapse_btn.clicked.connect(self._on_toggle_collapsed_mode)
        self.dock_btn.clicked.connect(self._on_toggle_dock_mode)

        self.note_list.currentItemChanged.connect(self._on_note_selected)
        self.note_list.customContextMenuRequested.connect(self._show_note_context_menu)
        self.note_editor.textChanged.connect(self._on_editor_changed)
        self.search_input.textChanged.connect(self._refresh_note_list)
        self.show_archived_checkbox.stateChanged.connect(self._on_archived_filter_changed)
        self.color_combo.currentTextChanged.connect(self._on_color_changed)
        self.emoji_combo.currentTextChanged.connect(self._on_emoji_changed)
        self.pin_checkbox.toggled.connect(self._on_pin_toggled)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.add_tag_btn.clicked.connect(self._on_add_tag)
        self.delete_tag_btn.clicked.connect(self._on_delete_selected_tags)
        self.tag_filter_list.itemSelectionChanged.connect(self._refresh_note_list)
        self.note_tag_list.itemChanged.connect(self._on_note_tag_item_changed)

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_create_note)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_current_note)
        QShortcut(QKeySequence("Delete"), self, activated=self._on_delete_note)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._on_toggle_collapsed_mode)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self._on_toggle_dock_mode)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self._on_set_reminder)

    def _show_note_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction("New Note", self._on_create_note)
        menu.addAction("Save", self._save_current_note)
        if self._current_note_id is not None:
            menu.addAction("Set Reminder", self._on_set_reminder)
            menu.addAction("Clear Reminder", self._on_clear_reminder)
            menu.addAction("Snooze", self._on_snooze)
            menu.addAction(
                "Restore" if self.show_archived_checkbox.isChecked() else "Archive",
                self._on_toggle_archive,
            )
            menu.addAction("Delete", self._on_delete_note)
        menu.addSeparator()
        menu.addAction(
            "Exit List Mode" if self._manual_collapsed else "Enter List Mode",
            self._on_toggle_collapsed_mode,
        )
        menu.addAction(
            "Undock Right" if self._dock_mode_enabled else "Dock Right",
            self._on_toggle_dock_mode,
        )
        menu.exec(self.note_list.viewport().mapToGlobal(pos))

    def _on_set_reminder(self) -> None:
        if self._current_note_id is None or self._reminder_controller is None:
            return
        current = self._reminder_controller.get_note_reminder(self._current_note_id)
        default_dt = None
        repeat_rule = None
        if current is not None:
            default_dt = datetime.fromisoformat(str(current["remind_at"]))
            repeat_rule = current["repeat_rule"]
        dialog = ReminderDialog(self, default_dt=default_dt, repeat_rule=repeat_rule)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        remind_at, rule = dialog.get_values()
        self._reminder_controller.on_set_reminder(self._current_note_id, remind_at, rule)
        self.status_label.setText("Reminder saved.")
        self._refresh_current_reminder_info()

    def _on_clear_reminder(self) -> None:
        if self._current_note_id is None or self._reminder_controller is None:
            return
        self._reminder_controller.on_clear_reminder(self._current_note_id)
        self.status_label.setText("Reminder cleared.")
        self._refresh_current_reminder_info()

    def _on_snooze(self) -> None:
        if self._current_note_id is None or self._reminder_controller is None:
            return
        minutes = int(self.snooze_combo.currentData())
        ok = self._reminder_controller.on_snooze(self._current_note_id, minutes)
        if ok:
            self.status_label.setText(f"Snoozed {minutes} minutes.")
        else:
            self.status_label.setText("No reminder to snooze.")
        self._refresh_current_reminder_info()

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
        self._refresh_note_tag_checks()
        self._refresh_current_reminder_info()
        self.status_label.setText("Archive status updated.")

    def _on_delete_note(self) -> None:
        if self._current_note_id is None:
            return
        self._note_controller.on_delete_note(self._current_note_id)
        self._current_note_id = None
        self.note_editor.clear()
        self._refresh_note_list()
        self._refresh_note_tag_checks()
        self._refresh_current_reminder_info()
        self.status_label.setText("Note deleted.")

    def _on_toggle_collapsed_mode(self) -> None:
        self._manual_collapsed = not self._manual_collapsed
        self._apply_view_mode()
        self.status_label.setText(
            "List mode enabled." if self._manual_collapsed else "List mode disabled."
        )

    def _on_toggle_dock_mode(self) -> None:
        self._dock_mode_enabled = not self._dock_mode_enabled
        if self._dock_mode_enabled:
            self._dock_expanded_width = max(480, self.width())
            self._dock_collapsed = True
            self._snap_to_right_edge(width=self._dock_collapsed_width)
        else:
            self._dock_collapsed = False
            self._snap_to_right_edge(width=max(720, self._dock_expanded_width))
        self._apply_view_mode()
        self._update_dock_button_text()
        self.status_label.setText(
            "Dock mode enabled. Hover to expand."
            if self._dock_mode_enabled
            else "Dock mode disabled."
        )

    def _on_note_selected(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._current_note_id = None
            self._update_action_state()
            self._refresh_note_tag_checks()
            self._refresh_current_reminder_info()
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
        self._refresh_note_tag_checks()
        self._refresh_current_reminder_info()
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
        self._refresh_note_tag_checks()
        self._refresh_current_reminder_info()
        self._update_action_state()

    def _on_color_changed(self, color_name: str) -> None:
        if self._loading_note or self._current_note_id is None:
            return
        self._note_controller.on_update_note_appearance(self._current_note_id, color=color_name)
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
        if self._settings_controller is not None:
            self._settings_controller.on_toggle_pin(enabled)

    def _on_opacity_changed(self, value: int) -> None:
        self.opacity_label.setText(f"Opacity: {value}%")
        if self._settings_controller is not None:
            self._settings_controller.on_change_transparency(value / 100)

    def _on_add_tag(self) -> None:
        name = self.new_tag_input.text().strip()
        if not name:
            self.status_label.setText("Tag name cannot be empty.")
            return
        tag = self._note_controller.on_create_tag(name)
        if tag is None:
            self.status_label.setText("Tag already exists or invalid.")
            return
        self.new_tag_input.clear()
        self._refresh_tags()
        self.status_label.setText(f"Tag '{tag.name}' created.")

    def _on_delete_selected_tags(self) -> None:
        selected = self.tag_filter_list.selectedItems()
        if not selected:
            self.status_label.setText("Select tags from Tag Filter first.")
            return
        for item in selected:
            tag_id = int(item.data(Qt.ItemDataRole.UserRole))
            self._note_controller.on_delete_tag(tag_id)
        self._refresh_tags()
        self._refresh_note_list()
        self._refresh_note_tag_checks()
        self.status_label.setText("Selected tags deleted.")

    def _on_note_tag_item_changed(self, _item: QListWidgetItem) -> None:
        if self._updating_note_tags or self._current_note_id is None:
            return
        checked_ids: list[int] = []
        for idx in range(self.note_tag_list.count()):
            it = self.note_tag_list.item(idx)
            if it.checkState() == Qt.CheckState.Checked:
                checked_ids.append(int(it.data(Qt.ItemDataRole.UserRole)))
        self._note_controller.on_set_note_tags(self._current_note_id, checked_ids)
        self.status_label.setText("Note tags updated.")
        self._refresh_note_list()
        self._select_note_in_list(self._current_note_id)

    def _on_reminder_event(self, message: str) -> None:
        self.status_label.setText(message)
        self._refresh_current_reminder_info()

    def _refresh_tags(self) -> None:
        selected_filter_ids = self._selected_filter_tag_ids()
        self._tags = self._note_controller.list_tags()

        self.tag_filter_list.blockSignals(True)
        self.tag_filter_list.clear()
        for tag in self._tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            item.setBackground(QColor(tag.color))
            self.tag_filter_list.addItem(item)
            if tag.id in selected_filter_ids:
                item.setSelected(True)
        self.tag_filter_list.blockSignals(False)
        self._refresh_note_tag_checks()

    def _refresh_note_tag_checks(self) -> None:
        note_tag_ids = (
            set(self._note_controller.get_note_tag_ids(self._current_note_id))
            if self._current_note_id is not None
            else set()
        )
        self._updating_note_tags = True
        self.note_tag_list.clear()
        for tag in self._tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            item.setCheckState(
                Qt.CheckState.Checked if tag.id in note_tag_ids else Qt.CheckState.Unchecked
            )
            item.setBackground(QColor(tag.color))
            self.note_tag_list.addItem(item)
        self.note_tag_list.setEnabled(self._current_note_id is not None)
        self._updating_note_tags = False

    def _refresh_current_reminder_info(self) -> None:
        if self._current_note_id is None or self._reminder_controller is None:
            self.reminder_info_label.setText("Reminder: none")
            return
        row = self._reminder_controller.get_note_reminder(self._current_note_id)
        if row is None or int(row["is_enabled"]) != 1:
            self.reminder_info_label.setText("Reminder: none")
            return
        remind_at = datetime.fromisoformat(str(row["remind_at"]))
        repeat_rule = row["repeat_rule"] or "one-time"
        self.reminder_info_label.setText(
            f"Reminder: {remind_at.strftime('%Y-%m-%d %H:%M')} ({repeat_rule})"
        )

    def _refresh_note_list(self, *_args) -> None:
        archived = self.show_archived_checkbox.isChecked()
        keyword = self.search_input.text().strip().lower()
        tag_ids = self._selected_filter_tag_ids()
        notes = self._note_controller.on_search(
            keyword, archived=archived, tag_ids=tag_ids or None
        )

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
            self._refresh_note_tag_checks()
            self._refresh_current_reminder_info()
        self._update_action_state()

    def _select_note_in_list(self, note_id: int) -> bool:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                return True
        return False

    def _selected_filter_tag_ids(self) -> list[int]:
        return [
            int(item.data(Qt.ItemDataRole.UserRole))
            for item in self.tag_filter_list.selectedItems()
        ]

    def _update_action_state(self) -> None:
        has_selection = self._current_note_id is not None
        self.delete_btn.setEnabled(has_selection)
        self.archive_btn.setEnabled(has_selection)
        self.color_combo.setEnabled(has_selection)
        self.emoji_combo.setEnabled(has_selection)
        self.reminder_btn.setEnabled(has_selection)
        self.clear_reminder_btn.setEnabled(has_selection)
        self.snooze_combo.setEnabled(has_selection)
        self.snooze_btn.setEnabled(has_selection)
        self.archive_btn.setText(
            "Restore" if self.show_archived_checkbox.isChecked() else "Archive"
        )

    def _update_dock_button_text(self) -> None:
        self.dock_btn.setText("Undock" if self._dock_mode_enabled else "Dock Right")

    def _apply_view_mode(self) -> None:
        effective_collapsed = self._manual_collapsed or self._dock_collapsed
        self.left_panel_widget.setVisible(not effective_collapsed)
        self.note_editor.setVisible(not effective_collapsed)
        self.control_bar_widget.setVisible(not effective_collapsed)
        self.collapse_btn.setText("Edit Mode" if self._manual_collapsed else "List Mode")

    def enterEvent(self, event) -> None:  # type: ignore[override]
        super().enterEvent(event)
        if self._dock_mode_enabled:
            self._dock_collapse_timer.stop()
            if self._dock_collapsed:
                self._dock_collapsed = False
                self._apply_view_mode()
                self._snap_to_right_edge(width=self._dock_expanded_width)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        super().leaveEvent(event)
        if self._dock_mode_enabled:
            self._dock_collapse_timer.start()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._dock_mode_enabled and not self._dock_internal_move:
            self._snap_to_right_edge(width=self.width())

    def _collapse_to_dock_if_needed(self) -> None:
        if not self._dock_mode_enabled or self.underMouse():
            return
        self._dock_collapsed = True
        self._apply_view_mode()
        self._snap_to_right_edge(width=self._dock_collapsed_width)

    def _snap_to_right_edge(self, width: int) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        new_width = max(56, min(width, available.width()))
        new_height = self.height()
        if new_height > available.height():
            new_height = available.height()
        x = available.right() - new_width + 1
        y = min(max(self.y(), available.top()), available.bottom() - new_height + 1)
        self._dock_internal_move = True
        self.setGeometry(x, y, new_width, new_height)
        self._dock_internal_move = False

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str, default: str) -> None:
        idx = combo.findText(value)
        combo.setCurrentText(default if idx < 0 else value)

