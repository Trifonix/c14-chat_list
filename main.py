"""ChatList — сравнение ответов нескольких нейросетей."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import AiModel, Database, Prompt, SavedResult, get_database
from models import send_prompt
from session import ResultSession

STYLES = """
QMainWindow, QDialog {
    background-color: #0f172a;
}
QWidget {
    background-color: transparent;
    color: #e2e8f0;
    font-family: "Segoe UI", sans-serif;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
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
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px;
}
QComboBox::drop-down {
    border: none;
}
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #475569;
    color: #94a3b8;
}
QPushButton#secondaryButton {
    background-color: #334155;
}
QPushButton#secondaryButton:hover {
    background-color: #475569;
}
QPushButton#dangerButton {
    background-color: #dc2626;
}
QPushButton#dangerButton:hover {
    background-color: #b91c1c;
}
QTableWidget {
    background-color: #0f172a;
    alternate-background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
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
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
"""


class SendPromptWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(
        self,
        prompt_text: str,
        active_models: list[AiModel],
        timeout: float,
    ) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.active_models = active_models
        self.timeout = timeout

    def run(self) -> None:
        try:
            responses = send_prompt(
                self.prompt_text,
                self.active_models,
                timeout=self.timeout,
            )
            self.finished.emit(responses)
        except Exception as exc:
            self.failed.emit(str(exc))


class QueryTab(QWidget):
    def __init__(self, db: Database, session: ResultSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.session = session
        self._current_prompt_id: int | None = None
        self._worker: SendPromptWorker | None = None
        self._build_ui()
        self._reload_saved_prompts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        prompt_group = QGroupBox("Промт")
        prompt_layout = QVBoxLayout(prompt_group)

        saved_row = QHBoxLayout()
        saved_row.addWidget(QLabel("Сохранённые:"))
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(300)
        self.saved_combo.currentIndexChanged.connect(self._on_saved_prompt_selected)
        saved_row.addWidget(self.saved_combo, 1)
        self.refresh_prompts_btn = QPushButton("Обновить")
        self.refresh_prompts_btn.setObjectName("secondaryButton")
        self.refresh_prompts_btn.clicked.connect(self._reload_saved_prompts)
        saved_row.addWidget(self.refresh_prompts_btn)
        prompt_layout.addLayout(saved_row)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса...")
        self.prompt_edit.setMinimumHeight(100)
        self.prompt_edit.textChanged.connect(self._on_prompt_text_changed)
        prompt_layout.addWidget(self.prompt_edit)

        actions = QHBoxLayout()
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self._send_prompt)
        self.save_btn = QPushButton("Сохранить выбранные")
        self.save_btn.setObjectName("secondaryButton")
        self.save_btn.clicked.connect(self._save_selected)
        self.clear_btn = QPushButton("Очистить результаты")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.clicked.connect(self._clear_session)
        actions.addWidget(self.send_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.clear_btn)
        actions.addStretch()
        prompt_layout.addLayout(actions)
        layout.addWidget(prompt_group)

        self.status_label = QLabel("Готово к отправке")
        self.status_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.status_label)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Выбрать", "Модель", "Ответ"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        layout.addWidget(self.results_table, 1)

    def _reload_saved_prompts(self) -> None:
        self.saved_combo.blockSignals(True)
        self.saved_combo.clear()
        self.saved_combo.addItem("— новый промт —", None)
        for prompt in self.db.list_prompts():
            label = f"[{prompt.created_at[:16]}] {prompt.prompt_text[:60]}"
            self.saved_combo.addItem(label, prompt.id)
        self.saved_combo.blockSignals(False)

    def _on_saved_prompt_selected(self, index: int) -> None:
        if index < 0:
            return
        prompt_id = self.saved_combo.currentData()
        if prompt_id is None:
            self._current_prompt_id = None
            return
        prompt = self.db.get_prompt(int(prompt_id))
        if prompt:
            self._current_prompt_id = prompt.id
            self.prompt_edit.blockSignals(True)
            self.prompt_edit.setPlainText(prompt.prompt_text)
            self.prompt_edit.blockSignals(False)
            self.session.clear()
            self._refresh_results_table()

    def _on_prompt_text_changed(self) -> None:
        if self.saved_combo.currentData() is not None:
            current_id = self.saved_combo.currentData()
            prompt = self.db.get_prompt(int(current_id)) if current_id else None
            if prompt and prompt.prompt_text != self.prompt_edit.toPlainText().strip():
                self.saved_combo.blockSignals(True)
                self.saved_combo.setCurrentIndex(0)
                self.saved_combo.blockSignals(False)
                self._current_prompt_id = None
        self.session.clear()
        self._refresh_results_table()

    def _get_timeout(self) -> float:
        raw = self.db.get_setting("request_timeout", "60") or "60"
        try:
            return float(raw)
        except ValueError:
            return 60.0

    def _set_busy(self, busy: bool, message: str) -> None:
        self.send_btn.setDisabled(busy)
        self.save_btn.setDisabled(busy)
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "color: #38bdf8;" if busy else "color: #94a3b8;"
        )

    def _send_prompt(self) -> None:
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Промт", "Введите текст запроса.")
            return

        active_models = self.db.list_models(active_only=True)
        if not active_models:
            QMessageBox.warning(
                self,
                "Модели",
                "Нет активных моделей. Включите хотя бы одну на вкладке «Модели».",
            )
            return

        self.session.clear()
        self._refresh_results_table()
        self._set_busy(True, "Отправка запросов в нейросети...")

        self._worker = SendPromptWorker(prompt_text, active_models, self._get_timeout())
        self._worker.finished.connect(self._on_send_finished)
        self._worker.failed.connect(self._on_send_failed)
        self._worker.start()

    def _on_send_finished(self, responses: list) -> None:
        self.session.load_from_responses(responses)
        self._refresh_results_table()
        self._set_busy(False, f"Получено ответов: {len(responses)}")

    def _on_send_failed(self, error: str) -> None:
        self._set_busy(False, "Ошибка отправки")
        QMessageBox.critical(self, "Ошибка", error)

    def _refresh_results_table(self) -> None:
        rows = self.session.rows
        self.results_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            checkbox = QCheckBox()
            checkbox.setChecked(row.selected)
            checkbox.stateChanged.connect(
                lambda state, i=index: self._on_checkbox_changed(i, state)
            )
            wrapper = QWidget()
            wrapper_layout = QHBoxLayout(wrapper)
            wrapper_layout.addWidget(checkbox)
            wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            self.results_table.setCellWidget(index, 0, wrapper)

            model_item = QTableWidgetItem(row.model_name)
            model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(index, 1, model_item)

            response_item = QTableWidgetItem(row.response_text)
            response_item.setFlags(response_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(index, 2, response_item)

    def _on_checkbox_changed(self, index: int, state: int) -> None:
        self.session.set_selected(index, state == int(Qt.CheckState.Checked.value))

    def _ensure_prompt_id(self) -> int | None:
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            return None
        if self._current_prompt_id is not None:
            prompt = self.db.get_prompt(self._current_prompt_id)
            if prompt and prompt.prompt_text == prompt_text:
                return self._current_prompt_id
        default_tags = self.db.get_setting("default_tags", "") or ""
        prompt_id = self.db.add_prompt(prompt_text, default_tags or None)
        self._current_prompt_id = prompt_id
        self._reload_saved_prompts()
        for i in range(self.saved_combo.count()):
            if self.saved_combo.itemData(i) == prompt_id:
                self.saved_combo.setCurrentIndex(i)
                break
        return prompt_id

    def _save_selected(self) -> None:
        selected = self.session.get_selected_rows()
        if not selected:
            QMessageBox.information(self, "Сохранение", "Отметьте хотя бы одну строку.")
            return

        prompt_id = self._ensure_prompt_id()
        if prompt_id is None:
            QMessageBox.warning(self, "Сохранение", "Нет промта для сохранения.")
            return

        self.db.save_results(prompt_id, self.session.selected_for_db())
        self.session.clear()
        self._refresh_results_table()
        self.status_label.setText(f"Сохранено строк: {len(selected)}")
        QMessageBox.information(self, "Сохранение", f"Сохранено ответов: {len(selected)}")

    def _clear_session(self) -> None:
        self.session.clear()
        self._refresh_results_table()
        self.status_label.setText("Временная таблица очищена")


class PromptsTab(QWidget):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по тексту и тегам...")
        self.search_edit.textChanged.connect(self.reload)
        filters.addWidget(self.search_edit, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["created_at", "prompt_text", "tags", "id"])
        self.sort_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(QLabel("Сортировка:"))
        filters.addWidget(self.sort_combo)

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["DESC", "ASC"])
        self.dir_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(self.dir_combo)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        delete_btn = QPushButton("Удалить выбранный")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(delete_btn)
        actions.addStretch()
        layout.addLayout(actions)

    def reload(self) -> None:
        prompts = self.db.list_prompts(
            search=self.search_edit.text(),
            sort_by=self.sort_combo.currentText(),
            sort_dir=self.dir_combo.currentText(),
        )
        self.table.setRowCount(len(prompts))
        for row_index, prompt in enumerate(prompts):
            self._set_row(row_index, prompt)

    def _set_row(self, index: int, prompt: Prompt) -> None:
        for col, value in enumerate(
            [str(prompt.id), prompt.created_at, prompt.prompt_text, prompt.tags or ""]
        ):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, col, item)

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Промты", "Выберите строку для удаления.")
            return
        prompt_id = int(self.table.item(row, 0).text())
        if QMessageBox.question(
            self,
            "Удаление",
            f"Удалить промт #{prompt_id} и связанные результаты?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_prompt(prompt_id)
        self.reload()


class ModelFormDialog(QWidget):
    """Встроенная форма редактирования модели на вкладке."""

    def __init__(self, db: Database, on_saved, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.on_saved = on_saved
        self._editing_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.url_edit = QLineEdit()
        self.api_id_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["openai", "deepseek", "groq"])
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(True)

        layout.addRow("Имя модели (API):", self.name_edit)
        layout.addRow("URL API:", self.url_edit)
        layout.addRow("Переменная .env:", self.api_id_edit)
        layout.addRow("Тип:", self.type_combo)
        layout.addRow("", self.active_check)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self._save)
        self.new_btn = QPushButton("Новая")
        self.new_btn.setObjectName("secondaryButton")
        self.new_btn.clicked.connect(self.clear_form)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.new_btn)
        buttons.addStretch()
        layout.addRow(buttons)

    def clear_form(self) -> None:
        self._editing_id = None
        self.name_edit.clear()
        self.url_edit.clear()
        self.api_id_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.active_check.setChecked(True)

    def load_model(self, model: AiModel) -> None:
        self._editing_id = model.id
        self.name_edit.setText(model.name)
        self.url_edit.setText(model.api_url)
        self.api_id_edit.setText(model.api_id)
        index = self.type_combo.findText(model.model_type)
        self.type_combo.setCurrentIndex(index if index >= 0 else 0)
        self.active_check.setChecked(model.is_active)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        api_id = self.api_id_edit.text().strip()
        if not name or not url or not api_id:
            QMessageBox.warning(self, "Модель", "Заполните все обязательные поля.")
            return
        model_type = self.type_combo.currentText()
        is_active = self.active_check.isChecked()
        try:
            if self._editing_id is None:
                self.db.add_model(name, url, api_id, is_active, model_type)
            else:
                self.db.update_model(
                    self._editing_id, name, url, api_id, is_active, model_type
                )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.on_saved()
        self.clear_form()
        QMessageBox.information(self, "Модель", "Сохранено.")


class ModelsTab(QWidget):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.textChanged.connect(self.reload)
        filters.addWidget(self.search_edit, 1)
        left.addLayout(filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "URL", "Переменная", "Тип", "Активна"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection)
        left.addWidget(self.table, 1)

        actions = QHBoxLayout()
        toggle_btn = QPushButton("Вкл/Выкл")
        toggle_btn.setObjectName("secondaryButton")
        toggle_btn.clicked.connect(self._toggle_active)
        delete_btn = QPushButton("Удалить")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(toggle_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        left.addLayout(actions)
        layout.addLayout(left, 2)

        self.form = ModelFormDialog(self.db, self.reload)
        layout.addWidget(self.form, 1)

    def reload(self) -> None:
        models = self.db.list_models(search=self.search_edit.text())
        self.table.setRowCount(len(models))
        for index, model in enumerate(models):
            values = [
                str(model.id),
                model.name,
                model.api_url,
                model.api_id,
                model.model_type,
                "Да" if model.is_active else "Нет",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(index, col, item)

    def _selected_model_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def _on_selection(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            return
        model = self.db.get_model(model_id)
        if model:
            self.form.load_model(model)

    def _toggle_active(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите модель.")
            return
        self.db.toggle_model_active(model_id)
        self.reload()

    def _delete_selected(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите модель.")
            return
        if QMessageBox.question(
            self, "Удаление", f"Удалить модель #{model_id}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_model(model_id)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.form.clear_form()
        self.reload()


class ResultsTab(QWidget):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по ответу, промту, модели...")
        self.search_edit.textChanged.connect(self.reload)
        filters.addWidget(self.search_edit, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["saved_at", "response_text", "prompt_id", "model_id", "id"])
        self.sort_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(QLabel("Сортировка:"))
        filters.addWidget(self.sort_combo)

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["DESC", "ASC"])
        self.dir_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(self.dir_combo)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Промт", "Модель", "Ответ", "prompt_id"]
        )
        self.table.setColumnHidden(5, True)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        delete_btn = QPushButton("Удалить выбранный")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        row = QHBoxLayout()
        row.addWidget(delete_btn)
        row.addStretch()
        layout.addLayout(row)

    def reload(self) -> None:
        results = self.db.list_results(
            search=self.search_edit.text(),
            sort_by=self.sort_combo.currentText(),
            sort_dir=self.dir_combo.currentText(),
        )
        self.table.setRowCount(len(results))
        for index, result in enumerate(results):
            self._set_row(index, result)

    def _set_row(self, index: int, result: SavedResult) -> None:
        values = [
            str(result.id),
            result.saved_at,
            result.prompt_text or "",
            result.model_name or "",
            result.response_text,
            str(result.prompt_id),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, col, item)

    def _delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Результаты", "Выберите строку.")
            return
        result_id = int(self.table.item(row, 0).text())
        if QMessageBox.question(
            self, "Удаление", f"Удалить результат #{result_id}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_result(result_id)
        self.reload()


class SettingsTab(QWidget):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(" сек")
        form.addRow("Таймаут запроса:", self.timeout_spin)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        form.addRow("Тема:", self.theme_combo)

        self.tags_edit = QLineEdit()
        form.addRow("Теги по умолчанию:", self.tags_edit)

        self.db_path_label = QLabel()
        form.addRow("Файл БД:", self.db_path_label)

        layout.addLayout(form)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()

    def reload(self) -> None:
        settings = self.db.list_settings()
        self.timeout_spin.setValue(int(settings.get("request_timeout", "60") or 60))
        theme = settings.get("theme", "dark")
        index = self.theme_combo.findText(theme)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self.tags_edit.setText(settings.get("default_tags", ""))
        self.db_path_label.setText(settings.get("db_path", "chatlist.db"))

    def _save(self) -> None:
        self.db.set_setting("request_timeout", str(self.timeout_spin.value()))
        self.db.set_setting("theme", self.theme_combo.currentText())
        self.db.set_setting("default_tags", self.tags_edit.text().strip())
        QMessageBox.information(self, "Настройки", "Настройки сохранены.")


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.session = ResultSession()
        self.setWindowTitle("ChatList")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)
        self._build_ui()
        self.setStyleSheet(STYLES)

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        self.query_tab = QueryTab(self.db, self.session)
        self.prompts_tab = PromptsTab(self.db)
        self.models_tab = ModelsTab(self.db)
        self.results_tab = ResultsTab(self.db)
        self.settings_tab = SettingsTab(self.db)

        tabs.addTab(self.query_tab, "Запрос")
        tabs.addTab(self.prompts_tab, "Промты")
        tabs.addTab(self.models_tab, "Модели")
        tabs.addTab(self.results_tab, "Результаты")
        tabs.addTab(self.settings_tab, "Настройки")
        tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(tabs)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.centralWidget().widget(index)
        if hasattr(widget, "reload"):
            widget.reload()


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    database = get_database()
    window = MainWindow(database)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
