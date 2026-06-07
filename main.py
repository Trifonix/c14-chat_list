import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

MESSAGE = "Минимальная программа на Python"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Минимальная программа")
        self.setMinimumSize(480, 320)
        self.resize(520, 360)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Добро пожаловать")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Нажмите кнопку, чтобы увидеть сообщение")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel(" ")
        self.message_label.setObjectName("message")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumHeight(48)

        button = QPushButton("Нажми меня")
        button.setObjectName("actionButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(48)
        button.setMinimumWidth(180)
        button.clicked.connect(self.show_message)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(button)
        button_row.addStretch()

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.message_label)
        layout.addLayout(button_row)
        layout.addStretch()

        self._apply_styles()

    def show_message(self) -> None:
        self.message_label.setText(MESSAGE)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0f172a;
            }
            QWidget {
                background-color: transparent;
                color: #e2e8f0;
                font-family: "Segoe UI", "Inter", sans-serif;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: 700;
                color: #f8fafc;
            }
            QLabel#subtitle {
                font-size: 14px;
                color: #94a3b8;
            }
            QLabel#message {
                font-size: 18px;
                font-weight: 600;
                color: #38bdf8;
                padding: 16px 20px;
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QPushButton#actionButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 12px;
                padding: 12px 28px;
            }
            QPushButton#actionButton:hover {
                background-color: #2563eb;
            }
            QPushButton#actionButton:pressed {
                background-color: #1d4ed8;
            }
            """
        )


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
