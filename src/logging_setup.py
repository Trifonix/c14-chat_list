"""Настройка файлового логирования."""

from __future__ import annotations

import logging

from app_meta import APP_NAME, APP_VERSION
from paths import DATA_DIR, LOG_FILE, ensure_data_dir

# Re-export for tests.
__all__ = ["LOG_FILE", "setup_logging"]


def setup_logging() -> None:
    ensure_data_dir()
    root = logging.getLogger()
    if any(isinstance(handler, logging.FileHandler) for handler in root.handlers):
        return

    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("chatlist").info(
        "%s %s started (data: %s)", APP_NAME, APP_VERSION, DATA_DIR
    )
