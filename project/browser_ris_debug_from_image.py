import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from config.loader import COMMON_SETTINGS, RIS_SETTINGS, RIS_COORDS


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]

DEFAULT_CARD_REGION = RIS_COORDS["debug_card_region"]
DEFAULT_BIRTH_REGION_INSIDE_CARD = RIS_COORDS["birth_region_inside_card"]
VALID_SERVICE_SUBSTRINGS = RIS_SETTINGS["valid_service_substrings"]


@dataclass
class RisCardOcrResult:
    raw_text: str
    fio: Optional[str]
    birth_date: Optional[str]
    service_ok: bool


def now_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text: str) -> str:
    text = text.replace("Ё", "Е").replace("ё", "е")
    text = text.replace("|", "1")
    text = text.replace("I", "1")
    text = text.replace("l", "1")
    text = text.replace(",", ".")
    return text


def normalize_compare_text(text: str) -> str:
    text = normalize_text(text).lower()
    text = re.sub(r"[^a-zа-я0-9\s.\-]", " ", text)
    return normalize_spaces(text)


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


def extract_dates(text: str) -> list[str]:
    raw = re.findall(r"\b\d{2}[.\-/ ]\d{2}[.\-/ ]\d{2,4}\b|\b\d{8}\b", text)
    result = []
    seen = set()

    for item in raw:
        nd = normalize_date(item)
        if nd and nd not in seen:
            seen.add(nd)
            result.append(nd)

    return result


def normalize_fio_case(fio: str) -> str:
    words = normalize_spaces(fio).split()
    return " ".join(w[:1].upper() + w[1:].lower() for w in words[:3])


def fix_common_fio_ocr(candidate: str) -> str:
    words = normalize_spaces(candidate).split()[:3]

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

    fixed_words = []
    for word in words:
        fixed = "".join(mapping.get(ch, ch) for ch in word)
        fixed = fixed.replace("0", "о").replace("3", "з").replace("6", "б")
        fixed_words.append(fixed)

    return normalize_fio_case(" ".join(fixed_words))


def looks_like_real_fio(value: str) -> bool:
    forbidden = {
        "Код", "Услуги", "Снилс", "Номер", "Направления", "Из", "Мис",
        "Рентгенография", "Флюорография", "Грудной", "Клетки"
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


def extract_fio(text: str) -> Optional[str]:
    text = normalize_spaces(text)

    patterns = [
        r"([А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+\s+[А-ЯA-Z][A-Za-zА-Яа-я\-]+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            candidate = fix_common_fio_ocr(match)
            if looks_like_real_fio(candidate):
                return candidate

    words = re.findall(r"[A-Za-zА-Яа-я\-]+", text)
    for i in range(len(words) - 2):
        candidate = " ".join(words[i:i+3])
        candidate = fix_common_fio_ocr(candidate)
        if looks_like_real_fio(candidate):
            return candidate

    return None


def fio_matches(task_fio: str, ocr_fio: str) -> bool:
    task_norm = normalize_compare_text(task_fio)
    ocr_norm = normalize_compare_text(ocr_fio)

    task_words = task_norm.split()
    ocr_words = ocr_norm.split()

    if len(task_words) < 2 or len(ocr_words) < 2:
        return False

    matched = sum(1 for w in task_words[:3] if w in ocr_words[:3])
    return matched >= 2


def service_matches_text(text: str) -> bool:
    t = normalize_compare_text(text)
    return any(s in t for s in VALID_SERVICE_SUBSTRINGS)


def crop_region(image: Image.Image, left: int, top: int, width: int, height: int) -> Image.Image:
    return image.crop((left, top, left + width, top + height))


def save_region_preview(image: Image.Image, left: int, top: int, width: int, height: int, out_path: Path):
    preview = image.copy()
    draw = ImageDraw.Draw(preview)
    draw.rectangle((left, top, left + width, top + height), outline="red", width=3)
    preview.save(out_path)


def preprocess_card_image(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def preprocess_birth_image_soft(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.resize((gray.width * 3, gray.height * 3))
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def preprocess_birth_image_strong(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.resize((gray.width * 4, gray.height * 4))
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    bw = gray.point(lambda x: 0 if x < 215 else 255, "1")
    return bw.convert("L")


def preprocess_birth_image_stronger(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.resize((gray.width * 4, gray.height * 4))
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    bw = gray.point(lambda x: 0 if x < 225 else 255, "1")
    return bw.convert("L")


def ocr_card_image(image: Image.Image) -> str:
    processed = preprocess_card_image(image)

    variants = []
    for psm in (6, 11):
        text = pytesseract.image_to_string(
            processed,
            lang="rus+eng",
            config=f"--psm {psm}"
        )
        text = normalize_text(text)
        if text.strip():
            variants.append(text)

    return max(variants, key=len) if variants else ""


def ocr_birth_region(image: Image.Image) -> str:
    variants = []

    prepared_images = (
        preprocess_birth_image_soft(image),
        preprocess_birth_image_strong(image),
        preprocess_birth_image_stronger(image),
    )

    for prepared in prepared_images:
        for psm in (7, 6, 13):
            text = pytesseract.image_to_string(
                prepared,
                lang="eng",
                config=(
                    f"--psm {psm} "
                    "-c tessedit_char_whitelist=0123456789.()- "
                )
            )
            text = normalize_text(text)
            if text.strip():
                variants.append(text)

    if not variants:
        return ""

    return max(variants, key=len)


def extract_birth_date_from_birth_region(card_img: Image.Image) -> Optional[str]:
    region = crop_region(
        card_img,
        DEFAULT_BIRTH_REGION_INSIDE_CARD["left"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["top"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["width"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["height"],
    )

    raw = ocr_birth_region(region)

    print()
    print("=== RAW BIRTH OCR ===")
    print(raw)

    m = re.search(r"\b\d{2}[.\-/ ]\d{2}[.\-/ ]\d{2,4}\b|\b\d{8}\b", raw)
    if m:
        nd = normalize_date(m.group(0))
        if nd:
            return nd

    dates = extract_dates(raw)
    if dates:
        return dates[0]

    return None


def parse_patient_card_ocr(img: Image.Image) -> RisCardOcrResult:
    raw_text = ocr_card_image(img)
    fio = extract_fio(raw_text)
    birth_date = extract_birth_date_from_birth_region(img)
    service_ok = service_matches_text(raw_text)

    return RisCardOcrResult(
        raw_text=raw_text,
        fio=fio,
        birth_date=birth_date,
        service_ok=service_ok,
    )


def debug_ris_card_from_image(
    image_path: str | Path,
    task_fio: Optional[str] = None,
    task_birth_date: Optional[str] = None,
    left: int = DEFAULT_CARD_REGION["left"],
    top: int = DEFAULT_CARD_REGION["top"],
    width: int = DEFAULT_CARD_REGION["width"],
    height: int = DEFAULT_CARD_REGION["height"],
):
    image_path = Path(image_path)
    image = Image.open(image_path)

    card = crop_region(image, left, top, width, height)
    result = parse_patient_card_ocr(card)

    ts = now_str()
    crop_path = LOG_DIR / f"ris_card_crop_{ts}.png"
    preview_path = LOG_DIR / f"ris_card_preview_{ts}.png"
    birth_crop_path = LOG_DIR / f"ris_birth_crop_{ts}.png"

    card.save(crop_path)
    save_region_preview(image, left, top, width, height, preview_path)

    birth_crop = crop_region(
        card,
        DEFAULT_BIRTH_REGION_INSIDE_CARD["left"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["top"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["width"],
        DEFAULT_BIRTH_REGION_INSIDE_CARD["height"],
    )
    birth_crop.save(birth_crop_path)

    print("=== DEBUG RIS OCR ===")
    print("IMAGE:", image_path)
    print("REGION:", {"left": left, "top": top, "width": width, "height": height})
    print("CROP SAVED:", crop_path)
    print("PREVIEW SAVED:", preview_path)
    print("BIRTH CROP SAVED:", birth_crop_path)
    print()

    print("=== RAW OCR TEXT ===")
    print(result.raw_text)
    print()

    print("=== PARSED ===")
    print("FIO       :", result.fio)
    print("BIRTH DATE:", result.birth_date)
    print("SERVICE OK:", result.service_ok)

    if task_fio:
        print()
        print("TASK FIO      :", task_fio)
        print("FIO MATCH     :", fio_matches(task_fio, result.fio or ""))

    if task_birth_date:
        print("TASK BIRTH    :", normalize_date(task_birth_date))
        print("BIRTH MATCH   :", normalize_date(task_birth_date) == normalize_date(result.birth_date or ""))

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Использование:")
        print('python project/browser_ris_debug_from_image.py "<path_to_image>"')
        print('python project/browser_ris_debug_from_image.py "<path_to_image>" "<fio>" "<birth_date>"')
        raise SystemExit(1)

    image_path = sys.argv[1]
    task_fio = sys.argv[2] if len(sys.argv) >= 3 else None
    task_birth = sys.argv[3] if len(sys.argv) >= 4 else None

    debug_ris_card_from_image(
        image_path=image_path,
        task_fio=task_fio,
        task_birth_date=task_birth,
    )