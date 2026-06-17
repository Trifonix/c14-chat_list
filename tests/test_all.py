"""
Единый набор тестов ChatList.

Запуск из корня проекта:
  pytest -c config/pytest.ini
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from db import AiModel, Database, get_database
from export_utils import export_json, export_markdown
from logging_setup import setup_logging
from models import (
    PromptResponse,
    build_chat_payload,
    build_headers,
    call_model,
    extract_chat_response,
    get_api_key,
    send_prompt,
)
from network import post_json
from paths import DATA_DIR
from prompt_improver import (
    PromptImprovementResult,
    get_improver_model,
    improve_prompt,
    parse_improvement_response,
)
from session import ResultSession, SessionRow


class TestDatabase:
    def test_init_creates_schema_and_seeds(self, temp_db: Database) -> None:
        settings = temp_db.list_settings()
        assert settings["request_timeout"] == "60"
        assert settings["theme"] == "dark"
        assert settings["ui_font_size"] == "10"
        assert "prompt_improver_model_id" in settings
        assert len(temp_db.list_models()) >= 3

    def test_prompt_crud(self, temp_db: Database) -> None:
        pid = temp_db.add_prompt("  Текст промта  ", "tag1")
        prompt = temp_db.get_prompt(pid)
        assert prompt is not None
        assert prompt.prompt_text == "Текст промта"

        temp_db.update_prompt(pid, "Новый текст", "tag2")
        updated = temp_db.get_prompt(pid)
        assert updated is not None
        assert updated.prompt_text == "Новый текст"

        temp_db.delete_prompt(pid)
        assert temp_db.get_prompt(pid) is None

    def test_list_prompts_search_and_sort(self, temp_db: Database) -> None:
        temp_db.add_prompt("Python tutorial", "python")
        temp_db.add_prompt("JavaScript basics", "js")
        assert len(temp_db.list_prompts(search="python")) == 1

    def test_model_crud_and_toggle(self, temp_db: Database) -> None:
        mid = temp_db.add_model("custom/model", "https://api.test/v1", "CUSTOM_KEY", True, "groq")
        model = temp_db.get_model(mid)
        assert model is not None
        assert temp_db.toggle_model_active(mid) is False
        temp_db.delete_model(mid)
        assert temp_db.get_model(mid) is None

    def test_toggle_unknown_model_raises(self, temp_db: Database) -> None:
        with pytest.raises(ValueError, match="не найдена"):
            temp_db.toggle_model_active(99999)

    def test_results_save_list_delete(self, temp_db: Database, sample_model: AiModel) -> None:
        prompt_id = temp_db.add_prompt("Промт")
        temp_db.save_results(prompt_id, [(sample_model.id, "ответ 1")])
        results = temp_db.list_results()
        assert len(results) == 1
        temp_db.delete_result(results[0].id)
        assert temp_db.list_results() == []

    def test_prompt_delete_cascades_results(
        self, temp_db: Database, sample_model: AiModel
    ) -> None:
        prompt_id = temp_db.add_prompt("каскад")
        temp_db.save_results(prompt_id, [(sample_model.id, "x")])
        temp_db.delete_prompt(prompt_id)
        assert temp_db.list_results() == []

    def test_settings(self, temp_db: Database) -> None:
        temp_db.set_setting("custom_key", "value")
        assert temp_db.get_setting("custom_key") == "value"

    def test_ui_font_size_round_trip(self, temp_db: Database) -> None:
        temp_db.set_setting("ui_font_size", "12")
        assert temp_db.get_setting("ui_font_size") == "12"

    def test_theme_persisted(self, temp_db: Database) -> None:
        temp_db.set_setting("theme", "light")
        assert temp_db.get_setting("theme") == "light"

    def test_request_logs(self, temp_db: Database, sample_model: AiModel) -> None:
        temp_db.log_request(sample_model.id, sample_model.name, "промт", "success")
        temp_db.clear_request_logs()
        assert temp_db.list_request_logs() == []

    def test_openrouter_models_migrated(self, temp_db: Database) -> None:
        names = {m.name for m in temp_db.list_models()}
        assert "google/gemma-4-31b-it:free" in names

    def test_get_database_factory(self) -> None:
        db = get_database()
        assert db.db_path == DATA_DIR / "chatlist.db"
        assert db.get_setting("request_timeout") == "60"


class TestResultSession:
    def test_empty_session(self, session: ResultSession) -> None:
        assert session.is_empty()
        assert session.selected_for_db() == []

    def test_load_and_selection(self, session: ResultSession, sample_responses) -> None:
        session.load_from_responses(sample_responses)
        session.set_selected(0, True)
        assert len(session.get_selected_rows()) == 1

    def test_load_uses_error_as_text(self, session: ResultSession) -> None:
        session.load_from_responses([PromptResponse(1, "m", "", error="ошибка API")])
        assert session.rows[0].response_text == "ошибка API"


class TestExportUtils:
    def test_export_markdown(self) -> None:
        rows = [SessionRow(1, "model-a", "текст A")]
        md = export_markdown("промт", rows)
        assert "# ChatList" in md
        assert "model-a" in md

    def test_export_json(self) -> None:
        raw = export_json("промт", [SessionRow(5, "gpt", "ответ", selected=True)])
        data = json.loads(raw)
        assert data["prompt"] == "промт"
        assert data["results"][0]["model_id"] == 5


class TestModels:
    def test_build_chat_payload(self) -> None:
        payload = build_chat_payload("gpt-4", "Привет")
        assert payload["messages"][0]["content"] == "Привет"

    def test_build_chat_payload_with_system(self) -> None:
        payload = build_chat_payload("gpt-4", "Привет", system_prompt="Система")
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["content"] == "Привет"

    def test_build_headers_openrouter(self, sample_model: AiModel) -> None:
        model = sample_model.__class__(**{**sample_model.__dict__, "model_type": "openrouter"})
        headers = build_headers(model, "secret")
        assert headers["HTTP-Referer"] == "https://github.com/chatlist"

    def test_extract_chat_response_success(self) -> None:
        data = {"choices": [{"message": {"content": "  ответ  "}}]}
        assert extract_chat_response(data) == "ответ"

    def test_get_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "abc")
        assert get_api_key("TEST_API_KEY") == "abc"

    def test_call_model_missing_api_key(self, temp_db: Database, sample_model: AiModel) -> None:
        result = call_model(sample_model, "тест", db=temp_db)
        assert result.error is not None

    def test_call_model_unsupported_type(self, temp_db: Database, monkeypatch) -> None:
        monkeypatch.setenv("KEY", "secret")
        mid = temp_db.add_model("x", "http://x", "KEY", True, "unknown-type")
        model = temp_db.get_model(mid)
        assert model is not None
        result = call_model(model, "тест", db=temp_db)
        assert "Неподдерживаемый тип" in (result.error or "")

    @patch("models.post_json")
    def test_call_model_success(
        self, mock_post: MagicMock, temp_db: Database, sample_model: AiModel, monkeypatch
    ) -> None:
        monkeypatch.setenv("TEST_API_KEY", "secret")
        mock_post.return_value = ({"choices": [{"message": {"content": "OK"}}]}, None)
        result = call_model(sample_model, "тест", db=temp_db)
        assert result.response_text == "OK"

    def test_send_prompt_empty_models(self) -> None:
        assert send_prompt("тест", []) == []


class TestNetwork:
    @patch("network.httpx.Client")
    def test_post_json_success(self, mock_client_cls: MagicMock) -> None:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response
        mock_client_cls.return_value = client
        data, error = post_json("http://test", {}, {"x": 1})
        assert data == {"ok": True}
        assert error is None

    @patch("network.httpx.Client")
    def test_post_json_http_error(self, mock_client_cls: MagicMock) -> None:
        response = MagicMock()
        response.status_code = 403
        response.text = "Forbidden"
        response.reason_phrase = "Forbidden"
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response
        mock_client_cls.return_value = client
        data, error = post_json("http://test", {}, {})
        assert data is None
        assert "403" in (error or "")


class TestLoggingSetup:
    def test_setup_logging_idempotent(self, tmp_path: Path, monkeypatch) -> None:
        log_file = tmp_path / "test.log"
        monkeypatch.setattr("logging_setup.LOG_FILE", log_file)
        root = logging.getLogger()
        for handler in list(root.handlers):
            if isinstance(handler, logging.FileHandler):
                root.removeHandler(handler)
        setup_logging()
        setup_logging()
        assert len([h for h in root.handlers if isinstance(h, logging.FileHandler)]) == 1


class TestPromptImprover:
    def test_parse_valid_json(self) -> None:
        raw = json.dumps(
            {
                "improved": "Улучшенный промт",
                "alternatives": ["Вариант A", "Вариант B"],
                "model_hints": {"code": "Для кода"},
            },
            ensure_ascii=False,
        )
        result = parse_improvement_response(raw, "исходный")
        assert result.improved == "Улучшенный промт"
        assert len(result.alternatives) == 2
        assert result.model_hints["code"] == "Для кода"

    def test_parse_json_in_markdown_block(self) -> None:
        raw = '```json\n{"improved": "x", "alternatives": ["a"]}\n```'
        result = parse_improvement_response(raw, "исходный")
        assert result.improved == "x"
        assert result.alternatives == ["a"]

    def test_parse_invalid_json_fallback(self) -> None:
        raw = "Просто текст без JSON"
        result = parse_improvement_response(raw, "исходный")
        assert result.improved == raw
        assert result.alternatives == []

    def test_improve_prompt_empty_text(self, temp_db: Database, sample_model: AiModel) -> None:
        result = improve_prompt("  ", sample_model, db=temp_db)
        assert result == "Промт пуст"

    def test_get_improver_model_from_settings(
        self, temp_db: Database, sample_model: AiModel
    ) -> None:
        temp_db.set_setting("prompt_improver_model_id", str(sample_model.id))
        model = get_improver_model(temp_db)
        assert model is not None
        assert model.id == sample_model.id

    @patch("prompt_improver.call_model")
    def test_improve_prompt_success(
        self, mock_call: MagicMock, temp_db: Database, sample_model: AiModel
    ) -> None:
        mock_call.return_value = PromptResponse(
            sample_model.id,
            sample_model.name,
            json.dumps(
                {
                    "improved": "лучше",
                    "alternatives": ["alt1", "alt2"],
                    "model_hints": {"analysis": "анализ"},
                },
                ensure_ascii=False,
            ),
        )
        result = improve_prompt("тест", sample_model, db=temp_db)
        assert isinstance(result, PromptImprovementResult)
        assert result.improved == "лучше"
        assert result.alternatives == ["alt1", "alt2"]
        assert result.model_hints["analysis"] == "анализ"

    @patch("prompt_improver.call_model")
    def test_improve_prompt_api_error(
        self, mock_call: MagicMock, temp_db: Database, sample_model: AiModel
    ) -> None:
        mock_call.return_value = PromptResponse(
            sample_model.id, sample_model.name, "", error="API недоступен"
        )
        result = improve_prompt("тест", sample_model, db=temp_db)
        assert result == "API недоступен"


class TestThemes:
    def test_get_stylesheet_dark_and_light(self) -> None:
        from themes import STYLES_DARK, STYLES_LIGHT, get_stylesheet

        assert get_stylesheet("dark") == STYLES_DARK
        assert get_stylesheet("light") == STYLES_LIGHT
        assert "QPushButton" in get_stylesheet("dark")
        assert "QPushButton#secondaryButton" in get_stylesheet("light")

    def test_apply_palette(self, qapp) -> None:
        from themes import apply_palette

        apply_palette(qapp, "dark")
        apply_palette(qapp, "light")

    def test_apply_theme(self, qapp, temp_db: Database) -> None:
        import main
        from themes import apply_theme

        window = main.MainWindow(temp_db)
        apply_theme(qapp, window, "light", 12)
        assert qapp.font().pointSize() == 12
        window.close()


class TestAppMeta:
    def test_constants(self) -> None:
        from app_meta import APP_NAME, APP_VERSION
        from version import __version__

        assert APP_NAME == "ChatList"
        assert APP_VERSION == __version__


class TestMainGui:
    def test_styles_defined(self) -> None:
        from themes import STYLES_DARK

        assert "QPushButton" in STYLES_DARK

    def test_main_styles_alias(self) -> None:
        import main

        assert "QPushButton" in main.STYLES

    def test_main_window_construct(self, qapp, temp_db: Database) -> None:
        import main
        from app_meta import APP_NAME, APP_VERSION

        window = main.MainWindow(temp_db)
        assert window.windowTitle() == f"{APP_NAME} {APP_VERSION}"
        window.close()

    def test_about_dialog(self, qapp) -> None:
        from about_dialog import AboutDialog

        dialog = AboutDialog()
        assert "ChatList" in dialog.windowTitle()
        dialog.close()

    def test_prompt_improvement_dialog(self, qapp) -> None:
        import main

        substituted: list[str] = []
        result = PromptImprovementResult(
            original="исходный",
            improved="улучшенный",
            alternatives=["alt1"],
            model_hints={"code": "для кода"},
        )
        dialog = main.PromptImprovementDialog(
            result, on_substitute=substituted.append, parent=None
        )
        dialog._substitute("улучшенный")
        assert substituted == ["улучшенный"]
        dialog.close()


class TestScenarios:
    @patch("models.call_model")
    def test_send_prompt_populates_session_flow(
        self, mock_call: MagicMock, temp_db: Database, session: ResultSession
    ) -> None:
        models = temp_db.list_models(active_only=True)
        assert models
        model = models[0]
        mock_call.return_value = PromptResponse(model.id, model.name, "mock-ответ")
        responses = send_prompt("Тест", [model], db=temp_db)
        session.load_from_responses(responses)
        assert session.rows[0].response_text == "mock-ответ"
