import json
import sys
from pathlib import Path

# При запуске из EXE PyInstaller распаковывает ресурсы во временную папку,
# но config удобнее читать рядом с самим exe.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    EXE_DIR = Path(sys.executable).resolve().parent
    CONFIG_DIR = EXE_DIR / "config"
else:
    BASE_DIR = Path(__file__).resolve().parent
    EXE_DIR = None
    CONFIG_DIR = BASE_DIR

print("[CONFIG] BASE_DIR =", BASE_DIR)
if EXE_DIR is not None:
    print("[CONFIG] EXE_DIR =", EXE_DIR)
print("[CONFIG] CONFIG_DIR =", CONFIG_DIR)


def load_json(name: str) -> dict:
    path = CONFIG_DIR / name

    if not path.exists():
        raise FileNotFoundError(f"Не найден config файл: {path}")

    print("[CONFIG] loading", path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("[CONFIG] loaded", name, "=>", data)
    return data

def save_json(name: str, data: dict):
    path = CONFIG_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("[CONFIG] saved", path)

def save_setting(section: str, key: str, value):
    data = load_json("settings.json")

    if section not in data:
        data[section] = {}

    data[section][key] = value

    save_json("settings.json", data)

settings = load_json("settings.json")
coords = load_json("coordinates.json")
templates = load_json("templates.json")
timings = load_json("timings.json")

COMMON_SETTINGS = settings.get("common", {})
MIS_SETTINGS = settings.get("mis", {})
RIS_SETTINGS = settings.get("ris", {})

MIS_COORDS = coords.get("mis", coords)
RIS_COORDS = coords.get("ris", coords)

MIS_TEMPLATES = templates.get("mis", templates)
RIS_TEMPLATES = templates.get("ris", templates)