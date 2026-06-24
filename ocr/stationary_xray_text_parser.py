import re

from models.patient_task import PatientTask


def _clean(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip(" ;\n\t")


def _extract_one(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return default
    return _clean(m.group(1))


def parse_stationary_xray_text(text: str) -> PatientTask:
    raw_text = text.strip()

    fio = _extract_one(
        r"ФИО\s*:\s*(.*?)(?:;|\n)\s*Дата\s+рождения",
        raw_text,
    )

    birth_date = _extract_one(
        r"Дата\s+рождения\s*:\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        raw_text,
    ).replace("-", ".").replace("/", ".")

    study_name = _extract_one(
        r"Исследование\s*:\s*(.*?)(?:;|\n)\s*Дата\s*:",
        raw_text,
    )

    study_date = _extract_one(
        r"Исследование\s*:.*?Дата\s*:\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        raw_text,
    ).replace("-", ".").replace("/", ".")

    dose = _extract_one(
        r"Доза\s*:\s*(.*?)(?:;|\n)",
        raw_text,
    )

    description = _extract_one(
        r"Описание\s*:\s*(.*?)(?:\n\s*Заключение\s*:)",
        raw_text,
    )

    conclusion = _extract_one(
        r"Заключение\s*:\s*(.*?)(?:_{5,}|Врач\s*:|$)",
        raw_text,
    )

    task = PatientTask(
        fio=fio,
        birth_date=birth_date,
        study_date=study_date,
        mode="xray",
        status="pending",
        source="text",
        note="",
        task_type="xray",
        study_name=study_name,
        dose=dose,
        description=description,
        conclusion=conclusion,
        raw_text=raw_text,
    )

    if not fio or not birth_date:
        task.status = "pending_fix"
        task.note = "Не распознаны ФИО или дата рождения"

    return task