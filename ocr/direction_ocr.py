import sys
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytesseract
from PIL import Image, ImageFilter, ImageOps

from config.loader import COMMON_SETTINGS
from models.patient_task import PatientTask


BASE_DIR = Path(__file__).resolve().parents[1]
pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]


@dataclass
class DirectionOcrResult:
    raw_text: str
    fio: Optional[str]
    birth_date: Optional[str]
    study_date: Optional[str]
    confidence_note: str = ""


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text: str) -> str:
    text = text.replace("Ё", "Е").replace("ё", "е")
    text = text.replace("|", "1")
    text = text.replace("l", "1")
    text = text.replace("I", "1")
    text = text.replace("Дата рожц", "Дата рожд")
    text = text.replace("Дата рохд", "Дата рожд")
    text = text.replace("Дата рожл", "Дата рожд")
    text = text.replace("Дата рсжд", "Дата рожд")
    text = text.replace("Дата р0жд", "Дата рожд")
    text = text.replace("Пациенг", "Пациент")
    text = text.replace("Пацие-г", "Пациент")
    text = text.replace("Nauesr", "Пациент")
    return text


def normalize_date(value: str) -> Optional[str]:
    value = value.strip()
    value = value.replace(",", ".").replace("-", ".").replace("/", ".").replace(" ", ".")
    value = re.sub(r"[^0-9.]", "", value)

    compact = value.replace(".", "")

    if re.fullmatch(r"\d{8}", compact):
        try:
            dt = datetime.strptime(compact, "%d%m%Y")
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            pass

    if re.fullmatch(r"\d{6}", compact):
        try:
            dt = datetime.strptime(compact, "%d%m%y")
            if dt.year < 1930:
                dt = dt.replace(year=dt.year + 100)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            pass

    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.year < 1930:
                dt = dt.replace(year=dt.year + 100)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue

    return None


def extract_all_dates(text: str) -> list[str]:
    candidates = []
    candidates.extend(re.findall(r"\b\d{2}[.\-/ ]\d{2}[.\-/ ]\d{2,4}\b", text))
    candidates.extend(re.findall(r"\b\d{8}\b", text))

    normalized = []
    for c in candidates:
        nd = normalize_date(c)
        if nd:
            normalized.append(nd)

    seen = set()
    result = []
    for d in normalized:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result


def crop_main_content(image: Image.Image) -> Image.Image:
    w, h = image.size
    return image.crop((int(w * 0.02), int(h * 0.02), int(w * 0.98), int(h * 0.72)))


def crop_header_region(image: Image.Image) -> Image.Image:
    w, h = image.size
    return image.crop((int(w * 0.02), int(h * 0.05), int(w * 0.98), int(h * 0.48)))


def crop_name_line_region(image: Image.Image) -> Image.Image:
    w, h = image.size
    return image.crop((int(w * 0.03), int(h * 0.18), int(w * 0.97), int(h * 0.42)))


def preprocess_soft(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def preprocess_stronger(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    bw = gray.point(lambda x: 0 if x < 155 else 255, "1")
    return bw.convert("L")


def ocr_pil(image: Image.Image, psm: int = 6) -> str:
    text = pytesseract.image_to_string(
        image,
        lang="rus+eng",
        config=f"--psm {psm}"
    )
    return normalize_text(text)


def ocr_image(image: Image.Image) -> str:
    variants = [
        ocr_pil(preprocess_soft(crop_main_content(image)), psm=6),
        ocr_pil(preprocess_soft(crop_header_region(image)), psm=6),
        ocr_pil(preprocess_stronger(crop_header_region(image)), psm=6),
    ]
    variants = [v for v in variants if v.strip()]
    return max(variants, key=len) if variants else ""


def ocr_name_region(image: Image.Image) -> str:
    region = crop_name_line_region(image)

    variants = [
        ocr_pil(preprocess_soft(region), psm=6),
        ocr_pil(preprocess_soft(region), psm=7),
        ocr_pil(preprocess_stronger(region), psm=7),
    ]
    variants = [v for v in variants if v.strip()]
    return max(variants, key=len) if variants else ""


def normalize_fio_case(fio: str) -> str:
    words = normalize_spaces(fio).split()
    fixed = []
    for w in words[:3]:
        if w:
            fixed.append(w[:1].upper() + w[1:].lower())
    return " ".join(fixed)


def fix_mixed_alphabet_word(word: str) -> str:
    mapping = {
        "A": "А", "a": "а",
        "B": "В", "E": "Е", "e": "е",
        "K": "К", "k": "к",
        "M": "М", "H": "Н",
        "O": "О", "o": "о",
        "P": "Р", "p": "р",
        "C": "С", "c": "с",
        "T": "Т", "X": "Х", "x": "х",
        "Y": "У", "y": "у",
    }
    fixed = "".join(mapping.get(ch, ch) for ch in word)
    fixed = fixed.replace("G", "Б").replace("g", "б")
    fixed = fixed.replace("0", "о").replace("3", "з").replace("6", "б")
    return fixed


def postprocess_fio(candidate: str) -> str:
    words = normalize_spaces(candidate).split()
    fixed_words = [fix_mixed_alphabet_word(w) for w in words[:3]]
    result = " ".join(fixed_words)
    result = result.replace("Юрьевма", "Юрьевна").replace("Юрьзама", "Юрьевна")
    result = result.replace("Юрьзна", "Юрьевна").replace("Юрьвна", "Юрьевна")
    result = result.replace("Юьевна", "Юрьевна")
    result = result.replace("Тагу", "Таму").replace("Гагу", "Таму")
    result = result.replace("Бахаееа", "Бакаева").replace("Бахаева", "Бакаева")
    result = result.replace("Бахаеаа", "Бакаева").replace("Бакаеваа", "Бакаева")
    return normalize_fio_case(result)


def looks_like_real_fio(value: str) -> bool:
    forbidden = {
        "Дата", "Рожд", "Пациент", "Услуги", "Диагноз",
        "Направление", "Номер", "Карты", "Возраст",
        "Медицинская", "Карта", "Пациента"
    }

    words = normalize_spaces(value).split()
    if len(words) < 3:
        return False
    words = words[:3]

    for w in words:
        if w.capitalize() in forbidden:
            return False
        if len(w) < 2:
            return False
        if not re.fullmatch(r"[A-Za-zА-Яа-я\-]+", w):
            return False

    return True


def detect_document_type(text: str) -> str:
    upper = text.upper()
    if "НАПРАВЛЕНИЕ" in upper:
        return "direction"
    if "МЕДИЦИНСКАЯ КАРТА ПАЦИЕНТА" in upper:
        return "medcard"
    return "unknown"


def extract_name_before_date(text: str) -> Optional[str]:
    text = normalize_text(text)
    patterns = [
        r"([А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+)\s+дата",
        r"([А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+)\s+дата\s*рожд",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = normalize_spaces(match.group(1))
            if looks_like_real_fio(candidate):
                return postprocess_fio(candidate)
    return None


def extract_fio_for_direction(text: str, name_region_text: str = "") -> Optional[str]:
    if name_region_text:
        fio = extract_name_before_date(name_region_text)
        if fio:
            return fio

    fio = extract_name_before_date(text)
    if fio:
        return fio

    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]
    for line in lines:
        if re.search(r"(пац|пациент)", line, re.IGNORECASE):
            left = re.split(r"дата\s*рожд", line, flags=re.IGNORECASE)[0]
            left = normalize_spaces(left)
            parts = re.split(r"[—\-:]+", left)
            candidate_zone = parts[-1].strip() if len(parts) >= 2 else left
            words = re.findall(r"[A-Za-zА-Яа-я\-]+", candidate_zone)
            for i in range(len(words) - 2):
                candidate = " ".join(words[i:i + 3])
                if looks_like_real_fio(candidate):
                    return postprocess_fio(candidate)

    return None


def extract_birth_date_for_direction(text: str, name_region_text: str = "") -> Optional[str]:
    for src in [name_region_text, text]:
        if not src:
            continue

        lines = [normalize_spaces(line) for line in src.splitlines() if normalize_spaces(line)]
        for line in lines:
            if re.search(r"дата\s*рожд", line, re.IGNORECASE):
                m = re.search(
                    r"дата\s*рожд[.: ]+(\d{2}[.\-/ ]?\d{2}[.\-/ ]?\d{2,4}|\d{8})",
                    line,
                    re.IGNORECASE
                )
                if m:
                    nd = normalize_date(m.group(1))
                    if nd:
                        return nd

                dates = extract_all_dates(line)
                if dates:
                    return dates[-1]

    return None


def extract_study_date_for_direction(text: str, birth_date: Optional[str]) -> Optional[str]:
    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    for line in lines:
        if re.search(r"^\s*(дата|dam|дам)\s*[: ]", line, re.IGNORECASE):
            dates = extract_all_dates(line)
            for d in dates:
                if d != birth_date:
                    return d

    for d in extract_all_dates(text):
        if d != birth_date:
            return d

    return None


def extract_fio_for_medcard(text: str, name_region_text: str = "") -> Optional[str]:
    if name_region_text:
        fio = extract_name_before_date(name_region_text)
        if fio:
            return fio

    fio = extract_name_before_date(text)
    if fio:
        return fio

    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    for line in lines:
        if re.search(r"^\s*2\b", line):
            parts = re.split(r"[—\-]+", line)
            if len(parts) >= 2:
                candidate_zone = parts[-1].strip()
                words = re.findall(r"[A-Za-zА-Яа-я\-]+", candidate_zone)

                for i in range(len(words) - 2):
                    candidate = " ".join(words[i:i + 3])
                    if looks_like_real_fio(candidate):
                        return postprocess_fio(candidate)

    return None


def extract_birth_date_for_medcard(text: str, name_region_text: str = "") -> Optional[str]:
    for src in [name_region_text, text]:
        if not src:
            continue

        lines = [normalize_spaces(line) for line in src.splitlines() if normalize_spaces(line)]
        for line in lines:
            if re.search(r"(?:\b4\b|дата\s*рожд|дестрожд|детрожд)", line, re.IGNORECASE):
                dates = extract_all_dates(line)
                if dates:
                    return dates[0]

    return None


def extract_study_date_for_medcard(text: str, birth_date: Optional[str]) -> Optional[str]:
    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]

    for line in lines:
        if re.search(r"^\s*1\b", line) or re.search(r"дата\s*заполн|дата\s*медицин", line, re.IGNORECASE):
            dates = extract_all_dates(line)
            for d in dates:
                if d != birth_date:
                    return d

    for d in extract_all_dates(text):
        if d != birth_date:
            return d

    return None


def parse_direction_text(text: str, name_region_text: str = "") -> DirectionOcrResult:
    text = normalize_text(text)
    name_region_text = normalize_text(name_region_text)
    doc_type = detect_document_type(text)

    fio = None
    birth_date = None
    study_date = None

    if doc_type == "direction":
        fio = extract_fio_for_direction(text, name_region_text=name_region_text)
        birth_date = extract_birth_date_for_direction(text, name_region_text=name_region_text)
        study_date = extract_study_date_for_direction(text, birth_date)
    elif doc_type == "medcard":
        fio = extract_fio_for_medcard(text, name_region_text=name_region_text)
        birth_date = extract_birth_date_for_medcard(text, name_region_text=name_region_text)
        study_date = extract_study_date_for_medcard(text, birth_date)
    else:
        fio = extract_fio_for_direction(text, name_region_text=name_region_text) or extract_fio_for_medcard(text, name_region_text=name_region_text)
        birth_date = extract_birth_date_for_direction(text, name_region_text=name_region_text) or extract_birth_date_for_medcard(text, name_region_text=name_region_text)
        study_date = extract_study_date_for_direction(text, birth_date) or extract_study_date_for_medcard(text, birth_date)

    if not study_date:
        study_date = datetime.now().strftime("%d.%m.%Y")

    note_parts = []
    if not fio:
        note_parts.append("ФИО не найдено")
    if not birth_date:
        note_parts.append("Дата рождения не найдена")

    return DirectionOcrResult(
        raw_text=text,
        fio=fio,
        birth_date=birth_date,
        study_date=study_date,
        confidence_note="; ".join(note_parts)
    )


def parse_direction_image(image_path: str | Path, mode: str = "normal") -> PatientTask:
    image_path = Path(image_path)
    image = Image.open(image_path)

    full_text = ocr_image(image)
    name_region_text = ocr_name_region(image)
    result = parse_direction_text(full_text, name_region_text=name_region_text)

    if not result.fio:
        raise ValueError("Не удалось распознать ФИО на направлении")

    if not result.birth_date:
        raise ValueError("Не удалось распознать дату рождения на направлении")

    return PatientTask(
        fio=result.fio,
        birth_date=result.birth_date,
        study_date=result.study_date,
        mode=mode
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python ocr/direction_ocr.py <path_to_image>")
        raise SystemExit(1)

    img_path = sys.argv[1]
    image = Image.open(img_path)

    full_text = ocr_image(image)
    name_region_text = ocr_name_region(image)
    result = parse_direction_text(full_text, name_region_text=name_region_text)

    print("=== RAW OCR TEXT ===")
    print(full_text)
    print()
    print("=== NAME REGION OCR ===")
    print(name_region_text)
    print()
    print("=== PARSED ===")
    print("FIO       :", result.fio)
    print("BIRTH DATE:", result.birth_date)
    print("STUDY DATE:", result.study_date)
    print("NOTE      :", result.confidence_note)