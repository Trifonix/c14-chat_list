# План реализации ChatList

Поэтапный порядок разработки по [PROJECT.md](PROJECT.md). **Статус: реализовано** (актуально на текущую версию).

---

## Структура каталогов (финальная)

```
├── main.py              # GUI + точка входа
├── README.md
├── LICENSE
├── src/                 # Python-модули
├── docs/                # MD-документация
├── config/              # requirements, pytest, .env, spec-файлы
├── data/                # chatlist.db, chatlist.log
└── tests/               # pytest (test_all.py)
```

---

## Этап 1. Подготовка проекта — ✅

- [x] Модули в `src/`, точка входа `main.py`
- [x] `config/requirements.txt`: PyQt6, httpx, python-dotenv, pytest
- [x] `config/.env.example`, ключи в `config/.env`
- [x] Схема БД в [DATABASE.md](DATABASE.md)

## Этап 2. База данных (`src/db.py`) — ✅

- [x] SQLite в `data/chatlist.db`
- [x] Таблицы: prompts, models, results, settings, request_logs
- [x] CRUD, поиск, сортировка, seed OpenRouter-моделей
- [x] Миграция устаревших имён моделей

## Этап 3. Сеть и модели — ✅

- [x] `src/network.py` — httpx, таймауты, ошибки
- [x] `src/models.py` — ключи из `.env`, адаптеры openai/openrouter/deepseek/groq
- [x] `send_prompt()` — параллельная отправка, прогресс, логирование

## Этап 4. Временная таблица — ✅

- [x] `src/session.py` — ResultSession, selected, selected_for_db()

## Этап 5. GUI (`main.py`) — ✅

- [x] Вкладки: Запрос, Промты, Модели, Результаты, Логи, Настройки
- [x] Тёмная тема, контрастные кнопки и поля
- [x] Markdown-просмотр ответа
- [x] Индикатор статуса при отправке

## Этап 6. Связка и сценарии — ✅

- [x] Сквозной поток: промт → отправка → выбор → сохранение
- [x] Граничные случаи (пустой промт, нет моделей, нет выбора)

## Этап 7. Дополнительные функции — ✅

- [x] Экспорт MD / JSON (`src/export_utils.py`)
- [x] Логи в `request_logs` и `data/chatlist.log`
- [x] PyInstaller: `config/chatlist.spec`
- [x] Единый pytest: `tests/test_all.py`

## Этап 8. Финализация — ✅

- [x] README, PROJECT.md, DATABASE.md актуализированы
- [x] Файлы разложены по каталогам (корень: main.py, README, LICENSE)
- [x] `pytest -c config/pytest.ini --rootdir=.` для проверки после рефакторинга

---

## Порядок зависимостей

```
Этап 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
           ↑
      DATABASE.md + config/.env
```

## Команды разработчика

```powershell
pip install -r config/requirements.txt
python main.py
pytest -c config/pytest.ini --rootdir=.
pyinstaller config/chatlist.spec
```
