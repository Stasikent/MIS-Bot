import re
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, ImageFilter

from config.loader import COMMON_SETTINGS
from models.patient_task import PatientTask


pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]


DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",   # 2003-12-25
    r"\b\d{2}\.\d{2}\.\d{4}\b", # 25.12.2003
]


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def keep_cyrillic_only(text: str) -> str:
    text = re.sub(r"[^А-Яа-яЁё\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_fio(text: str) -> str:
    text = keep_cyrillic_only(text)

    words = text.split()
    words = words[:3]

    fixed = []
    for w in words:
        if w:
            fixed.append(w[:1].upper() + w[1:].lower())

    return " ".join(fixed)

def normalize_birth_date_for_task(value: str) -> str:
    value = value.strip()

    # yyyy-mm-dd -> dd.mm.yyyy
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        y, m, d = value.split("-")
        return f"{d}.{m}.{y}"

    # dd.mm.yyyy -> 그대로
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        return value

    return value


def extract_date_from_line(line: str):
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, line)
        if m:
            return m.group(0)
    return None


def preprocess_list_image(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def ocr_image_to_text(image_path: str | Path) -> str:
    img = Image.open(image_path)
    prepared = preprocess_list_image(img)

    variants = []
    for psm in (6, 11, 4):
        text = pytesseract.image_to_string(
            prepared,
            lang="rus+eng",
            config=f"--psm {psm} -c tessedit_char_whitelist=АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя0123456789.- "
        )
        if text.strip():
            variants.append(text)

    if not variants:
        return ""

    return max(variants, key=len)


def parse_patients_from_ocr_text(raw_text: str, default_mode="normal"):
    tasks = []

    lines = [normalize_spaces(x) for x in raw_text.splitlines()]
    lines = [x for x in lines if x]

    for line in lines:
        date_text = extract_date_from_line(line)
        if not date_text:
            continue

        date_pos = line.find(date_text)
        fio = line[:date_pos].strip() if date_pos != -1 else line
        fio = normalize_fio(fio)

        # отбрасываем мусор
        if len(fio.split()) < 2:
            continue
        
        # отсекаем мусорные строки
        if any(x in fio.lower() for x in ["дата", "врач", "кабинет", "прием"]):
            continue

        birth_date = normalize_birth_date_for_task(date_text)

        task = PatientTask(
            fio=fio,
            birth_date=birth_date,
            study_date="",
            mode=default_mode,
            status="pending",
            note="",
            source="screen"
        )
        tasks.append(task)

    return tasks


def parse_screen_region(image_path: str | Path, mode="normal"):
    raw_text = ocr_image_to_text(image_path)
    tasks = parse_patients_from_ocr_text(raw_text, default_mode=mode)

    if not tasks:
        raise ValueError("Не удалось распознать ни одной записи из выделенной области.")

    if len(tasks) == 1:
        return tasks[0]

    return tasks