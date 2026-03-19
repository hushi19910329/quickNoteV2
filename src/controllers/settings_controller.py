from __future__ import annotations

from src.services.window_service import WindowService


class SettingsController:
    def __init__(self, window_service: WindowService) -> None:
        self._window_service = window_service

    def on_toggle_pin(self, enabled: bool) -> None:
        self._window_service.set_always_on_top(enabled)

    def on_change_transparency(self, alpha: float) -> None:
        self._window_service.set_transparency(alpha)

