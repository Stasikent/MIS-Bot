from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def app_dir() -> Path:
    """
    Папка рядом с EXE для рабочей onedir-версии.
    При запуске из исходников — корень проекта.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _source_root()


def bundle_dir() -> Path:
    """
    Read-only/встроенные ресурсы PyInstaller.
    Для исходников совпадает с корнем проекта.
    """
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve()
    return _source_root()


APP_DIR = app_dir()
BUNDLE_DIR = bundle_dir()

CONFIG_DIR = APP_DIR / "config"
PROJECT_DIR = APP_DIR / "project"
TEMPLATES_DIR = PROJECT_DIR / "templates"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = APP_DIR / "data"
NAMES_DIR = DATA_DIR / "names"
TESSERACT_DIR = APP_DIR / "tesseract"

BUNDLE_CONFIG_DIR = BUNDLE_DIR / "config"
BUNDLE_PROJECT_DIR = BUNDLE_DIR / "project"
BUNDLE_TEMPLATES_DIR = BUNDLE_PROJECT_DIR / "templates"
BUNDLE_DATA_DIR = BUNDLE_DIR / "data"
BUNDLE_NAMES_DIR = BUNDLE_DATA_DIR / "names"
BUNDLE_TESSERACT_DIR = BUNDLE_DIR / "tesseract"


def ensure_runtime_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    NAMES_DIR.mkdir(parents=True, exist_ok=True)


def ensure_external_file(relative_path: str) -> Path:
    """
    Если внешний рабочий файл отсутствует, копируем начальный вариант
    из ресурсов PyInstaller. Уже существующий файл никогда не перезаписываем.
    """
    ensure_runtime_dirs()

    dst = APP_DIR / relative_path
    if dst.exists():
        return dst

    src = BUNDLE_DIR / relative_path
    if src.exists() and src.is_file() and src.resolve() != dst.resolve():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return dst


def config_path(name: str) -> Path:
    """
    Return a writable workstation config path.

    Private settings.json and coordinates.json are intentionally not tracked by
    Git. On a fresh source checkout (or a build that contains only examples),
    bootstrap them once from the corresponding *.example.json files.
    Existing workstation files are never overwritten.
    """
    dst = ensure_external_file(f"config/{name}")
    if dst.exists():
        return dst

    example_names = {
        "settings.json": "settings.example.json",
        "coordinates.json": "coordinates.example.json",
    }
    example_name = example_names.get(name)
    if not example_name:
        return dst

    candidates = [
        CONFIG_DIR / example_name,
        BUNDLE_CONFIG_DIR / example_name,
    ]
    for src in candidates:
        try:
            if src.exists() and src.is_file() and src.resolve() != dst.resolve():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                return dst
        except OSError:
            continue

    return dst


def template_path(filename: str) -> Path:
    external = TEMPLATES_DIR / filename
    if external.exists():
        return external

    bundled = BUNDLE_TEMPLATES_DIR / filename
    if bundled.exists():
        return bundled

    return external


def names_dir() -> Path:
    required = ("surnames.txt", "first_names.txt", "patronymics.txt")

    if all((NAMES_DIR / name).exists() for name in required):
        return NAMES_DIR

    if all((BUNDLE_NAMES_DIR / name).exists() for name in required):
        return BUNDLE_NAMES_DIR

    return NAMES_DIR


def tesseract_exe() -> Path:
    external = TESSERACT_DIR / "tesseract.exe"
    if external.exists():
        return external

    bundled = BUNDLE_TESSERACT_DIR / "tesseract.exe"
    if bundled.exists():
        return bundled

    return external


ensure_runtime_dirs()
