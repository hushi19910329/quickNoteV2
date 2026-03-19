from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)


class ReminderDialog(QDialog):
    def __init__(self, parent=None, default_dt: datetime | None = None, repeat_rule: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Reminder")
        self.resize(360, 140)

        dt = default_dt or datetime.now().astimezone()
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDateTime(QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute))
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("One-time", userData=None)
        self.repeat_combo.addItem("Daily", userData="daily")
        if repeat_rule == "daily":
            self.repeat_combo.setCurrentIndex(1)
        else:
            self.repeat_combo.setCurrentIndex(0)

        form.addRow("Remind At", self.datetime_edit)
        form.addRow("Repeat", self.repeat_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[datetime, str | None]:
        dt = self.datetime_edit.dateTime().toPython()
        if dt.tzinfo is None:
            dt = dt.astimezone()
        repeat_rule = self.repeat_combo.currentData()
        return dt, repeat_rule

