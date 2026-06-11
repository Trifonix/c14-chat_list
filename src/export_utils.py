"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from session import SessionRow


def export_markdown(prompt_text: str, rows: list[SessionRow]) -> str:
    lines = [
        "# ChatList — результаты",
        "",
        f"**Промт:** {prompt_text}",
        "",
        f"**Дата экспорта:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {index}. {row.model_name}",
                "",
                row.response_text,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def export_json(prompt_text: str, rows: list[SessionRow]) -> str:
    payload = {
        "prompt": prompt_text,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "results": [
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "response_text": row.response_text,
                "selected": row.selected,
            }
            for row in rows
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
