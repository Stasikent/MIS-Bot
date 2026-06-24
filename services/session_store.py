import json
from pathlib import Path

from models.patient_task import PatientTask


ROOT_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT_DIR / "config" / "runtime"
SESSION_PATH = RUNTIME_DIR / "session.json"


def save_session(tasks: list[PatientTask]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "tasks": [task.to_dict() for task in tasks]
    }

    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return SESSION_PATH


def load_session() -> list[PatientTask]:
    if not SESSION_PATH.exists():
        return []

    with open(SESSION_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_tasks = data.get("tasks", [])
    return [PatientTask.from_dict(item) for item in raw_tasks]


def clear_session():
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()