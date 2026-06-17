# Публикация ChatList на GitHub

Пошаговая инструкция: локальная сборка, GitHub Release и GitHub Pages.

---

## 1. Подготовка (один раз)

### 1.1. Инструменты на Windows

```powershell
# Python 3.11+
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r config/requirements.txt
pip install pyinstaller
```

Установите [Inno Setup 6](https://jrsoftware.org/isdl.php) — для установщика.

### 1.2. API-ключ для сборки

Создайте `config\.env` (файл в `.gitignore`, в git не попадает):

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

Ключ **вшивается в exe** при сборке. Пользователь получает один файл без `.env`.

### 1.3. Версия

Измените номер в `version.py`:

```python
__version__ = "1.2.0"
```

---

## 2. Локальная сборка

```powershell
.\config\build.ps1
```

Результат:

| Файл | Назначение |
|------|------------|
| `dist\chatlist-VERSION.exe` | Программа (portable, один файл) |
| `dist\ChatList-VERSION-Setup.exe` | Установщик Windows |
| `dist\ChatList-VERSION-portable.zip` | Архив с одним exe для Release |
| `dist\release\` | Папка для загрузки в GitHub Release + SHA256SUMS.txt |

Сборка без ключей (только для разработки):

```powershell
.\config\build.ps1 -AllowMissingEnv
```

### Что видит пользователь после установки

```
C:\Program Files\ChatList\
    chatlist-1.2.0.exe      ← единственный файл
    data\                   ← создаётся при первом запуске
        chatlist.db
        chatlist.log
```

---

## 3. GitHub Release (ручная публикация)

### 3.1. Коммит и тег

```powershell
git add .
git commit -m "Release 1.2.0"
git tag v1.2.0
git push origin main
git push origin v1.2.0
```

Тег **обязательно** с префиксом `v` (например `v1.2.0`).

### 3.2. Создание Release на GitHub

1. Откройте репозиторий на GitHub → **Releases** → **Draft a new release**.
2. **Choose a tag:** `v1.2.0`.
3. **Release title:** `ChatList v1.2.0`.
4. Описание — по шаблону `.github/RELEASE_NOTES_TEMPLATE.md`.
5. Прикрепите файлы из `dist\release\`:
   - `ChatList-1.2.0-Setup.exe`
   - `chatlist-1.2.0.exe`
   - `SHA256SUMS.txt`
6. Дополнительно: `dist\ChatList-1.2.0-portable.zip`.
7. **Publish release**.

### 3.3. Автоматическая сборка (CI)

Workflow `.github/workflows/release.yml` собирает релиз при push тега `v*`.

**Один раз настройте секрет:**

1. GitHub → репозиторий → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret:** имя `OPENROUTER_API_KEY`, значение — ваш ключ OpenRouter.

После push тега:

```powershell
git tag v1.2.0
git push origin v1.2.0
```

GitHub Actions соберёт exe, установщик и создаст Release автоматически.

---

## 4. GitHub Pages (лендинг)

### 4.1. Включение Pages

1. GitHub → репозиторий → **Settings** → **Pages**.
2. **Source:** Deploy from a branch.
3. **Branch:** `main`, папка **`/docs`**.
4. **Save**.

Сайт будет доступен по адресу:

```
https://ВАШ-USERNAME.github.io/ИМЯ-РЕПО/
```

### 4.2. Лендинг

Файл `docs/index.html` — готовая страница. После push в `main` подождите 1–2 минуты и откройте URL Pages.

Ссылки «Скачать» ведут на последний GitHub Release (`/releases/latest`).

### 4.3. Обновление лендинга

1. Отредактируйте `docs/index.html` (версия, текст, скриншоты).
2. `git commit` → `git push`.
3. Pages обновится автоматически.

---

## 5. Чеклист перед публикацией

- [ ] `version.py` обновлён
- [ ] `config\.env` с рабочим ключом (локально или секрет в GitHub)
- [ ] `.\config\build.ps1` прошёл без ошибок
- [ ] Portable exe запускается без дополнительных файлов
- [ ] Установщик ставит только exe; `data\` появляется после первого запуска
- [ ] Тег `vX.Y.Z` создан и запушен
- [ ] Release опубликован (вручную или через Actions)
- [ ] GitHub Pages включён, лендинг открывается

---

## 6. Безопасность

Ключ OpenRouter внутри exe **можно извлечь**. Для коммерческой продажи:

- ограничивайте лимиты на OpenRouter;
- при масштабе — свой backend-сервер вместо вшитого ключа.

`config\.env` и `dist\` не коммитьте в git.
