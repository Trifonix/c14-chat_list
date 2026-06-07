# Схема базы данных ChatList

База данных: **SQLite**, файл по умолчанию — `chatlist.db` в каталоге приложения (путь можно вынести в `settings`).

Доступ к БД инкапсулирован в модуле `db.py`. API-ключи в БД **не хранятся** — только имя переменной окружения (`api_id`), сам ключ читается из файла `.env`.

---

## Диаграмма связей

```
┌─────────────┐       ┌─────────────┐
│   prompts   │       │   models    │
│─────────────│       │─────────────│
│ id (PK)     │       │ id (PK)     │
│ created_at  │       │ name        │
│ prompt_text │       │ api_url     │
│ tags        │       │ api_id      │
└──────┬──────┘       │ is_active   │
       │              │ model_type  │
       │              └──────┬──────┘
       │                     │
       └──────────┬──────────┘
                  │
                  ▼
           ┌─────────────┐
           │   results   │
           │─────────────│
           │ id (PK)     │
           │ prompt_id   │──► FK → prompts.id
           │ model_id    │──► FK → models.id
           │ response    │
           │ saved_at    │
           └─────────────┘

┌─────────────┐
│  settings   │   (независимая таблица ключ–значение)
│─────────────│
│ key (PK)    │
│ value       │
└─────────────┘
```

---

## Таблица `prompts`

Хранит сохранённые запросы пользователя.

| Поле         | Тип          | Ограничения              | Описание                                      |
|--------------|--------------|--------------------------|-----------------------------------------------|
| `id`         | INTEGER      | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор                    |
| `created_at` | TEXT         | NOT NULL, DEFAULT (datetime('now')) | Дата и время создания записи (ISO 8601) |
| `prompt_text`| TEXT         | NOT NULL                 | Текст промта                                  |
| `tags`       | TEXT         | NULL                     | Теги через запятую, например: `код,python`   |

**Индексы:** `idx_prompts_created_at` на `created_at` (сортировка по дате).

**Пример строки:**

| id | created_at          | prompt_text              | tags    |
|----|-----------------------|--------------------------|---------|
| 1  | 2026-06-07T12:00:00   | Объясни async/await в Python | python |

---

## Таблица `models`

Справочник нейросетей и параметров подключения к API.

| Поле         | Тип          | Ограничения              | Описание                                      |
|--------------|--------------|--------------------------|-----------------------------------------------|
| `id`         | INTEGER      | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор                    |
| `name`       | TEXT         | NOT NULL, UNIQUE         | Отображаемое имя модели                       |
| `api_url`    | TEXT         | NOT NULL                 | Базовый URL API (endpoint)                    |
| `api_id`     | TEXT         | NOT NULL                 | Имя переменной в `.env`, например `OPENAI_API_KEY` |
| `is_active`  | INTEGER      | NOT NULL, DEFAULT 1      | `1` — участвует в отправке, `0` — отключена  |
| `model_type` | TEXT         | NOT NULL, DEFAULT 'openai' | Тип адаптера: `openai`, `deepseek`, `groq` и т.д. |

**Индексы:** `idx_models_is_active` на `is_active`.

**Важно:** значение `api_id` — это ключ в `.env`, не сам секрет:

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

**Пример строки:**

| id | name       | api_url                              | api_id           | is_active | model_type |
|----|------------|--------------------------------------|------------------|-----------|------------|
| 1  | GPT-4o     | https://api.openai.com/v1/chat/completions | OPENAI_API_KEY | 1         | openai     |

---

## Таблица `results`

Постоянное хранение ответов, которые пользователь отметил и сохранил из временной таблицы.

| Поле          | Тип     | Ограничения              | Описание                                      |
|---------------|---------|--------------------------|-----------------------------------------------|
| `id`          | INTEGER | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор                    |
| `prompt_id`   | INTEGER | NOT NULL, FK → prompts.id | Связь с промтом, по которому получен ответ  |
| `model_id`    | INTEGER | NOT NULL, FK → models.id  | Связь с моделью, давшей ответ               |
| `response_text` | TEXT  | NOT NULL                 | Текст ответа нейросети                        |
| `saved_at`    | TEXT    | NOT NULL, DEFAULT (datetime('now')) | Дата и время сохранения в БД          |

**Индексы:**

- `idx_results_prompt_id` на `prompt_id`
- `idx_results_model_id` на `model_id`
- `idx_results_saved_at` на `saved_at`

**Пример строки:**

| id | prompt_id | model_id | response_text        | saved_at              |
|----|-----------|----------|----------------------|-----------------------|
| 1  | 1         | 1        | Async/await позволяет… | 2026-06-07T12:05:00 |

При сохранении из GUI в `results` попадают только строки временной таблицы с `selected = True`. Связь `prompt_id` берётся из текущего промта (нового или выбранного из `prompts`); при первом использовании нового текста промт предварительно записывается в `prompts`.

---

## Таблица `settings`

Произвольные настройки приложения в формате ключ–значение.

| Поле    | Тип  | Ограничения | Описание                    |
|---------|------|-------------|-----------------------------|
| `key`   | TEXT | PRIMARY KEY | Уникальное имя настройки    |
| `value` | TEXT | NULL        | Значение (строка)           |

**Рекомендуемые ключи:**

| key              | Пример value        | Назначение                          |
|------------------|---------------------|-------------------------------------|
| `db_path`        | `chatlist.db`       | Путь к файлу SQLite                 |
| `request_timeout`| `60`                | Таймаут HTTP-запроса (секунды)      |
| `theme`          | `dark`              | Тема интерфейса                     |
| `default_tags`   | ``                  | Теги по умолчанию для новых промтов |

---

## Временная таблица (не в SQLite)

Результаты текущей сессии запроса хранятся **только в памяти** приложения, в БД не пишутся до нажатия «Сохранить».

| Поле            | Тип    | Описание                                      |
|-----------------|--------|-----------------------------------------------|
| `model_id`      | int    | Id из таблицы `models`                        |
| `model_name`    | str    | Имя для отображения в GUI                     |
| `response_text` | str    | Ответ модели или текст ошибки                 |
| `selected`      | bool   | Отмечен ли чекбокс пользователем              |

Жизненный цикл:

1. Создаётся после успешной отправки промта в активные модели.
2. Очищается при вводе нового промта или после сохранения выбранных строк.
3. Не дублируется в SQLite.

---

## SQL: создание таблиц

```sql
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
```

---

## Начальные данные (seed)

При первом запуске `db.py` может заполнить:

**`models`** — примеры (без реальных ключей):

| name     | api_url                                      | api_id            | model_type |
|----------|----------------------------------------------|-------------------|------------|
| GPT-4o   | https://api.openai.com/v1/chat/completions   | OPENAI_API_KEY    | openai     |
| DeepSeek | https://api.deepseek.com/v1/chat/completions | DEEPSEEK_API_KEY  | deepseek   |

**`settings`:**

| key              | value        |
|------------------|--------------|
| `request_timeout`| `60`         |
| `theme`          | `dark`       |

---

## Соглашения для `db.py`

- Все запросы — через параметризованные SQL-выражения (защита от SQL-инъекций).
- Транзакция при пакетной вставке в `results`.
- Методы поиска: `LIKE` по `prompt_text`, `tags`, `response_text`, `name`.
- Сортировка: по любому столбцу таблицы, направление `ASC` / `DESC`.
- При удалении промта каскадно удаляются связанные `results` (`ON DELETE CASCADE`).
