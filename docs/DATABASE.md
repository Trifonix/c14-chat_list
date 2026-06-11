# Схема базы данных ChatList

База данных: **SQLite**, файл по умолчанию — `data/chatlist.db` (путь задаётся в `settings.db_path` и модуле `src/paths.py`).

Доступ к БД инкапсулирован в `src/db.py`. API-ключи в БД **не хранятся** — только имя переменной окружения (`api_id`), сам ключ читается из `config/.env`.

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
           │ prompt_id   │──► FK → prompts.id (CASCADE)
           │ model_id    │──► FK → models.id (RESTRICT)
           │ response    │
           │ saved_at    │
           └─────────────┘

┌─────────────┐       ┌─────────────────┐
│  settings   │       │  request_logs   │
│─────────────│       │─────────────────│
│ key (PK)    │       │ id (PK)         │
│ value       │       │ model_id (FK?)  │
└─────────────┘       │ model_name      │
                      │ prompt_text     │
                      │ status          │
                      │ response_preview│
                      │ error_message   │
                      │ duration_ms     │
                      │ created_at      │
                      └─────────────────┘
```

---

## Таблица `prompts`

| Поле          | Тип     | Описание |
|---------------|---------|----------|
| `id`          | INTEGER | PK, AUTOINCREMENT |
| `created_at`  | TEXT    | DEFAULT datetime('now') |
| `prompt_text` | TEXT    | NOT NULL |
| `tags`        | TEXT    | NULL, через запятую |

**Индекс:** `idx_prompts_created_at`

---

## Таблица `models`

| Поле         | Тип     | Описание |
|--------------|---------|----------|
| `id`         | INTEGER | PK |
| `name`       | TEXT    | NOT NULL, UNIQUE — идентификатор в API |
| `api_url`    | TEXT    | NOT NULL |
| `api_id`     | TEXT    | NOT NULL — имя переменной в `.env` |
| `is_active`  | INTEGER | 0 / 1 |
| `model_type` | TEXT    | `openrouter`, `openai`, `deepseek`, `groq` |

**Индекс:** `idx_models_is_active`

При первом запуске seed добавляет три бесплатные модели OpenRouter (`:free`). Устаревшие имена деактивируются миграцией `_migrate()`.

---

## Таблица `results`

| Поле            | Тип     | Описание |
|-----------------|---------|----------|
| `id`            | INTEGER | PK |
| `prompt_id`     | INTEGER | FK → prompts.id, ON DELETE CASCADE |
| `model_id`      | INTEGER | FK → models.id, ON DELETE RESTRICT |
| `response_text` | TEXT    | NOT NULL |
| `saved_at`      | TEXT    | DEFAULT datetime('now') |

**Индексы:** `prompt_id`, `model_id`, `saved_at`

В `results` попадают только строки временной таблицы с `selected = True`.

---

## Таблица `settings`

| Поле    | Тип  | Описание |
|---------|------|----------|
| `key`   | TEXT | PK |
| `value` | TEXT | NULL |

| key               | Пример value              | Назначение |
|-------------------|---------------------------|------------|
| `db_path`         | `.../data/chatlist.db`    | Путь к SQLite |
| `request_timeout` | `60`                      | Таймаут HTTP (сек) |
| `theme`           | `dark`                    | Тема GUI |
| `default_tags`    | ``                        | Теги для новых промтов |

---

## Таблица `request_logs`

Журнал каждого запроса к API (успех или ошибка).

| Поле               | Тип     | Описание |
|--------------------|---------|----------|
| `id`               | INTEGER | PK |
| `model_id`         | INTEGER | FK → models.id, ON DELETE SET NULL |
| `model_name`       | TEXT    | NOT NULL |
| `prompt_text`      | TEXT    | NOT NULL |
| `status`           | TEXT    | `success` / `error` |
| `response_preview` | TEXT    | До 500 символов ответа |
| `error_message`    | TEXT    | Текст ошибки |
| `duration_ms`      | INTEGER | Длительность запроса |
| `created_at`       | TEXT    | DEFAULT datetime('now') |

**Индекс:** `idx_request_logs_created_at`

Дублируется файловым логом `data/chatlist.log` (общие события приложения).

---

## Временная таблица (не в SQLite)

Модуль `src/session.py`, класс `ResultSession`:

| Поле            | Тип  | Описание |
|-----------------|------|----------|
| `model_id`      | int  | Id из `models` |
| `model_name`    | str  | Для GUI |
| `response_text` | str  | Ответ или текст ошибки |
| `selected`      | bool | Чекбокс пользователя |

Жизненный цикл: создаётся после отправки промта → очищается при новом промте / после сохранения / вручную.

---

## Соглашения для `db.py`

- Параметризованные SQL-запросы
- Пакетная вставка в `results`
- Поиск через `LIKE` по текстовым полям
- Сортировка с белым списком столбцов (`PROMPT_SORT_COLUMNS`, …)
- Каскадное удаление `results` при удалении `prompts`

---

## Расположение файлов

| Файл | Путь |
|------|------|
| База SQLite | `data/chatlist.db` |
| Лог приложения | `data/chatlist.log` |
| Переменные окружения | `config/.env` |
