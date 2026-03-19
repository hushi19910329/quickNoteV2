from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QTextEdit

from src.config.constants import IMAGE_DIR

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


class NoteEditorPanel(QTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image_dir = IMAGE_DIR
        self._image_dir.mkdir(parents=True, exist_ok=True)

    def set_image_dir(self, image_dir: Path) -> None:
        self._image_dir = image_dir
        self._image_dir.mkdir(parents=True, exist_ok=True)

    def insert_image_from_path(self, source_path: str | Path) -> bool:
        source = Path(source_path)
        if not source.exists():
            return False
        target = self._copy_image_to_assets(source)
        self._insert_image_html(target)
        return True

    def canInsertFromMimeData(self, source: QMimeData) -> bool:  # type: ignore[override]
        if source.hasImage():
            return True
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    suffix = Path(url.toLocalFile()).suffix.lower()
                    if suffix in IMAGE_SUFFIXES:
                        return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData) -> None:  # type: ignore[override]
        if source.hasImage():
            image_obj = source.imageData()
            if isinstance(image_obj, QImage):
                target = self._save_qimage(image_obj)
                self._insert_image_html(target)
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
                self._insert_image_html(target)
                inserted = True
            if inserted:
                return
        super().insertFromMimeData(source)

    def _copy_image_to_assets(self, source: Path) -> Path:
        suffix = source.suffix.lower() if source.suffix else ".png"
        target = self._image_dir / f"img_{uuid.uuid4().hex}{suffix}"
        shutil.copy2(source, target)
        return target.resolve()

    def _save_qimage(self, image: QImage) -> Path:
        target = self._image_dir / f"img_{uuid.uuid4().hex}.png"
        image.save(str(target), "PNG")
        return target.resolve()

    def _insert_image_html(self, image_path: Path) -> None:
        uri = image_path.resolve().as_uri()
        self.textCursor().insertHtml(
            f'<p><img src="{uri}" style="max-width: 100%; height: auto;" /></p>'
        )

