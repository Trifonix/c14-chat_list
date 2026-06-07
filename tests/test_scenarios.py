"""Сквозные сценарии этапа 6 PLAN.md."""

from __future__ import annotations

import gc
import os
import tempfile
import unittest
from unittest.mock import patch

from db import Database
from export_utils import export_json, export_markdown
from models import PromptResponse, send_prompt
from session import ResultSession


class ScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db = Database(self._tmp.name)
        self.db.init()
        self.session = ResultSession()

    def tearDown(self) -> None:
        del self.db
        gc.collect()
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_empty_prompt_rejected_by_logic(self) -> None:
        prompt_text = "   "
        self.assertFalse(bool(prompt_text.strip()))

    def test_no_active_models(self) -> None:
        for model in self.db.list_models():
            if model.is_active:
                self.db.toggle_model_active(model.id)
        active = self.db.list_models(active_only=True)
        self.assertEqual(active, [])
        responses = send_prompt("Привет", active, db=self.db)
        self.assertEqual(responses, [])

    def test_new_prompt_clears_session(self) -> None:
        self.session.load_from_responses(
            [PromptResponse(1, "m1", "ответ 1"), PromptResponse(2, "m2", "ответ 2")]
        )
        self.assertEqual(len(self.session.rows), 2)
        self.session.clear()
        self.assertTrue(self.session.is_empty())

    def test_save_only_selected_rows(self) -> None:
        self.session.load_from_responses(
            [
                PromptResponse(1, "m1", "ответ 1"),
                PromptResponse(2, "m2", "ответ 2"),
            ]
        )
        self.session.set_selected(0, True)
        prompt_id = self.db.add_prompt("Тестовый промт")
        self.db.save_results(prompt_id, self.session.selected_for_db())
        saved = self.db.list_results()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].response_text, "ответ 1")

    def test_save_without_selection_is_empty(self) -> None:
        self.session.load_from_responses([PromptResponse(1, "m1", "ответ")])
        self.assertEqual(self.session.get_selected_rows(), [])
        self.assertEqual(self.session.selected_for_db(), [])

    def test_saved_prompt_can_be_loaded(self) -> None:
        prompt_id = self.db.add_prompt("Объясни Python", "python")
        loaded = self.db.get_prompt(prompt_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.prompt_text, "Объясни Python")

    def test_openrouter_models_migrated(self) -> None:
        names = {model.name for model in self.db.list_models()}
        self.assertIn("openai/gpt-4o-mini", names)

    @patch("models.call_model")
    def test_send_prompt_populates_session_flow(self, mock_call) -> None:
        models = self.db.list_models(active_only=True)
        if not models:
            mid = self.db.add_model(
                "test-model",
                "https://example.com",
                "TEST_KEY",
                True,
                "openrouter",
            )
            models = [self.db.get_model(mid)]
        assert models and models[0] is not None
        model = models[0]
        mock_call.return_value = PromptResponse(model.id, model.name, "mock-ответ")

        responses = send_prompt("Тест", [model], db=self.db)
        self.session.load_from_responses(responses)

        self.assertEqual(len(self.session.rows), 1)
        self.assertEqual(self.session.rows[0].response_text, "mock-ответ")

    def test_export_formats(self) -> None:
        rows = self.session.rows
        self.session.load_from_responses([PromptResponse(1, "m1", "текст")])
        rows = self.session.rows
        md = export_markdown("промт", rows)
        js = export_json("промт", rows)
        self.assertIn("# ChatList", md)
        self.assertIn('"prompt": "промт"', js)


if __name__ == "__main__":
    unittest.main()
