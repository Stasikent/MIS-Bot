import re
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, ImageFilter

from config.loader import COMMON_SETTINGS
from models.patient_task import PatientTask


pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def preprocess_fio_image(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def preprocess_date_image(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.resize((gray.width * 3, gray.height * 3))
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def ocr_fio(image_path: str | Path) -> str:
    img = Image.open(image_path)
    prepared = preprocess_fio_image(img)

    variants = []
    for psm in (7, 6, 11):
        text = pytesseract.image_to_string(
            prepared,
            lang="rus+eng",
            config=f"--psm {psm}"
        )
        text = normalize_spaces(text.replace("\n", " "))
        if text:
            variants.append(text)

    if not variants:
        return ""

    fio = max(variants, key=len)
    fio = fio.strip(" .,:;|-")
    fio = normalize_spaces(fio)
    return fio


def normalize_birth_date_for_task(value: str) -> str:
    value = value.strip()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        y, m, d = value.split("-")
        return f"{d}.{m}.{y}"

    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", value):
        return value

    if re.fullmatch(r"\d{8}", value):
        # ddmmyyyy
        return f"{value[0:2]}.{value[2:4]}.{value[4:8]}"

    return value


def extract_birth_date(text: str) -> str | None:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}\.\d{2}\.\d{4}\b",
        r"\b\d{8}\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return normalize_birth_date_for_task(m.group(0))

    return None


def ocr_birth_date(image_path: str | Path) -> str:
    img = Image.open(image_path)
    prepared = preprocess_date_image(img)

    variants = []
    for psm in (7, 13, 6):
        text = pytesseract.image_to_string(
            prepared,
            lang="eng",
            config=f"--psm {psm} -c tessedit_char_whitelist=0123456789.-"
        )
        text = text.strip()
        if text:
            variants.append(text)

    for text in variants:
        date_value = extract_birth_date(text)
        if date_value:
            return date_value

    raise ValueError("Не удалось распознать дату рождения")


def build_task_from_two_regions(fio_image_path: str | Path, birth_image_path: str | Path, mode="normal") -> PatientTask:
    fio = ocr_fio(fio_image_path)

    if len(fio.split()) < 2:
        raise ValueError(f"Не удалось надёжно распознать ФИО: {fio!r}")

    try:
        birth_date = ocr_birth_date(birth_image_path)
        note = ""
        status = "pending"
    except Exception:
        birth_date = "ЗАМЕНИТЬ"
        note = "Дата рождения не распознана"
        status = "pending_fix"

    return PatientTask(
        fio=fio,
        birth_date=birth_date,
        study_date="",
        mode=mode,
        status=status,
        note=note,
        source="screen_two_step",
    )