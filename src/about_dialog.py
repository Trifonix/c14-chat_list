"""Диалог «О программе»."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from app_meta import (
    APP_DESCRIPTION,
    APP_LICENSE,
    APP_NAME,
    APP_STACK,
    APP_VERSION,
)
from paths import DOCS_DIR


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"О программе — {APP_NAME}")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        version = QLabel(f"Версия {APP_VERSION}")
        version.setObjectName("mutedLabel")
        layout.addWidget(version)

        description = QLabel(APP_DESCRIPTION)
        description.setWordWrap(True)
        layout.addWidget(description)

        stack = QLabel(f"<b>Стек:</b> {APP_STACK}")
        stack.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(stack)

        docs_path = (DOCS_DIR / "PROJECT.md").as_uri()
        docs = QLabel(
            f'<b>Документация:</b> <a href="{docs_path}">docs/PROJECT.md</a>'
        )
        docs.setTextFormat(Qt.TextFormat.RichText)
        docs.setOpenExternalLinks(True)
        docs.setWordWrap(True)
        layout.addWidget(docs)

        license_label = QLabel(f"<b>Лицензия:</b> {APP_LICENSE}")
        license_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(license_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
