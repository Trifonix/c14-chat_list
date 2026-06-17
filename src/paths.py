"""Общие пути проекта ChatList."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def resolve_root_dir() -> Path:
    """Корень данных приложения.

    В режиме разработки — каталог проекта.
    В собранном exe — каталог, где лежит исполняемый файл (portable / установка).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT_DIR = resolve_root_dir()
SRC_DIR = ROOT_DIR / "src" if not is_frozen() else ROOT_DIR
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
DOCS_DIR = ROOT_DIR / "docs"
LOG_FILE = DATA_DIR / "chatlist.log"
ENV_FILE = CONFIG_DIR / ".env"


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def bundled_env_file() -> Path | None:
    """Встроенный при сборке .env (PyInstaller _MEIPASS/config/.env)."""
    if not is_frozen():
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    candidate = Path(meipass) / "config" / ".env"
    return candidate if candidate.exists() else None
