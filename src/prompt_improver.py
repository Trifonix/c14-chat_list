"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from db import AiModel
from models import call_model, load_env

if TYPE_CHECKING:
    from db import Database

SYSTEM_PROMPT = (
    "Ты помощник по улучшению промтов. Верни JSON: "
    '{"improved": "...", "alternatives": ["...", "..."], '
    '"model_hints": {"code": "...", "analysis": "...", "creative": "..."}}. '
    "Язык ответа — как у исходного промта. "
    "alternatives — 2–3 переформулировки. "
    "model_hints — опциональные подсказки под тип задачи."
)


@dataclass
class PromptImprovementResult:
    original: str
    improved: str
    alternatives: list[str]
    model_hints: dict[str, str]


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE
    )
    if block_match:
        return block_match.group(1).strip()
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text


def parse_improvement_response(raw: str, original: str) -> PromptImprovementResult:
    """Разбирает JSON-ответ модели; при ошибке — эвристический fallback."""
    json_text = _extract_json_text(raw)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return PromptImprovementResult(
            original=original,
            improved=raw.strip() or original,
            alternatives=[],
            model_hints={},
        )

    if not isinstance(data, dict):
        return PromptImprovementResult(
            original=original,
            improved=raw.strip() or original,
            alternatives=[],
            model_hints={},
        )

    improved = str(data.get("improved", "")).strip() or original
    alternatives_raw = data.get("alternatives") or []
    alternatives: list[str] = []
    if isinstance(alternatives_raw, list):
        alternatives = [str(item).strip() for item in alternatives_raw if str(item).strip()]

    hints_raw = data.get("model_hints") or {}
    model_hints: dict[str, str] = {}
    if isinstance(hints_raw, dict):
        model_hints = {
            str(key): str(value)
            for key, value in hints_raw.items()
            if value is not None and str(value).strip()
        }

    return PromptImprovementResult(
        original=original,
        improved=improved,
        alternatives=alternatives[:3],
        model_hints=model_hints,
    )


def get_improver_model(db: Database) -> AiModel | None:
    """Возвращает модель для улучшения промта из settings или первую активную."""
    raw = db.get_setting("prompt_improver_model_id")
    if raw:
        try:
            model = db.get_model(int(raw))
            if model and model.is_active:
                return model
        except ValueError:
            pass
    active = db.list_models(active_only=True)
    return active[0] if active else None


def improve_prompt(
    text: str,
    model: AiModel,
    timeout: float = 60.0,
    db: Database | None = None,
) -> PromptImprovementResult | str:
    """Улучшает промт через одну модель. При ошибке API возвращает строку."""
    original = text.strip()
    if not original:
        return "Промт пуст"

    load_env()
    user_message = f"Исходный промт:\n{original}"
    response = call_model(
        model,
        user_message,
        timeout=timeout,
        db=db,
        system_prompt=SYSTEM_PROMPT,
    )

    if response.error:
        return response.error

    return parse_improvement_response(response.response_text, original)
