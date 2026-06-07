"""Доступ к SQLite для ChatList."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = "chatlist.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    prompt_text TEXT    NOT NULL,
    tags        TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id      TEXT    NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    model_type  TEXT    NOT NULL DEFAULT 'openai'
);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    model_id      INTEGER NOT NULL REFERENCES models(id)  ON DELETE RESTRICT,
    response_text TEXT    NOT NULL,
    saved_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active   ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id  ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id   ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_saved_at   ON results(saved_at);
"""

PROMPT_SORT_COLUMNS = {"id", "created_at", "prompt_text", "tags"}
MODEL_SORT_COLUMNS = {"id", "name", "api_url", "api_id", "is_active", "model_type"}
RESULT_SORT_COLUMNS = {"id", "prompt_id", "model_id", "response_text", "saved_at"}


@dataclass
class Prompt:
    id: int
    created_at: str
    prompt_text: str
    tags: str | None


@dataclass
class AiModel:
    id: int
    name: str
    api_url: str
    api_id: str
    is_active: bool
    model_type: str


@dataclass
class SavedResult:
    id: int
    prompt_id: int
    model_id: int
    response_text: str
    saved_at: str
    prompt_text: str | None = None
    model_name: str | None = None


class Database:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._seed(conn)

    def _seed(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        if count == 0:
            seed_models = [
                (
                    "gpt-4o",
                    "https://api.openai.com/v1/chat/completions",
                    "OPENAI_API_KEY",
                    1,
                    "openai",
                ),
                (
                    "deepseek-chat",
                    "https://api.deepseek.com/v1/chat/completions",
                    "DEEPSEEK_API_KEY",
                    1,
                    "deepseek",
                ),
                (
                    "llama-3.3-70b-versatile",
                    "https://api.groq.com/openai/v1/chat/completions",
                    "GROQ_API_KEY",
                    0,
                    "groq",
                ),
            ]
            conn.executemany(
                """
                INSERT INTO models (name, api_url, api_id, is_active, model_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                seed_models,
            )

        default_settings = {
            "db_path": str(self.db_path),
            "request_timeout": "60",
            "theme": "dark",
            "default_tags": "",
        }
        for key, value in default_settings.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                """,
                (key, value),
            )

    # --- prompts ---

    def add_prompt(self, prompt_text: str, tags: str | None = None) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO prompts (prompt_text, tags) VALUES (?, ?)",
                (prompt_text.strip(), tags or None),
            )
            return int(cursor.lastrowid)

    def get_prompt(self, prompt_id: int) -> Prompt | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
            ).fetchone()
            return self._row_to_prompt(row) if row else None

    def list_prompts(
        self,
        search: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "DESC",
    ) -> list[Prompt]:
        column = sort_by if sort_by in PROMPT_SORT_COLUMNS else "created_at"
        direction = "DESC" if sort_dir.upper() == "DESC" else "ASC"
        query = f"SELECT * FROM prompts WHERE 1=1"
        params: list[Any] = []
        if search.strip():
            pattern = f"%{search.strip()}%"
            query += " AND (prompt_text LIKE ? OR IFNULL(tags, '') LIKE ?)"
            params.extend([pattern, pattern])
        query += f" ORDER BY {column} {direction}"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_prompt(row) for row in rows]

    def update_prompt(
        self, prompt_id: int, prompt_text: str, tags: str | None = None
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE prompts SET prompt_text = ?, tags = ? WHERE id = ?",
                (prompt_text.strip(), tags or None, prompt_id),
            )

    def delete_prompt(self, prompt_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

    # --- models ---

    def add_model(
        self,
        name: str,
        api_url: str,
        api_id: str,
        is_active: bool = True,
        model_type: str = "openai",
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO models (name, api_url, api_id, is_active, model_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name.strip(), api_url.strip(), api_id.strip(), int(is_active), model_type),
            )
            return int(cursor.lastrowid)

    def get_model(self, model_id: int) -> AiModel | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
            return self._row_to_model(row) if row else None

    def list_models(
        self,
        search: str = "",
        active_only: bool = False,
        sort_by: str = "name",
        sort_dir: str = "ASC",
    ) -> list[AiModel]:
        column = sort_by if sort_by in MODEL_SORT_COLUMNS else "name"
        direction = "DESC" if sort_dir.upper() == "DESC" else "ASC"
        query = "SELECT * FROM models WHERE 1=1"
        params: list[Any] = []
        if active_only:
            query += " AND is_active = 1"
        if search.strip():
            pattern = f"%{search.strip()}%"
            query += " AND (name LIKE ? OR api_url LIKE ? OR api_id LIKE ?)"
            params.extend([pattern, pattern, pattern])
        query += f" ORDER BY {column} {direction}"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_model(row) for row in rows]

    def update_model(
        self,
        model_id: int,
        name: str,
        api_url: str,
        api_id: str,
        is_active: bool,
        model_type: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE models
                SET name = ?, api_url = ?, api_id = ?, is_active = ?, model_type = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    api_url.strip(),
                    api_id.strip(),
                    int(is_active),
                    model_type,
                    model_id,
                ),
            )

    def delete_model(self, model_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM models WHERE id = ?", (model_id,))

    def toggle_model_active(self, model_id: int) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT is_active FROM models WHERE id = ?", (model_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Модель {model_id} не найдена")
            new_value = 0 if row["is_active"] else 1
            conn.execute(
                "UPDATE models SET is_active = ? WHERE id = ?", (new_value, model_id)
            )
            return bool(new_value)

    # --- results ---

    def save_results(
        self,
        prompt_id: int,
        rows: list[tuple[int, str]],
    ) -> None:
        if not rows:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO results (prompt_id, model_id, response_text)
                VALUES (?, ?, ?)
                """,
                [(prompt_id, model_id, response_text) for model_id, response_text in rows],
            )

    def list_results(
        self,
        search: str = "",
        sort_by: str = "saved_at",
        sort_dir: str = "DESC",
    ) -> list[SavedResult]:
        column = sort_by if sort_by in RESULT_SORT_COLUMNS else "saved_at"
        direction = "DESC" if sort_dir.upper() == "DESC" else "ASC"
        query = """
            SELECT r.*, p.prompt_text, m.name AS model_name
            FROM results r
            JOIN prompts p ON r.prompt_id = p.id
            JOIN models m ON r.model_id = m.id
            WHERE 1=1
        """
        params: list[Any] = []
        if search.strip():
            pattern = f"%{search.strip()}%"
            query += " AND (r.response_text LIKE ? OR p.prompt_text LIKE ? OR m.name LIKE ?)"
            params.extend([pattern, pattern, pattern])
        query += f" ORDER BY r.{column} {direction}"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_result(row) for row in rows]

    def delete_result(self, result_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM results WHERE id = ?", (result_id,))

    # --- settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return default
            return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def list_settings(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
            return {row["key"]: row["value"] or "" for row in rows}

    # --- helpers ---

    @staticmethod
    def _row_to_prompt(row: sqlite3.Row) -> Prompt:
        return Prompt(
            id=row["id"],
            created_at=row["created_at"],
            prompt_text=row["prompt_text"],
            tags=row["tags"],
        )

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> AiModel:
        return AiModel(
            id=row["id"],
            name=row["name"],
            api_url=row["api_url"],
            api_id=row["api_id"],
            is_active=bool(row["is_active"]),
            model_type=row["model_type"],
        )

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> SavedResult:
        return SavedResult(
            id=row["id"],
            prompt_id=row["prompt_id"],
            model_id=row["model_id"],
            response_text=row["response_text"],
            saved_at=row["saved_at"],
            prompt_text=row["prompt_text"],
            model_name=row["model_name"],
        )


def get_database() -> Database:
    db = Database()
    db.init()
    return db
