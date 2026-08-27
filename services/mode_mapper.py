import json
from pathlib import Path
from services.runtime_paths import config_path

PROTOCOLS_PATH = config_path("protocols.json")

_FALLBACK = [
    {"key": "normal", "name": "Норма", "template_key": "template_row_normal", "aliases": ["норма"]},
    {"key": "cardiomegaly", "name": "Кардиомегалия", "template_key": "template_row_cardiomegaly", "aliases": ["кардиомегалия"]},
    {"key": "two_projections", "name": "2 Проекции", "template_key": "template_row_two_projections", "aliases": ["2 проекции", "две проекции"]},
    {"key": "manual_edit", "name": "Свой протокол", "template_key": "template_row_normal", "aliases": ["свой протокол"]},
]

def load_protocols(section="fluoro"):
    try:
        data = json.loads(PROTOCOLS_PATH.read_text(encoding="utf-8"))
        items = data.get(section, [])
        return items if isinstance(items, list) and items else list(_FALLBACK if section == "fluoro" else [])
    except Exception:
        return list(_FALLBACK if section == "fluoro" else [])

def get_ui_mode_to_internal():
    return {item["name"]: item["key"] for item in load_protocols("fluoro")}

def get_internal_to_ui_mode():
    return {item["key"]: item["name"] for item in load_protocols("fluoro")}

def get_protocol_template_key(internal_key, section="fluoro"):
    for item in load_protocols(section):
        if item.get("key") == internal_key:
            return item.get("template_key")
    return None

def get_protocol_names(section="fluoro"):
    return [item.get("name", item.get("key", "")) for item in load_protocols(section)]

# Backward compatibility for existing imports.
UI_MODE_TO_INTERNAL = get_ui_mode_to_internal()
INTERNAL_TO_UI_MODE = get_internal_to_ui_mode()


def refresh_mode_maps():
    global UI_MODE_TO_INTERNAL, INTERNAL_TO_UI_MODE
    UI_MODE_TO_INTERNAL = get_ui_mode_to_internal()
    INTERNAL_TO_UI_MODE = get_internal_to_ui_mode()
    return UI_MODE_TO_INTERNAL, INTERNAL_TO_UI_MODE
