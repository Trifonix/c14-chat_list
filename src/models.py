"""Логика работы с нейросетями и отправка промтов."""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from dotenv import load_dotenv

from db import AiModel
from network import post_json
from paths import CONFIG_DIR, ENV_FILE, ROOT_DIR

if TYPE_CHECKING:
    from db import Database

logger = logging.getLogger(__name__)

OPENAI_COMPATIBLE_TYPES = {"openai", "deepseek", "groq", "openrouter"}


@dataclass
class PromptResponse:
    model_id: int
    model_name: str
    response_text: str
    error: str | None = None


def load_env(env_path: str | Path | None = None) -> None:
    if env_path is not None:
        load_dotenv(Path(env_path))
        return
    for candidate in (ENV_FILE, ROOT_DIR / ".env", Path(".env")):
        if candidate.exists():
            load_dotenv(candidate)
            return
    load_dotenv()


def get_api_key(api_id: str) -> str | None:
    value = os.getenv(api_id, "").strip()
    return value or None


def build_chat_payload(
    model_name: str,
    prompt_text: str,
    system_prompt: str | None = None,
) -> dict:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt_text})
    return {
        "model": model_name,
        "messages": messages,
    }


def build_headers(model: AiModel, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if model.model_type == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/chatlist"
        headers["X-Title"] = "ChatList"
    return headers


def extract_chat_response(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("API вернул пустой список choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise ValueError("API вернул пустой текст ответа")
    return str(content).strip()


def _log_request(
    db: Database | None,
    model: AiModel,
    prompt_text: str,
    status: str,
    response_text: str = "",
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    if db is None:
        return
    db.log_request(
        model_id=model.id,
        model_name=model.name,
        prompt_text=prompt_text,
        status=status,
        response_preview=response_text,
        error_message=error_message,
        duration_ms=duration_ms,
    )


def call_model(
    model: AiModel,
    prompt_text: str,
    timeout: float = 60.0,
    db: Database | None = None,
    system_prompt: str | None = None,
) -> PromptResponse:
    started = time.perf_counter()
    api_key = get_api_key(model.api_id)
    if not api_key:
        error = f"Ключ API не найден в .env (переменная {model.api_id})"
        _log_request(db, model, prompt_text, "error", error_message=error)
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=error,
        )

    if model.model_type not in OPENAI_COMPATIBLE_TYPES:
        error = f"Неподдерживаемый тип модели: {model.model_type}"
        _log_request(db, model, prompt_text, "error", error_message=error)
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=error,
        )

    headers = build_headers(model, api_key)
    payload = build_chat_payload(model.name, prompt_text, system_prompt=system_prompt)

    data, error = post_json(model.api_url, headers, payload, timeout=timeout)
    duration_ms = int((time.perf_counter() - started) * 1000)

    if error:
        _log_request(
            db, model, prompt_text, "error", error_message=error, duration_ms=duration_ms
        )
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=error,
        )

    try:
        text = extract_chat_response(data or {})
    except ValueError as exc:
        _log_request(
            db,
            model,
            prompt_text,
            "error",
            error_message=str(exc),
            duration_ms=duration_ms,
        )
        return PromptResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=str(exc),
        )

    _log_request(
        db, model, prompt_text, "success", response_text=text, duration_ms=duration_ms
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
    db: Database | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[PromptResponse]:
    """Отправляет промт во все активные модели."""
    if not active_models:
        return []

    load_env()

    def _report(message: str) -> None:
        if on_progress:
            on_progress(message)

    def _task(model: AiModel) -> PromptResponse:
        _report(f"Запрос отправлен в модель {model.name}")
        logger.info("Отправка промта в модель %s", model.name)
        _report(f"Ожидание ответа от модели {model.name}")
        result = call_model(model, prompt_text, timeout=timeout, db=db)
        if result.error:
            logger.warning("Ошибка модели %s: %s", model.name, result.error)
            _report(f"Ошибка от модели {model.name}: {result.error}")
            result.response_text = result.error
        else:
            _report(f"Ответ получен от модели {model.name}")
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
