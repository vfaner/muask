"""Small UI helpers shared by the About / update dialogs."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QWidget


def open_url(url: str) -> None:
    """Open ``url`` in the default browser, falling back to ``webbrowser``."""
    if not QDesktopServices.openUrl(QUrl(url)):
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass


class Card(QFrame):
    """White rounded card used by the About pages."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            "Card {"
            "  background:#ffffff;"
            "  border:1px solid #e6ebf2;"
            "  border-radius:10px;"
            "}"
        )
