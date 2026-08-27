import re

from models.patient_task import PatientTask


def _normalize(text: str) -> str:
    if not text:
        return ""

    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\xa0", " ")
        .replace("\u200b", "")
    )

    # Keep new lines in clinical text, but normalize tabs and repeated spaces.
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _clean(value: str) -> str:
    if not value:
        return ""

    value = _normalize(value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip(" ;:|\n\t")


def _label_pattern(label: str) -> str:
    """
    Label may be separated from the previous field by:
    newline / semicolon / tab / many spaces / nothing except a word boundary.

    Colon is optional because some MIS clipboard variants copy:
      Описание
      ...
    instead of:
      Описание:
      ...
    """
    parts = [re.escape(part) for part in label.split()]
    return r"\b" + r"\s+".join(parts) + r"\b\s*:?\s*"


def _find_label(text: str, label: str, start: int = 0):
    return re.search(_label_pattern(label), text[start:], flags=re.IGNORECASE)


def _slice_between_labels(text: str, start_label: str, end_labels: list[str]) -> str:
    start = re.search(_label_pattern(start_label), text, flags=re.IGNORECASE)
    if not start:
        return ""

    content_start = start.end()
    tail = text[content_start:]

    positions = []
    for label in end_labels:
        m = re.search(_label_pattern(label), tail, flags=re.IGNORECASE)
        if m:
            positions.append(m.start())

    content_end = min(positions) if positions else len(tail)
    return _clean(tail[:content_end])


def _extract_date_after_label(text: str, label: str) -> str:
    m = re.search(
        _label_pattern(label) + r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return ""

    return m.group(1).replace("-", ".").replace("/", ".")


def _extract_study_date(text: str) -> str:
    """
    Prefer Date after 'Исследование'. If unavailable, use a plain 'Дата:' field
    that follows the study label.
    """
    study = re.search(_label_pattern("Исследование"), text, flags=re.IGNORECASE)
    if not study:
        return ""

    tail = text[study.end():]
    m = re.search(
        _label_pattern("Дата") + r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        tail,
        flags=re.IGNORECASE,
    )
    if not m:
        return ""

    return m.group(1).replace("-", ".").replace("/", ".")


def _extract_description(text: str) -> str:
    """
    STRICT rule:
      text after "Описание" and before "Заключение".

    Crucially, labels may be in ONE LINE:
      ... Доза: 0.1 Описание: aaa Заключение: bbb Врач: ...
    """
    return _slice_between_labels(
        text,
        "Описание",
        ["Заключение"],
    )


def _extract_conclusion(text: str) -> str:
    """
    STRICT rule:
      after "Заключение"
      until first:
        - "Врач" (with or without colon, including same line)
        - horizontal separator
        - end of input
    """
    start = re.search(_label_pattern("Заключение"), text, flags=re.IGNORECASE)
    if not start:
        return ""

    tail = text[start.end():]

    stops = []

    doctor = re.search(
        r"\bВрач\b\s*:?",
        tail,
        flags=re.IGNORECASE,
    )
    if doctor:
        stops.append(doctor.start())

    separator_patterns = [
        r"[_\-=—–─━]{4,}",
        r"[―]{4,}",
    ]
    for pattern in separator_patterns:
        sep = re.search(pattern, tail)
        if sep:
            stops.append(sep.start())

    end = min(stops) if stops else len(tail)
    return _clean(tail[:end])


def parse_stationary_xray_text(text: str) -> PatientTask:
    raw_text = _normalize(text or "")

    fio = _slice_between_labels(
        raw_text,
        "ФИО",
        ["Дата рождения"],
    )

    birth_date = _extract_date_after_label(raw_text, "Дата рождения")

    study_name = _slice_between_labels(
        raw_text,
        "Исследование",
        ["Дата", "Доза", "Описание", "Заключение"],
    )

    study_date = _extract_study_date(raw_text)

    dose = _slice_between_labels(
        raw_text,
        "Доза",
        ["Описание", "Заключение"],
    )

    description = _extract_description(raw_text)
    conclusion = _extract_conclusion(raw_text)

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

    missing = []

    if not fio:
        missing.append("ФИО")
    if not birth_date:
        missing.append("дата рождения")
    if not description:
        missing.append("описание")
    if not conclusion:
        missing.append("заключение")

    if missing:
        task.status = "pending_fix"
        task.note = "Не распознано: " + ", ".join(missing)

    return task
