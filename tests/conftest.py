"""Общие фикстуры для всех тестов ChatList."""

from __future__ import annotations

import gc
import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from db import AiModel, Database
from models import PromptResponse
from session import ResultSession


@pytest.fixture
def temp_db() -> Iterator[Database]:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = handle.name
    handle.close()
    db = Database(path)
    db.init()
    try:
        yield db
    finally:
        del db
        gc.collect()
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def session() -> ResultSession:
    return ResultSession()


@pytest.fixture
def sample_model(temp_db: Database) -> AiModel:
    model_id = temp_db.add_model(
        "test/sample-model",
        "https://api.example.com/v1/chat/completions",
        "TEST_API_KEY",
        is_active=True,
        model_type="openai",
    )
    model = temp_db.get_model(model_id)
    assert model is not None
    return model


@pytest.fixture
def sample_responses(sample_model: AiModel) -> list[PromptResponse]:
    return [
        PromptResponse(sample_model.id, sample_model.name, "ответ модели"),
        PromptResponse(99, "other-model", "второй ответ"),
    ]


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
