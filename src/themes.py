"""Темы оформления и применение стилей ChatList."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow

STYLES_DARK = """
QMainWindow, QDialog {
    background-color: #0f172a;
}
QWidget {
    background-color: transparent;
    color: #e2e8f0;
    font-family: "Segoe UI", sans-serif;
}
QLabel {
    color: #e2e8f0;
}
QLabel#statusLabel {
    color: #cbd5e1;
}
QLabel#statusLabel[busy="true"] {
    color: #7dd3fc;
}
QLabel#mutedLabel {
    color: #cbd5e1;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #cbd5e1;
    padding: 10px 18px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background-color: #334155;
    color: #f8fafc;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #0f172a;
    color: #e2e8f0;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #1e293b;
    color: #94a3b8;
    border-color: #334155;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #475569;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    outline: none;
}
QTextBrowser {
    background-color: #0f172a;
    color: #e2e8f0;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 12px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #475569;
    color: #cbd5e1;
}
QPushButton#secondaryButton {
    background-color: #334155;
    color: #f8fafc;
}
QPushButton#secondaryButton:hover {
    background-color: #475569;
    color: #ffffff;
}
QPushButton#secondaryButton:disabled {
    background-color: #1e293b;
    color: #94a3b8;
}
QPushButton#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
}
QPushButton#dangerButton:hover {
    background-color: #b91c1c;
    color: #ffffff;
}
QCheckBox {
    color: #e2e8f0;
    spacing: 8px;
}
QCheckBox:disabled {
    color: #64748b;
}
QTableWidget {
    background-color: #0f172a;
    alternate-background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QTableWidget::item {
    color: #e2e8f0;
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #334155;
    color: #f8fafc;
    padding: 8px;
    border: none;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #f1f5f9;
}
QMenuBar {
    background-color: #0f172a;
    color: #e2e8f0;
}
QMenuBar::item:selected {
    background-color: #334155;
}
QMenu {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #475569;
}
QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""

STYLES_LIGHT = """
QMainWindow, QDialog {
    background-color: #f1f5f9;
}
QWidget {
    background-color: transparent;
    color: #0f172a;
    font-family: "Segoe UI", sans-serif;
}
QLabel {
    color: #0f172a;
}
QLabel#statusLabel {
    color: #475569;
}
QLabel#statusLabel[busy="true"] {
    color: #0284c7;
}
QLabel#mutedLabel {
    color: #64748b;
}
QTabWidget::pane {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #e2e8f0;
    color: #475569;
    padding: 10px 18px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #cbd5e1;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    outline: none;
}
QTextBrowser {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #94a3b8;
    border-radius: 8px;
    padding: 12px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #cbd5e1;
    color: #64748b;
}
QPushButton#secondaryButton {
    background-color: #e2e8f0;
    color: #0f172a;
}
QPushButton#secondaryButton:hover {
    background-color: #cbd5e1;
    color: #0f172a;
}
QPushButton#secondaryButton:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
}
QPushButton#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
}
QPushButton#dangerButton:hover {
    background-color: #b91c1c;
    color: #ffffff;
}
QCheckBox {
    color: #0f172a;
    spacing: 8px;
}
QCheckBox:disabled {
    color: #94a3b8;
}
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    gridline-color: #e2e8f0;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QTableWidget::item {
    color: #0f172a;
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #e2e8f0;
    color: #0f172a;
    padding: 8px;
    border: none;
}
QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #0f172a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1e293b;
}
QMenuBar {
    background-color: #f1f5f9;
    color: #0f172a;
}
QMenuBar::item:selected {
    background-color: #e2e8f0;
}
QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
}
QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""

_PALETTE_DARK = {
    QPalette.ColorRole.Window: "#0f172a",
    QPalette.ColorRole.WindowText: "#e2e8f0",
    QPalette.ColorRole.Base: "#0f172a",
    QPalette.ColorRole.AlternateBase: "#1e293b",
    QPalette.ColorRole.Text: "#e2e8f0",
    QPalette.ColorRole.Button: "#2563eb",
    QPalette.ColorRole.ButtonText: "#ffffff",
    QPalette.ColorRole.Highlight: "#2563eb",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.PlaceholderText: "#94a3b8",
}

_PALETTE_LIGHT = {
    QPalette.ColorRole.Window: "#f1f5f9",
    QPalette.ColorRole.WindowText: "#0f172a",
    QPalette.ColorRole.Base: "#ffffff",
    QPalette.ColorRole.AlternateBase: "#f8fafc",
    QPalette.ColorRole.Text: "#0f172a",
    QPalette.ColorRole.Button: "#2563eb",
    QPalette.ColorRole.ButtonText: "#ffffff",
    QPalette.ColorRole.Highlight: "#2563eb",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.PlaceholderText: "#64748b",
}

_DISABLED_TEXT_DARK = "#94a3b8"
_DISABLED_TEXT_LIGHT = "#94a3b8"
_DISABLED_BUTTON_TEXT_DARK = "#cbd5e1"
_DISABLED_BUTTON_TEXT_LIGHT = "#64748b"
_DISABLED_PLACEHOLDER_DARK = "#64748b"
_DISABLED_PLACEHOLDER_LIGHT = "#94a3b8"


def get_stylesheet(theme: str) -> str:
    if theme == "light":
        return STYLES_LIGHT
    return STYLES_DARK


def apply_palette(app: QApplication, theme: str = "dark") -> None:
    """Глобальная палитра для placeholder, выделения и системных виджетов."""
    colors = _PALETTE_LIGHT if theme == "light" else _PALETTE_DARK
    disabled_text = _DISABLED_TEXT_LIGHT if theme == "light" else _DISABLED_TEXT_DARK
    disabled_button = (
        _DISABLED_BUTTON_TEXT_LIGHT if theme == "light" else _DISABLED_BUTTON_TEXT_DARK
    )
    disabled_placeholder = (
        _DISABLED_PLACEHOLDER_LIGHT if theme == "light" else _DISABLED_PLACEHOLDER_DARK
    )

    palette = QPalette()
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(disabled_text)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(disabled_button),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.PlaceholderText,
        QColor(disabled_placeholder),
    )
    app.setPalette(palette)


def apply_theme(
    app: QApplication,
    main_window: QMainWindow,
    theme: str,
    font_size: int,
) -> None:
    """Применяет тему, шрифт и палитру к приложению и главному окну."""
    app.setFont(QFont("Segoe UI", font_size))
    apply_palette(app, theme)
    main_window.setStyleSheet(get_stylesheet(theme))
