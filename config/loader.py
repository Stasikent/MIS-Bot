from __future__ import annotations

import json
from pathlib import Path

from services.runtime_paths import CONFIG_DIR, config_path, tesseract_exe


def load_json(filename: str):
    path = config_path(filename)
    print(f"[CONFIG] loading {path}")

    if not path.exists():
        raise FileNotFoundError(f"Конфиг не найден: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[CONFIG] loaded {filename} => {data}")
    return data


def save_json(filename: str, data):
    path = CONFIG_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def save_setting(section: str, key: str, value):
    settings = load_json("settings.json")
    settings.setdefault(section, {})[key] = value
    save_json("settings.json", settings)

    # Обновляем модульные dict-и там, где это возможно.
    if section == "common":
        COMMON_SETTINGS[key] = value
    elif section == "mis":
        MIS_SETTINGS[key] = value
    elif section == "ris":
        RIS_SETTINGS[key] = value


settings = load_json("settings.json")
coordinates = load_json("coordinates.json")
templates = load_json("templates.json")
timings = load_json("timings.json")

COMMON_SETTINGS = settings.setdefault("common", {})
MIS_SETTINGS = settings.setdefault("mis", {})
RIS_SETTINGS = settings.setdefault("ris", {})

MIS_COORDS = coordinates.setdefault("mis", {})
RIS_COORDS = coordinates.setdefault("ris", {})

MIS_TEMPLATES = templates.setdefault("mis", {})
RIS_TEMPLATES = templates.setdefault("ris", {})

# Портативная версия: если путь из settings.json отсутствует,
# используем tesseract рядом с приложением.
configured_tesseract = str(COMMON_SETTINGS.get("tesseract_path", "") or "").strip()
if not configured_tesseract or not Path(configured_tesseract).exists():
    portable = tesseract_exe()
    if portable.exists():
        COMMON_SETTINGS["tesseract_path"] = str(portable)

