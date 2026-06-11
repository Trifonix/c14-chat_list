"""Временная таблица результатов в памяти."""

from __future__ import annotations

from dataclasses import dataclass, replace

from models import PromptResponse


@dataclass
class SessionRow:
    model_id: int
    model_name: str
    response_text: str
    selected: bool = False


class ResultSession:
    """Хранит результаты текущего запроса до сохранения в БД."""

    def __init__(self) -> None:
        self._rows: list[SessionRow] = []

    def clear(self) -> None:
        self._rows.clear()

    def is_empty(self) -> bool:
        return len(self._rows) == 0

    @property
    def rows(self) -> list[SessionRow]:
        return list(self._rows)

    def load_from_responses(self, responses: list[PromptResponse]) -> None:
        self.clear()
        self._rows = [
            SessionRow(
                model_id=item.model_id,
                model_name=item.model_name,
                response_text=item.response_text or item.error or "Пустой ответ",
                selected=False,
            )
            for item in responses
        ]

    def set_selected(self, index: int, selected: bool) -> None:
        if 0 <= index < len(self._rows):
            self._rows[index] = replace(self._rows[index], selected=selected)

    def get_selected_rows(self) -> list[SessionRow]:
        return [row for row in self._rows if row.selected]

    def selected_for_db(self) -> list[tuple[int, str]]:
        return [(row.model_id, row.response_text) for row in self.get_selected_rows()]
