import re
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import mss
import pyautogui
import pytesseract
from PIL import Image, ImageFilter, ImageOps

from config.loader import (
    COMMON_SETTINGS,
    RIS_SETTINGS,
    RIS_COORDS,
    RIS_TEMPLATES,
    timings,
)


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]

RIS_URL = RIS_SETTINGS["ris_url"]

pyautogui.PAUSE = 0.2
pyautogui.FAILSAFE = True

SEARCH_BUTTON_TO_FIELD_OFFSET_X = RIS_COORDS["search_button_to_field_offset"][0]
SEARCH_BUTTON_TO_FIELD_OFFSET_Y = RIS_COORDS["search_button_to_field_offset"][1]

PAGE_OPEN_WAIT = timings["page_open_wait"]
SEARCH_RESULT_WAIT = timings["search_result_wait"]
OPEN_CARD_WAIT = timings["open_card_wait"]
AFTER_START_WAIT = timings["after_start_wait"]
AFTER_FINISH_WAIT = timings["after_finish_wait"]

WAIT_CHECKS = timings.get("wait_checks", 3)
WAIT_PAUSE = timings.get("wait_pause", 3.0)
WAIT_PROBE_TIMEOUT = timings.get("wait_probe_timeout", 0.5)

PATIENT_CARD_REGION_OFFSET = RIS_COORDS["patient_card_region_offset"]
BIRTH_REGION_INSIDE_CARD = RIS_COORDS["birth_region_inside_card"]

VALID_SERVICE_SUBSTRINGS = RIS_SETTINGS["valid_service_substrings"]


@dataclass
class RisCardOcrResult:
    raw_text: str
    fio: Optional[str]
    birth_date: Optional[str]
    service_ok: bool


def now_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_DIR / "ris_flow.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_debug_image(img: Image.Image, prefix: str):
    out = LOG_DIR / f"{prefix}_{now_str()}.png"
    img.save(out)
    log(f"Сохранен debug image: {out}")
    return out


def fail(win, message: str):
    log(f"ОШИБКА: {message}")
    raise RuntimeError(message)


def template_file(key: str) -> Path:
    return TEMPLATES_DIR / RIS_TEMPLATES[key]["file"]


def template_conf(key: str, default: float = 0.82) -> float:
    return RIS_TEMPLATES[key].get("confidence", default)


def locate_image_on_screen(template_key: str, confidence=None, timeout=10.0):
    path = template_file(template_key)
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден: {path}")

    conf = template_conf(template_key, 0.82) if confidence is None else confidence

    end = time.time() + timeout
    while time.time() < end:
        loc = pyautogui.locateCenterOnScreen(str(path), confidence=conf)
        if loc:
            return loc
        time.sleep(0.25)
    return None


def wait_for_template_strict(
    template_key: str,
    confidence=None,
    checks=None,
    pause=None,
    probe_timeout=None,
):
    checks = WAIT_CHECKS if checks is None else checks
    pause = WAIT_PAUSE if pause is None else pause
    probe_timeout = WAIT_PROBE_TIMEOUT if probe_timeout is None else probe_timeout
    conf = template_conf(template_key, 0.80) if confidence is None else confidence

    started = time.time()

    for attempt in range(1, checks + 1):
        loc = locate_image_on_screen(template_key, confidence=conf, timeout=probe_timeout)

        if loc:
            elapsed = time.time() - started
            log(f"{template_key} найден ({attempt}/{checks}) за {elapsed:.2f} сек")
            return loc

        log(f"{template_key} НЕ найден ({attempt}/{checks})")

        if attempt < checks:
            time.sleep(pause)

    elapsed = time.time() - started
    log(f"{template_key} не найден после {checks} проверок за {elapsed:.2f} сек")
    return None


def click_image(win, template_key: str, confidence=None, timeout=10.0, clicks=1, offset=(0, 0)):
    loc = locate_image_on_screen(template_key, confidence=confidence, timeout=timeout)
    if not loc:
        return False

    x = loc.x + offset[0]
    y = loc.y + offset[1]
    pyautogui.click(x, y, clicks=clicks, interval=0.2)
    log(f"Клик по шаблону: {template_key} offset={offset}")
    return True


def double_click_image(win, template_key: str, confidence=None, timeout=10.0, offset=(0, 0)):
    return click_image(win, template_key, confidence=confidence, timeout=timeout, clicks=2, offset=offset)


def wait_for_template_3_checks(template_key: str, confidence=None, checks=3, pause=1.0):
    return wait_for_template_strict(
        template_key=template_key,
        confidence=confidence,
        checks=checks,
        pause=pause,
        probe_timeout=WAIT_PROBE_TIMEOUT,
    ) is not None


def grab_screen_region(left: int, top: int, width: int, height: int) -> Image.Image:
    with mss.mss() as sct:
        shot = sct.grab({
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        })
        return Image.frombytes("RGB", shot.size, shot.rgb)


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
        BIRTH_REGION_INSIDE_CARD["left"],
        BIRTH_REGION_INSIDE_CARD["top"],
        BIRTH_REGION_INSIDE_CARD["width"],
        BIRTH_REGION_INSIDE_CARD["height"],
    )

    raw = ocr_birth_region(region)
    log(f"RAW BIRTH OCR: {raw}")

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


def capture_patient_card_image(win=None) -> Image.Image:
    loc = locate_image_on_screen("ris_patient_card_side", timeout=4)
    if not loc:
        fail(win, "Не найдена карточка пациента слева")

    left = loc.x + PATIENT_CARD_REGION_OFFSET["left"]
    top = loc.y + PATIENT_CARD_REGION_OFFSET["top"]
    width = PATIENT_CARD_REGION_OFFSET["width"]
    height = PATIENT_CARD_REGION_OFFSET["height"]

    img = grab_screen_region(left, top, width, height)
    log(f"OCR карточки пациента: region=({left}, {top}, {width}, {height})")
    save_debug_image(img, "ris_patient_card")
    return img


def clear_active_input():
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.15)


def type_text(text: str):
    pyautogui.write(text, interval=0.03)
    time.sleep(0.3)


def click_search_field_by_button_offset(win=None):
    loc = locate_image_on_screen("ris_search_button_active", timeout=8)
    if not loc:
        fail(win, "Не найдена активная кнопка поиска")

    x = loc.x + SEARCH_BUTTON_TO_FIELD_OFFSET_X
    y = loc.y + SEARCH_BUTTON_TO_FIELD_OFFSET_Y

    pyautogui.click(x, y)
    time.sleep(0.2)
    pyautogui.click(x, y)
    time.sleep(0.2)

    log(f"Клик в поле поиска по offset от кнопки: ({x}, {y})")
    return x, y


def wait_search_button_ready(win=None):
    ok = wait_for_template_3_checks(
        "ris_search_button_active",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE
    )
    if not ok:
        fail(win, "Активная кнопка поиска не появилась")


def wait_patient_cards(win=None):
    ok = wait_for_template_3_checks(
        "ris_patient_card_side",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE
    )
    if not ok:
        fail(win, "Карточки пациентов не появились")


def open_ris_page(win=None):
    log("Открываю страницу РИС")
    webbrowser.open(RIS_URL, new=2)
    time.sleep(PAGE_OPEN_WAIT)

    wait_search_button_ready(win)
    log("Страница РИС готова")


def search_patient(task, win=None):
    log("Начинаю поиск пациента в РИС")

    click_search_field_by_button_offset(win)
    clear_active_input()

    search_text = normalize_compare_text(task.fio)
    log(f"Ввожу ФИО: {search_text}")
    type_text(search_text)

    ok = click_image(win, "ris_search_button_active", timeout=4)
    if not ok:
        pyautogui.press("enter")

    time.sleep(SEARCH_RESULT_WAIT)
    wait_patient_cards(win)

    log("Результаты поиска появились")


def check_found_patient(task, win=None):
    log("OCR проверка найденного пациента")

    img = capture_patient_card_image(win)
    result = parse_patient_card_ocr(img)

    log("=== OCR карточки РИС ===")
    log(result.raw_text)
    log(f"OCR ФИО: {result.fio}")
    log(f"OCR ДР : {result.birth_date}")
    log(f"OCR service_ok: {result.service_ok}")

    if not result.fio:
        fail(win, "OCR: ФИО не найдено в карточке пациента")

    if not fio_matches(task.fio, result.fio):
        fail(win, f"OCR: ФИО не совпало. task={task.fio} / ocr={result.fio}")

    if not result.birth_date:
        fail(win, "OCR: дата рождения не найдена в карточке пациента")

    if normalize_date(task.birth_date) != normalize_date(result.birth_date):
        fail(win, f"OCR: дата рождения не совпала. task={task.birth_date} / ocr={result.birth_date}")

    if not result.service_ok:
        fail(win, "OCR: услуга не похожа на рентгенографию грудной клетки / флюорографию")

    log("OCR проверка пациента успешна")


def open_patient_card(win=None):
    log("Открываю карточку пациента")

    ok = double_click_image(win, "ris_patient_card_side", timeout=4)
    if not ok:
        fail(win, "Не удалось открыть карточку пациента")

    time.sleep(OPEN_CARD_WAIT)

    loc = wait_for_template_strict(
        "ris_apparatus_field",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    if not loc:
        fail(win, "Карточка пациента не открылась")

    log("Карточка пациента открыта")


def choose_apparatus(win=None):
    log("Выбор аппарата")

    ok = click_image(win, "ris_apparatus_field", timeout=6)
    if not ok:
        fail(win, "Не найдено поле Аппарат")

    time.sleep(0.3)

    pyautogui.press("tab")
    time.sleep(0.3)
    pyautogui.press("pagedown")
    time.sleep(0.5)
    pyautogui.press("pagedown")
    time.sleep(0.8)

    target = wait_for_template_strict(
        "ris_apparatus_target",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    if not target:
        fail(win, "Не найден нужный аппарат в списке")

    pyautogui.click(target.x, target.y)
    time.sleep(1.0)

    ok = wait_for_template_3_checks(
        "ris_start_button",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE
    )
    if not ok:
        fail(win, "После выбора аппарата не появилась кнопка 'Начать исследование'")

    log("Аппарат выбран")


def start_research(win=None):
    log("Нажимаю 'Начать исследование'")

    ok = click_image(win, "ris_start_button", timeout=6)
    if not ok:
        fail(win, "Не найдена кнопка 'Начать исследование'")

    log("Жду после старта исследования")
    time.sleep(AFTER_START_WAIT)

    ok = wait_for_template_3_checks(
        "ris_finish_button",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE
    )
    if not ok:
        fail(win, "Кнопка 'Завершить' не появилась после старта")

    log("Кнопка 'Завершить' появилась")


def finish_research(win=None):
    log("Нажимаю 'Завершить'")

    ok = click_image(win, "ris_finish_button", timeout=6)
    if not ok:
        fail(win, "Не найдена кнопка 'Завершить'")

    time.sleep(AFTER_FINISH_WAIT)

    ok = wait_for_template_3_checks(
        "ris_completed_status",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE
    )
    if not ok:
        fail(win, "Статус 'Завершено' не появился")

    log("Статус 'Завершено' подтвержден")


def reset_search_for_next_patient(win=None):
    log("Возвращаюсь к поиску следующего пациента")

    wait_search_button_ready(win)
    click_search_field_by_button_offset(win)
    clear_active_input()

    log("Поле поиска очищено")


def run_ris_link(task, win=None):
    log(f"РИС: полный цикл для {task.fio} / {task.birth_date}")

    open_ris_page(win)
    search_patient(task, win)
    check_found_patient(task, win)
    open_patient_card(win)
    choose_apparatus(win)
    start_research(win)
    finish_research(win)
    reset_search_for_next_patient(win)

    log("РИС: полный цикл завершен успешно")