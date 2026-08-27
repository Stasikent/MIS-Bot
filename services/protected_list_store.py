import base64
import hashlib
import inspect
import json
import os
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path

from services.runtime_paths import CONFIG_DIR
from models.patient_task import PatientTask

PROFILE_PATH = CONFIG_DIR / "list_profile.json"
ITERATIONS = 300_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode("ascii"))


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32)


def _fernet(key: bytes):
    try:
        from cryptography.fernet import Fernet
    except ImportError as e:
        raise RuntimeError("Для защищённых списков нужен пакет cryptography. Установите: pip install cryptography") from e
    return Fernet(base64.urlsafe_b64encode(key))


def load_profile():
    try:
        if PROFILE_PATH.exists():
            return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def save_profile(fio: str, password: str):
    fio = (fio or "").strip()
    if not fio or not password:
        raise ValueError("ФИО и пароль не могут быть пустыми")
    salt = os.urandom(16)
    verifier = _derive(password, salt)
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps({"fio": fio, "salt": _b64(salt), "verifier": _b64(verifier)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return fio


def verify_profile_password(password: str) -> bool:
    import hmac
    p = load_profile()
    if not p:
        return False
    actual = _derive(password, _unb64(p["salt"]))
    return hmac.compare_digest(actual, _unb64(p["verifier"]))


def _task_to_dict(task):
    if is_dataclass(task):
        return asdict(task)
    return dict(vars(task))


def save_protected_list(path, tasks, fio: str, password: str):
    fio = (fio or "").strip()
    if not fio or not password:
        raise ValueError("Нужны ФИО профиля и пароль")
    salt = os.urandom(16)
    key = _derive(password, salt)
    payload = json.dumps({"version": 1, "tasks": [_task_to_dict(t) for t in tasks]}, ensure_ascii=False).encode("utf-8")
    token = _fernet(key).encrypt(payload).decode("ascii")
    wrapper = {"format": "mislist", "version": 1, "owner": fio, "salt": _b64(salt), "iterations": ITERATIONS, "data": token}
    Path(path).write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")


def peek_owner(path) -> str:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != "mislist":
        raise ValueError("Это не файл сохранённого списка MIS Bot")
    return str(data.get("owner", "")).strip()


def load_protected_list(path, fio: str, password: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != "mislist":
        raise ValueError("Это не файл сохранённого списка MIS Bot")
    owner = str(data.get("owner", "")).strip()
    if owner.casefold() != (fio or "").strip().casefold():
        raise ValueError("ФИО профиля не совпадает с владельцем списка")
    key = _derive(password, _unb64(data["salt"]))
    try:
        raw = _fernet(key).decrypt(data["data"].encode("ascii"))
    except Exception as e:
        raise ValueError("Неверный пароль или файл повреждён") from e
    payload = json.loads(raw.decode("utf-8"))
    return [_dict_to_task(x) for x in payload.get("tasks", [])]


def _dict_to_task(data: dict):
    params = inspect.signature(PatientTask).parameters
    kwargs = {k: v for k, v in data.items() if k in params}
    task = PatientTask(**kwargs)
    for k, v in data.items():
        try:
            setattr(task, k, v)
        except Exception:
            pass
    return task


def ensure_unique_id(task, existing_ids):
    if not getattr(task, "id", None) or task.id in existing_ids:
        task.id = str(uuid.uuid4())
    return task
