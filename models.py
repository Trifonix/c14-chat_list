"""Логика работы с нейросетями и отправка промтов."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from db import AiModel
from network import post_json

logger = logging.getLogger(__name__)

OPENAI_COMPATIBLE_TYPES = {"openai", "deepseek", "groq"}


@dataclass
class PromptResponse:
    model_id: int
    model_name: str
    response_text: str
    error: str | None = None


def load_env(env_path: str | Path | None = None) -> None:
    path = Path(env_path) if env_path else Path(".env")
    if path.exists():
        load_dotenv(path)
    else:
        load_dotenv()


def get_api_key(api_id: str) -> str | None:
    value = os.getenv(api_id, "").strip()
    return value or None


def build_chat_payload(model_name: str, prompt_text: str) -> dict:
    return {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_text}],
    }


def extract_chat_response(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("API вернул пустой список choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise ValueError("API вернул пустой текст ответа")
    return str(content).strip()


def call_model(
    model: AiModel,
    prompt_text: str,
    timeout: float = 60.0,
) -> PromptResponse:
    api_key = get_api_key(model.api_id)
    if not api_key:
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"Ключ API не найден в .env (переменная {model.api_id})",
        )

    if model.model_type not in OPENAI_COMPATIBLE_TYPES:
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"Неподдерживаемый тип модели: {model.model_type}",
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = build_chat_payload(model.name, prompt_text)

    data, error = post_json(model.api_url, headers, payload, timeout=timeout)
    if error:
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=error,
        )

    try:
        text = extract_chat_response(data or {})
    except ValueError as exc:
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=str(exc),
        )

    return PromptResponse(
        model_id=model.id,
        model_name=model.name,
        response_text=text,
    )


def send_prompt(
    prompt_text: str,
    active_models: list[AiModel],
    timeout: float = 60.0,
    parallel: bool = True,
) -> list[PromptResponse]:
    """Отправляет промт во все активные модели."""
    if not active_models:
        return []

    load_env()

    def _task(model: AiModel) -> PromptResponse:
        logger.info("Отправка промта в модель %s", model.name)
        result = call_model(model, prompt_text, timeout=timeout)
        if result.error:
            logger.warning("Ошибка модели %s: %s", model.name, result.error)
            result.response_text = result.error
        return result

    results: list[PromptResponse] = []
    if parallel and len(active_models) > 1:
        with ThreadPoolExecutor(max_workers=len(active_models)) as executor:
            futures = {executor.submit(_task, model): model for model in active_models}
            for future in as_completed(futures):
                results.append(future.result())
    else:
        for model in active_models:
            results.append(_task(model))

    order = {model.id: index for index, model in enumerate(active_models)}
    results.sort(key=lambda item: order.get(item.model_id, 0))
    return results
