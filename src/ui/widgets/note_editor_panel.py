from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QPoint, Qt, QMimeData, Signal
from PySide6.QtGui import QImage, QPixmap, QTextBlockFormat, QTextCursor, QTextImageFormat
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.constants import IMAGE_DIR

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
PRESET_WIDTHS = {"S": 240, "M": 480, "L": 720}


class ImagePreviewDialog(QDialog):
    def __init__(self, image_paths: list[Path], current_index: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Image Preview")
        self.resize(920, 680)
        self._image_paths = image_paths
        self._current_index = max(0, min(current_index, len(image_paths) - 1)) if image_paths else 0
        self._zoom = 1.0

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.info_label = QLabel("")
        self.prev_btn = QPushButton("Prev")
        self.next_btn = QPushButton("Next")
        self.zoom_out_btn = QPushButton("-")
        self.zoom_in_btn = QPushButton("+")
        self.reset_btn = QPushButton("100%")
        for btn in (self.prev_btn, self.next_btn, self.zoom_out_btn, self.zoom_in_btn, self.reset_btn):
            btn.setFixedHeight(25)
        toolbar.addWidget(self.prev_btn)
        toolbar.addWidget(self.next_btn)
        toolbar.addSpacing(10)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.reset_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.info_label)
        layout.addLayout(toolbar)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        layout.addWidget(self.view, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.prev_btn.clicked.connect(self._on_prev)
        self.next_btn.clicked.connect(self._on_next)
        self.zoom_out_btn.clicked.connect(lambda: self._set_zoom(self._zoom / 1.15))
        self.zoom_in_btn.clicked.connect(lambda: self._set_zoom(self._zoom * 1.15))
        self.reset_btn.clicked.connect(lambda: self._set_zoom(1.0))

        self._load_current()

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if event.angleDelta().y() > 0:
            self._set_zoom(self._zoom * 1.1)
        else:
            self._set_zoom(self._zoom / 1.1)

    def _on_prev(self) -> None:
        if not self._image_paths:
            return
        self._current_index = (self._current_index - 1) % len(self._image_paths)
        self._load_current()

    def _on_next(self) -> None:
        if not self._image_paths:
            return
        self._current_index = (self._current_index + 1) % len(self._image_paths)
        self._load_current()

    def _load_current(self) -> None:
        self.scene.clear()
        if not self._image_paths:
            self.info_label.setText("No image")
            return
        path = self._image_paths[self._current_index]
        img = QImage(str(path))
        if img.isNull():
            self.info_label.setText(f"Failed: {path.name}")
            return
        item = QGraphicsPixmapItem()
        item.setPixmap(QPixmap.fromImage(img))
        self.scene.addItem(item)
        self.scene.setSceneRect(item.boundingRect())
        self._zoom = 1.0
        self.view.resetTransform()
        self.info_label.setText(f"{self._current_index + 1}/{len(self._image_paths)} - {path.name}")

    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.1, min(8.0, zoom))
        self.view.resetTransform()
        self.view.scale(self._zoom, self._zoom)


class NoteEditorPanel(QTextEdit):
    image_selected = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image_dir = IMAGE_DIR
        self._image_dir.mkdir(parents=True, exist_ok=True)
        self._active_image_cursor: QTextCursor | None = None
        self._active_image_name: str | None = None
        self._resize_dragging = False
        self._resize_start_x = 0
        self._resize_start_width = 0

        self._toolbar = self._create_image_toolbar()
        self._toolbar.hide()
        self.cursorPositionChanged.connect(self._sync_image_selection)

    def set_image_dir(self, image_dir: Path) -> None:
        self._image_dir = image_dir
        self._image_dir.mkdir(parents=True, exist_ok=True)

    def insert_image_from_path(self, source_path: str | Path) -> bool:
        source = Path(source_path)
        if not source.exists():
            return False
        target = self._copy_image_to_assets(source)
        self._insert_image(target)
        return True

    def canInsertFromMimeData(self, source: QMimeData) -> bool:  # type: ignore[override]
        if source.hasImage():
            return True
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
                    return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData) -> None:  # type: ignore[override]
        if source.hasImage():
            image_obj = source.imageData()
            if isinstance(image_obj, QImage):
                target = self._save_qimage(image_obj)
                self._insert_image(target)
                return
        if source.hasUrls():
            inserted = False
            for url in source.urls():
                if not url.isLocalFile():
                    continue
                local = Path(url.toLocalFile())
                if local.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                target = self._copy_image_to_assets(local)
                self._insert_image(target)
                inserted = True
            if inserted:
                return
        super().insertFromMimeData(source)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        super().mousePressEvent(event)
        self._sync_image_selection()
        if (
            event.button() == Qt.MouseButton.LeftButton
            and (event.modifiers() & Qt.KeyboardModifier.AltModifier)
            and self._active_image_cursor is not None
        ):
            self._resize_dragging = True
            self._resize_start_x = event.pos().x()
            fmt = self._active_image_format()
            self._resize_start_width = int(fmt.width()) if fmt is not None and fmt.width() > 0 else 320

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        cursor = self.cursorForPosition(event.pos())
        if self._try_select_image_cursor(cursor):
            self._open_preview_dialog()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and self._active_image_cursor is not None:
            factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
            self._scale_active_image(factor)
            event.accept()
            return
        super().wheelEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._resize_dragging and self._active_image_cursor is not None:
            dx = event.pos().x() - self._resize_start_x
            self._set_active_image_width(max(80, self._resize_start_width + dx))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._resize_dragging = False
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        cursor = self.cursorForPosition(event.pos())
        if self._try_select_image_cursor(cursor):
            menu = QMenu(self)
            menu.addAction("Zoom In", lambda: self._scale_active_image(1.12))
            menu.addAction("Zoom Out", lambda: self._scale_active_image(1 / 1.12))
            menu.addAction("Original Size", self._set_active_image_original_size)
            menu.addAction("Fit Width", self._fit_active_image_to_editor_width)
            menu.addSeparator()
            menu.addAction("Preset S", lambda: self._set_active_image_width(PRESET_WIDTHS["S"]))
            menu.addAction("Preset M", lambda: self._set_active_image_width(PRESET_WIDTHS["M"]))
            menu.addAction("Preset L", lambda: self._set_active_image_width(PRESET_WIDTHS["L"]))
            menu.addSeparator()
            menu.addAction("Align Left", lambda: self._align_active_image(Qt.AlignmentFlag.AlignLeft))
            menu.addAction("Align Center", lambda: self._align_active_image(Qt.AlignmentFlag.AlignHCenter))
            menu.addAction("Align Right", lambda: self._align_active_image(Qt.AlignmentFlag.AlignRight))
            menu.addAction("Increase Spacing", lambda: self._change_active_image_spacing(6))
            menu.addAction("Decrease Spacing", lambda: self._change_active_image_spacing(-6))
            menu.addSeparator()
            menu.addAction("Add Caption", self._add_caption_for_active_image)
            menu.addAction("Open Preview", self._open_preview_dialog)
            menu.addAction("Copy Image Path", self._copy_active_image_path)
            menu.addAction("Open in Explorer", self._open_active_image_in_explorer)
            menu.addAction("Delete Image", self._delete_active_image)
            menu.exec(event.globalPos())
            return
        super().contextMenuEvent(event)

    def _create_image_toolbar(self) -> QWidget:
        bar = QWidget(self.viewport())
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        bar.setStyleSheet("background:#ffffff;border:1px solid #d1d5db;border-radius:6px;")

        actions: list[tuple[str, callable]] = [
            ("-", lambda: self._scale_active_image(1 / 1.12)),
            ("+", lambda: self._scale_active_image(1.12)),
            ("100%", self._set_active_image_original_size),
            ("Fit", self._fit_active_image_to_editor_width),
            ("S", lambda: self._set_active_image_width(PRESET_WIDTHS["S"])),
            ("M", lambda: self._set_active_image_width(PRESET_WIDTHS["M"])),
            ("L", lambda: self._set_active_image_width(PRESET_WIDTHS["L"])),
            ("Preview", self._open_preview_dialog),
        ]
        for text, handler in actions:
            btn = QPushButton(text)
            btn.setFixedHeight(24)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
        return bar

    def _sync_image_selection(self) -> None:
        cursor = self.textCursor()
        ok = self._try_select_image_cursor(cursor)
        self.image_selected.emit(ok)
        if ok:
            self._position_toolbar_near_cursor()
        else:
            self._toolbar.hide()

    def _position_toolbar_near_cursor(self) -> None:
        if self._active_image_cursor is None:
            self._toolbar.hide()
            return
        rect = self.cursorRect(self._active_image_cursor)
        x = max(4, min(rect.x(), max(4, self.viewport().width() - self._toolbar.width() - 8)))
        y = max(4, rect.y() - self._toolbar.height() - 6)
        self._toolbar.adjustSize()
        self._toolbar.move(x, y)
        self._toolbar.show()

    def _try_select_image_cursor(self, cursor: QTextCursor) -> bool:
        c = QTextCursor(cursor)
        fmt = c.charFormat()
        if fmt.isImageFormat():
            self._active_image_cursor = c
            self._active_image_name = QTextImageFormat(fmt).name()
            return True
        c.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        fmt2 = c.charFormat()
        if fmt2.isImageFormat():
            self._active_image_cursor = c
            self._active_image_name = QTextImageFormat(fmt2).name()
            return True
        self._active_image_cursor = None
        self._active_image_name = None
        return False

    def _active_image_format(self) -> QTextImageFormat | None:
        if self._active_image_cursor is None:
            return None
        fmt = self._active_image_cursor.charFormat()
        if not fmt.isImageFormat():
            return None
        return QTextImageFormat(fmt)

    def _apply_image_format(self, img_fmt: QTextImageFormat) -> None:
        if self._active_image_cursor is None:
            return
        c = QTextCursor(self._active_image_cursor)
        c.setCharFormat(img_fmt)
        self.setTextCursor(c)
        self._active_image_cursor = c
        self._active_image_name = img_fmt.name()
        self._position_toolbar_near_cursor()

    def _scale_active_image(self, factor: float) -> None:
        fmt = self._active_image_format()
        if fmt is None:
            return
        current_w = fmt.width() if fmt.width() > 0 else self._guess_image_pixel_size(fmt.name())[0]
        new_w = max(80.0, min(float(self.viewport().width() * 2), float(current_w) * factor))
        self._set_active_image_width(int(new_w))

    def _set_active_image_width(self, width_px: int) -> None:
        fmt = self._active_image_format()
        if fmt is None:
            return
        pix_w, pix_h = self._guess_image_pixel_size(fmt.name())
        if pix_w <= 0:
            pix_w = width_px
            pix_h = int(width_px * 0.75)
        ratio = pix_h / pix_w if pix_w else 0.75
        fmt.setWidth(float(width_px))
        fmt.setHeight(float(max(40, int(width_px * ratio))))
        self._apply_image_format(fmt)

    def _set_active_image_original_size(self) -> None:
        fmt = self._active_image_format()
        if fmt is None:
            return
        pix_w, pix_h = self._guess_image_pixel_size(fmt.name())
        if pix_w > 0 and pix_h > 0:
            fmt.setWidth(float(pix_w))
            fmt.setHeight(float(pix_h))
            self._apply_image_format(fmt)

    def _fit_active_image_to_editor_width(self) -> None:
        target = max(160, int(self.viewport().width() * 0.92))
        self._set_active_image_width(target)

    def _align_active_image(self, alignment: Qt.AlignmentFlag) -> None:
        if self._active_image_cursor is None:
            return
        c = QTextCursor(self._active_image_cursor)
        c.select(QTextCursor.SelectionType.BlockUnderCursor)
        bf = c.blockFormat()
        bf.setAlignment(alignment)
        c.setBlockFormat(bf)
        self.setTextCursor(c)
        self._active_image_cursor = c

    def _change_active_image_spacing(self, delta: int) -> None:
        if self._active_image_cursor is None:
            return
        c = QTextCursor(self._active_image_cursor)
        c.select(QTextCursor.SelectionType.BlockUnderCursor)
        bf = QTextBlockFormat(c.blockFormat())
        new_top = max(0.0, bf.topMargin() + float(delta))
        new_bottom = max(0.0, bf.bottomMargin() + float(delta))
        bf.setTopMargin(new_top)
        bf.setBottomMargin(new_bottom)
        c.setBlockFormat(bf)
        self.setTextCursor(c)
        self._active_image_cursor = c

    def _add_caption_for_active_image(self) -> None:
        if self._active_image_cursor is None:
            return
        text, ok = QInputDialog.getText(self, "Image Caption", "Caption text:")
        if not ok:
            return
        caption = text.strip()
        if not caption:
            return
        c = QTextCursor(self._active_image_cursor)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        c.insertBlock()
        bf = c.blockFormat()
        bf.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        c.setBlockFormat(bf)
        c.insertHtml(f'<span style="color:#6b7280;font-style:italic;">{caption}</span>')
        c.insertBlock()

    def _delete_active_image(self) -> None:
        if self._active_image_cursor is None:
            return
        c = QTextCursor(self._active_image_cursor)
        c.deleteChar()
        self._active_image_cursor = None
        self._active_image_name = None
        self._toolbar.hide()

    def _copy_active_image_path(self) -> None:
        path = self._resolve_image_path(self._active_image_name or "")
        if path is None:
            return
        QApplication.clipboard().setText(str(path))

    def _open_active_image_in_explorer(self) -> None:
        path = self._resolve_image_path(self._active_image_name or "")
        if path is None:
            return
        try:
            os.startfile(str(path.parent))  # type: ignore[attr-defined]
        except Exception:
            return

    def _open_preview_dialog(self) -> None:
        all_paths = self._collect_image_paths()
        if not all_paths:
            return
        active = self._resolve_image_path(self._active_image_name or "")
        index = 0
        if active is not None:
            try:
                index = all_paths.index(active)
            except ValueError:
                index = 0
        dlg = ImagePreviewDialog(all_paths, current_index=index, parent=self)
        dlg.exec()

    def _collect_image_paths(self) -> list[Path]:
        out: list[Path] = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fmt = frag.charFormat()
                    if fmt.isImageFormat():
                        path = self._resolve_image_path(QTextImageFormat(fmt).name())
                        if path is not None and path not in out:
                            out.append(path)
                it += 1
            block = block.next()
        return out

    def _resolve_image_path(self, name: str) -> Path | None:
        if not name:
            return None
        parsed = urlparse(name)
        if parsed.scheme == "file":
            p = Path(parsed.path.lstrip("/"))
        else:
            p = Path(name)
        if p.exists():
            return p.resolve()
        return None

    def _guess_image_pixel_size(self, name: str) -> tuple[int, int]:
        path = self._resolve_image_path(name)
        if path is None:
            return 0, 0
        img = QImage(str(path))
        if img.isNull():
            return 0, 0
        return img.width(), img.height()

    def _copy_image_to_assets(self, source: Path) -> Path:
        suffix = source.suffix.lower() if source.suffix else ".png"
        target = self._image_dir / f"img_{uuid.uuid4().hex}{suffix}"
        shutil.copy2(source, target)
        return target.resolve()

    def _save_qimage(self, image: QImage) -> Path:
        target = self._image_dir / f"img_{uuid.uuid4().hex}.png"
        image.save(str(target), "PNG")
        return target.resolve()

    def _insert_image(self, image_path: Path) -> None:
        uri = image_path.resolve().as_uri()
        img = QImage(str(image_path))
        width = min(max(220, img.width()), max(320, int(self.viewport().width() * 0.92))) if not img.isNull() else 360
        self.textCursor().insertHtml(
            f'<p style="text-align:center;"><img src="{uri}" width="{width}" style="max-width: 100%; height: auto;" /></p>'
        )
