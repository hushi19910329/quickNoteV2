from __future__ import annotations


class BackupService:
    def export_markdown_bundle(self, _output_dir: str) -> str:
        raise NotImplementedError

    def import_markdown_bundle(self, _bundle_dir: str) -> None:
        raise NotImplementedError

