"""Загрузка __version__ из version.py для spec-файлов и скриптов сборки."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "version.py"
    spec = importlib.util.spec_from_file_location("_app_version", version_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить версию из {version_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__
