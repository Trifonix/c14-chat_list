# ChatList

Python-приложение для отправки одного промта в несколько нейросетей и сравнения их ответов. Построено на **PyQt6** и **SQLite**.

## Возможности

- Ввод нового промта или выбор сохранённого из базы
- Параллельная отправка в активные модели (OpenRouter)
- Временная таблица результатов с чекбоксами и просмотром ответа в Markdown
- Сохранение отмеченных ответов в постоянную БД
- Вкладки: **Запрос**, **Промты**, **Модели**, **Результаты**, **Логи**, **Настройки**
- Поиск и сортировка во всех таблицах
- Экспорт в Markdown и JSON
- Логи запросов в БД и файл `data/chatlist.log`
- Тёмная тема интерфейса с контрастными элементами управления

## Требования

- Python 3.11+
- Windows / Linux / macOS

## Установка

```powershell
cd C:\projects\app
pip install -r config/requirements.txt
Copy-Item config\.env.example config\.env
```

Откройте `config/.env` и укажите API-ключи. Для OpenRouter достаточно одной переменной:

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

## Запуск

```powershell
python main.py
```

При первом запуске создаётся `data/chatlist.db` с моделями OpenRouter по умолчанию.

## Структура проекта

```
ChatList/
├── main.py              # Точка входа и графический интерфейс
├── README.md
├── LICENSE
├── src/                 # Python-модули
│   ├── db.py               # SQLite
│   ├── models.py           # Отправка промтов в API
│   ├── network.py          # HTTP-клиент
│   ├── session.py          # Временная таблица в памяти
│   ├── export_utils.py     # Экспорт MD / JSON
│   ├── logging_setup.py    # Файловые логи
│   └── paths.py            # Пути data/, config/, docs/
├── docs/                # Документация
│   ├── PROJECT.md          # Спецификация
│   ├── PLAN.md             # План и статус реализации
│   └── DATABASE.md         # Схема БД
├── config/              # Конфигурация и сборка
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   ├── chatlist.spec
│   └── minimal_program.spec
├── data/                # БД и логи (создаются автоматически)
│   ├── chatlist.db
│   └── chatlist.log
└── tests/               # pytest
    ├── conftest.py
    └── test_all.py
```

## Настройка моделей

На вкладке **Модели** можно включать/отключать нейросети. Поле **Переменная .env** должно совпадать с именем ключа в `config/.env` (например, `OPENROUTER_API_KEY`).

Модели OpenRouter по умолчанию (в API — **с суффиксом `:free`**):

| Имя модели | Тип |
|------------|-----|
| `google/gemma-4-31b-it:free` | openrouter |
| `poolside/laguna-xs.2:free` | openrouter |
| `openai/gpt-oss-20b:free` | openrouter |

## Тесты

Единый набор pytest для рефакторинга — покрывает все модули в `src/` и smoke-тесты GUI:

```powershell
pip install -r config/requirements.txt
pytest -c config/pytest.ini --rootdir=.
pytest -c config/pytest.ini --rootdir=. -q
```

## Сборка exe

```powershell
pip install pyinstaller
pyinstaller config/chatlist.spec
```

Исполняемый файл: `dist\chatlist.exe`

Рядом с exe положите `config/.env` с API-ключами (или `.env` в рабочей папке).

## Документация

- [docs/PROJECT.md](docs/PROJECT.md) — назначение и рабочий процесс
- [docs/DATABASE.md](docs/DATABASE.md) — схема SQLite
- [docs/PLAN.md](docs/PLAN.md) — этапы разработки и текущий статус
