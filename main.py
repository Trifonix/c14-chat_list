"""ChatList — сравнение ответов нескольких нейросетей."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from about_dialog import AboutDialog
from app_meta import APP_NAME
from db import AiModel, Database, Prompt, RequestLog, SavedResult, get_database
from export_utils import export_json, export_markdown
from logging_setup import setup_logging
from models import send_prompt
from prompt_improver import (
    PromptImprovementResult,
    get_improver_model,
    improve_prompt,
)
from session import ResultSession, SessionRow
from themes import apply_theme, get_stylesheet

STYLES = get_stylesheet("dark")


class MarkdownResponseDialog(QDialog):
    """Просмотр ответа нейросети в форматированном Markdown."""

    def __init__(
        self,
        model_name: str,
        response_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ответ — {model_name}")
        self.setMinimumSize(640, 480)
        self.resize(800, 560)

        layout = QVBoxLayout(self)
        header = QLabel(f"Модель: {model_name}")
        header.setStyleSheet("font-weight: 600;")
        layout.addWidget(header)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(response_text)
        layout.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class SendPromptWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        prompt_text: str,
        active_models: list[AiModel],
        timeout: float,
        db: Database,
    ) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.active_models = active_models
        self.timeout = timeout
        self.db = db

    def run(self) -> None:
        try:
            responses = send_prompt(
                self.prompt_text,
                self.active_models,
                timeout=self.timeout,
                db=self.db,
                on_progress=self.progress.emit,
            )
            self.finished.emit(responses)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImprovePromptWorker(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(
        self,
        prompt_text: str,
        model: AiModel,
        timeout: float,
        db: Database,
    ) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.model = model
        self.timeout = timeout
        self.db = db

    def run(self) -> None:
        try:
            self.status.emit("Улучшение промта…")
            result = improve_prompt(
                self.prompt_text, self.model, timeout=self.timeout, db=self.db
            )
            if isinstance(result, str):
                self.failed.emit(result)
            else:
                self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PromptImprovementDialog(QDialog):
    """Диалог с улучшенным промтом, альтернативами и подсказками по типам задач."""

    def __init__(
        self,
        result: PromptImprovementResult,
        on_substitute,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_substitute = on_substitute
        self.setWindowTitle("Улучшение промта")
        self.setMinimumSize(640, 520)
        self.resize(760, 620)
        self._build_ui(result)

    def _build_ui(self, result: PromptImprovementResult) -> None:
        layout = QVBoxLayout(self)

        original_group = QGroupBox("Исходный промт")
        original_edit = QTextEdit()
        original_edit.setReadOnly(True)
        original_edit.setPlainText(result.original)
        original_edit.setMaximumHeight(100)
        original_group_layout = QVBoxLayout(original_group)
        original_group_layout.addWidget(original_edit)
        layout.addWidget(original_group)

        improved_group = QGroupBox("Улучшенный")
        improved_layout = QVBoxLayout(improved_group)
        improved_edit = QTextEdit()
        improved_edit.setReadOnly(True)
        improved_edit.setPlainText(result.improved)
        improved_edit.setMinimumHeight(80)
        improved_layout.addWidget(improved_edit)
        substitute_btn = QPushButton("Подставить")
        substitute_btn.clicked.connect(lambda: self._substitute(result.improved))
        improved_layout.addWidget(substitute_btn)
        layout.addWidget(improved_group)

        if result.alternatives:
            alt_group = QGroupBox("Альтернативы")
            alt_layout = QVBoxLayout(alt_group)
            for index, alternative in enumerate(result.alternatives, start=1):
                row = QHBoxLayout()
                alt_edit = QTextEdit()
                alt_edit.setReadOnly(True)
                alt_edit.setPlainText(alternative)
                alt_edit.setMaximumHeight(72)
                row.addWidget(alt_edit, 1)
                btn = QPushButton("Подставить")
                btn.setObjectName("secondaryButton")
                btn.clicked.connect(lambda _checked=False, text=alternative: self._substitute(text))
                row.addWidget(btn)
                alt_layout.addLayout(row)
            layout.addWidget(alt_group)

        if result.model_hints:
            hints_group = QGroupBox("Под разные задачи")
            hints_group.setCheckable(True)
            hints_group.setChecked(False)
            hints_layout = QVBoxLayout(hints_group)
            labels = {"code": "Код", "analysis": "Анализ", "creative": "Креатив"}
            for key, hint_text in result.model_hints.items():
                title = labels.get(key, key)
                hints_layout.addWidget(QLabel(title))
                hint_row = QHBoxLayout()
                hint_edit = QTextEdit()
                hint_edit.setReadOnly(True)
                hint_edit.setPlainText(hint_text)
                hint_edit.setMaximumHeight(72)
                hint_row.addWidget(hint_edit, 1)
                btn = QPushButton("Подставить")
                btn.setObjectName("secondaryButton")
                btn.clicked.connect(lambda _checked=False, text=hint_text: self._substitute(text))
                hint_row.addWidget(btn)
                hints_layout.addLayout(hint_row)
            layout.addWidget(hints_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _substitute(self, text: str) -> None:
        self._on_substitute(text)
        self.accept()


class QueryTab(QWidget):
    def __init__(self, db: Database, session: ResultSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.session = session
        self._current_prompt_id: int | None = None
        self._worker: SendPromptWorker | None = None
        self._improve_worker: ImprovePromptWorker | None = None
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
        self.improve_btn = QPushButton("Улучшить промт")
        self.improve_btn.setObjectName("secondaryButton")
        self.improve_btn.clicked.connect(self._improve_prompt)
        self.save_btn = QPushButton("Сохранить выбранные")
        self.save_btn.setObjectName("secondaryButton")
        self.save_btn.clicked.connect(self._save_selected)
        self.clear_btn = QPushButton("Очистить результаты")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.clicked.connect(self._clear_session)
        self.export_md_btn = QPushButton("Экспорт MD")
        self.export_md_btn.setObjectName("secondaryButton")
        self.export_md_btn.clicked.connect(lambda: self._export("md"))
        self.export_json_btn = QPushButton("Экспорт JSON")
        self.export_json_btn.setObjectName("secondaryButton")
        self.export_json_btn.clicked.connect(lambda: self._export("json"))
        actions.addWidget(self.send_btn)
        actions.addWidget(self.improve_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.clear_btn)
        actions.addWidget(self.export_md_btn)
        actions.addWidget(self.export_json_btn)
        actions.addStretch()
        prompt_layout.addLayout(actions)
        layout.addWidget(prompt_group)

        self.status_label = QLabel("Готово к отправке")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Выбрать", "Модель", "Ответ", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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
        self.improve_btn.setDisabled(busy)
        self.save_btn.setDisabled(busy)
        self.status_label.setText(message)
        self.status_label.setProperty("busy", busy)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _improve_prompt(self) -> None:
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Промт", "Введите текст запроса.")
            return

        model = get_improver_model(self.db)
        if model is None:
            QMessageBox.warning(
                self,
                "Модели",
                "Нет активных моделей. Включите хотя бы одну на вкладке «Модели» "
                "или выберите модель в «Настройки».",
            )
            return

        self._set_busy(True, "Улучшение промта…")
        self._improve_worker = ImprovePromptWorker(
            prompt_text, model, self._get_timeout(), self.db
        )
        self._improve_worker.finished.connect(self._on_improve_finished)
        self._improve_worker.failed.connect(self._on_improve_failed)
        self._improve_worker.status.connect(
            lambda message: self._set_busy(True, message)
        )
        self._improve_worker.start()

    def _on_improve_finished(self, result: PromptImprovementResult) -> None:
        self._set_busy(False, "Улучшение завершено")
        dialog = PromptImprovementDialog(
            result,
            on_substitute=self.prompt_edit.setPlainText,
            parent=self,
        )
        dialog.exec()

    def _on_improve_failed(self, error: str) -> None:
        self._set_busy(False, "Ошибка улучшения промта")
        QMessageBox.critical(self, "Ошибка", error)

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

        self._worker = SendPromptWorker(
            prompt_text, active_models, self._get_timeout(), self.db
        )
        self._worker.finished.connect(self._on_send_finished)
        self._worker.failed.connect(self._on_send_failed)
        self._worker.progress.connect(self._on_send_progress)
        self._worker.start()

    def _on_send_progress(self, message: str) -> None:
        self._set_busy(True, message)

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

            response_edit = QTextEdit()
            response_edit.setReadOnly(True)
            response_edit.setPlainText(row.response_text)
            response_edit.setMinimumHeight(90)
            response_edit.setMaximumHeight(160)
            self.results_table.setCellWidget(index, 2, response_edit)

            open_btn = QPushButton("Открыть")
            open_btn.setObjectName("secondaryButton")
            open_btn.clicked.connect(lambda _checked=False, i=index: self._open_response(i))
            open_wrapper = QWidget()
            open_layout = QHBoxLayout(open_wrapper)
            open_layout.addWidget(open_btn)
            open_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            open_layout.setContentsMargins(4, 4, 4, 4)
            self.results_table.setCellWidget(index, 3, open_wrapper)

            self.results_table.setRowHeight(index, 100)

    def _open_response(self, index: int) -> None:
        rows = self.session.rows
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        dialog = MarkdownResponseDialog(row.model_name, row.response_text, self)
        dialog.exec()

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

    def _export(self, fmt: str) -> None:
        rows = self.session.rows
        if not rows:
            QMessageBox.information(self, "Экспорт", "Нет результатов для экспорта.")
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        suffix = "md" if fmt == "md" else "json"
        filter_map = {
            "md": "Markdown (*.md)",
            "json": "JSON (*.json)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить экспорт",
            f"chatlist_export.{suffix}",
            filter_map[fmt],
        )
        if not path:
            return

        content = (
            export_markdown(prompt_text, rows)
            if fmt == "md"
            else export_json(prompt_text, rows)
        )
        Path(path).write_text(content, encoding="utf-8")
        QMessageBox.information(self, "Экспорт", f"Файл сохранён:\n{path}")


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
        self.type_combo.addItems(["openrouter", "openai", "deepseek", "groq"])
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

        export_md_btn = QPushButton("Экспорт MD")
        export_md_btn.setObjectName("secondaryButton")
        export_md_btn.clicked.connect(lambda: self._export_saved("md"))
        export_json_btn = QPushButton("Экспорт JSON")
        export_json_btn.setObjectName("secondaryButton")
        export_json_btn.clicked.connect(lambda: self._export_saved("json"))
        delete_btn = QPushButton("Удалить выбранный")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_selected)
        row = QHBoxLayout()
        row.addWidget(export_md_btn)
        row.addWidget(export_json_btn)
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

    def _export_saved(self, fmt: str) -> None:
        results = self.db.list_results(
            search=self.search_edit.text(),
            sort_by=self.sort_combo.currentText(),
            sort_dir=self.dir_combo.currentText(),
        )
        if not results:
            QMessageBox.information(self, "Экспорт", "Нет сохранённых результатов.")
            return

        prompt_text = results[0].prompt_text or "Сохранённые результаты"
        rows = [
            SessionRow(
                model_id=result.model_id,
                model_name=result.model_name or "",
                response_text=result.response_text,
                selected=True,
            )
            for result in results
        ]
        suffix = "md" if fmt == "md" else "json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить экспорт",
            f"chatlist_saved.{suffix}",
            "Markdown (*.md)" if fmt == "md" else "JSON (*.json)",
        )
        if not path:
            return
        content = (
            export_markdown(prompt_text, rows)
            if fmt == "md"
            else export_json(prompt_text, rows)
        )
        Path(path).write_text(content, encoding="utf-8")
        QMessageBox.information(self, "Экспорт", f"Файл сохранён:\n{path}")


class LogsTab(QWidget):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по модели, промту, статусу...")
        self.search_edit.textChanged.connect(self.reload)
        filters.addWidget(self.search_edit, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["created_at", "model_name", "status", "duration_ms", "id"])
        self.sort_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(QLabel("Сортировка:"))
        filters.addWidget(self.sort_combo)

        self.dir_combo = QComboBox()
        self.dir_combo.addItems(["DESC", "ASC"])
        self.dir_combo.currentTextChanged.connect(self.reload)
        filters.addWidget(self.dir_combo)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Модель", "Статус", "мс", "Промт", "Ошибка / ответ"]
        )
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        info = QLabel("Логи также пишутся в файл chatlist.log")
        info.setObjectName("mutedLabel")
        layout.addWidget(info)

        clear_btn = QPushButton("Очистить логи")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._clear_logs)
        row = QHBoxLayout()
        row.addWidget(clear_btn)
        row.addStretch()
        layout.addLayout(row)

    def reload(self) -> None:
        logs = self.db.list_request_logs(
            search=self.search_edit.text(),
            sort_by=self.sort_combo.currentText(),
            sort_dir=self.dir_combo.currentText(),
        )
        self.table.setRowCount(len(logs))
        for index, log in enumerate(logs):
            self._set_row(index, log)

    def _set_row(self, index: int, log: RequestLog) -> None:
        preview = log.error_message or log.response_preview or ""
        values = [
            str(log.id),
            log.created_at,
            log.model_name,
            log.status,
            str(log.duration_ms or ""),
            log.prompt_text[:120],
            preview[:200],
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, col, item)

    def _clear_logs(self) -> None:
        if QMessageBox.question(
            self, "Логи", "Очистить все записи логов запросов?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.db.clear_request_logs()
        self.reload()


class SettingsTab(QWidget):
    def __init__(
        self,
        db: Database,
        on_settings_saved=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self._on_settings_saved = on_settings_saved
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

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setSuffix(" pt")
        form.addRow("Размер шрифта:", self.font_spin)

        self.tags_edit = QLineEdit()
        form.addRow("Теги по умолчанию:", self.tags_edit)

        self.improver_model_combo = QComboBox()
        form.addRow("Модель для улучшения промта:", self.improver_model_combo)

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
        self.font_spin.setValue(int(settings.get("ui_font_size", "10") or 10))
        self.tags_edit.setText(settings.get("default_tags", ""))
        self.db_path_label.setText(settings.get("db_path", "chatlist.db"))

        saved_id = settings.get("prompt_improver_model_id")
        self.improver_model_combo.blockSignals(True)
        self.improver_model_combo.clear()
        active_models = self.db.list_models(active_only=True)
        selected_index = 0
        for index, model in enumerate(active_models):
            self.improver_model_combo.addItem(model.name, model.id)
            if saved_id and str(model.id) == saved_id:
                selected_index = index
        if active_models:
            self.improver_model_combo.setCurrentIndex(selected_index)
        self.improver_model_combo.blockSignals(False)

    def _save(self) -> None:
        self.db.set_setting("request_timeout", str(self.timeout_spin.value()))
        self.db.set_setting("theme", self.theme_combo.currentText())
        self.db.set_setting("ui_font_size", str(self.font_spin.value()))
        self.db.set_setting("default_tags", self.tags_edit.text().strip())
        model_id = self.improver_model_combo.currentData()
        if model_id is not None:
            self.db.set_setting("prompt_improver_model_id", str(model_id))
        if self._on_settings_saved:
            self._on_settings_saved()
        QMessageBox.information(self, "Настройки", "Настройки сохранены.")


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.session = ResultSession()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon("app.ico"))
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)
        self._build_ui()
        self._build_menu()

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("Справка")
        about_action = help_menu.addAction("О программе…")
        about_action.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        dialog = AboutDialog(self)
        dialog.exec()

    def apply_current_theme(self, app: QApplication) -> None:
        settings = self.db.list_settings()
        theme = settings.get("theme", "dark") or "dark"
        try:
            font_size = int(settings.get("ui_font_size", "10") or 10)
        except ValueError:
            font_size = 10
        font_size = max(8, min(24, font_size))
        apply_theme(app, self, theme, font_size)

    def _on_settings_saved(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            self.apply_current_theme(app)

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        self.query_tab = QueryTab(self.db, self.session)
        self.prompts_tab = PromptsTab(self.db)
        self.models_tab = ModelsTab(self.db)
        self.results_tab = ResultsTab(self.db)
        self.logs_tab = LogsTab(self.db)
        self.settings_tab = SettingsTab(self.db, on_settings_saved=self._on_settings_saved)

        tabs.addTab(self.query_tab, "Запрос")
        tabs.addTab(self.prompts_tab, "Промты")
        tabs.addTab(self.models_tab, "Модели")
        tabs.addTab(self.results_tab, "Результаты")
        tabs.addTab(self.logs_tab, "Логи")
        tabs.addTab(self.settings_tab, "Настройки")
        tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(tabs)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.centralWidget().widget(index)
        if hasattr(widget, "reload"):
            widget.reload()


def main() -> None:
    setup_logging()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app.ico"))

    database = get_database()
    window = MainWindow(database)
    window.apply_current_theme(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
