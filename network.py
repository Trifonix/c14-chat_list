"""HTTP-клиент для запросов к API нейросетей."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float = 60.0,
) -> tuple[dict[str, Any] | None, str | None]:
    """Отправляет POST-запрос и возвращает (данные, ошибка)."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                detail = response.text.strip() or response.reason_phrase
                return None, f"HTTP {response.status_code}: {detail}"
            return response.json(), None
    except httpx.TimeoutException:
        logger.warning("Таймаут запроса к %s", url)
        return None, "Превышено время ожидания ответа от API"
    except httpx.RequestError as exc:
        logger.warning("Сетевая ошибка %s: %s", url, exc)
        return None, f"Сетевая ошибка: {exc}"
    except ValueError as exc:
        logger.warning("Некорректный JSON от %s: %s", url, exc)
        return None, f"Некорректный ответ API: {exc}"
