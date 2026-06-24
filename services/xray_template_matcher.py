import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "xray_template_map.json"


def normalize_text(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def match_xray_template(study_name: str) -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    normalized = normalize_text(study_name)

    for rule in data.get("rules", []):
        for kw in rule.get("keywords", []):
            if normalize_text(kw) in normalized:
                return rule

    return {
        "template_key": data.get("default"),
        "template_name": "default",
        "keywords": [],
    }