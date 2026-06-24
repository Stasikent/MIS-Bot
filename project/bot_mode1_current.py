import time
import json
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import mss
import tkinter as tk
import pyautogui
import pygetwindow as gw
import pytesseract
from PIL import Image

import cv2
import numpy as np

from config.loader import (
    COMMON_SETTINGS,
    MIS_SETTINGS,
    MIS_COORDS,
    MIS_TEMPLATES,
    timings,
)
from gui.runtime_click_pick import pick_runtime_point

from config.loader import load_json

from project.run_controller import RunController

from gui.ui_helper import (
    ui_error,
    ui_checkpoint,
    ui_manual_continue,
    ui_adapt_action,
)


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CONFIG_COORDS_PATH = Path(__file__).resolve().parents[1] / "config" / "coordinates.json"

pytesseract.pytesseract.tesseract_cmd = COMMON_SETTINGS["tesseract_path"]

MIS_WINDOW_TITLE = MIS_SETTINGS["window_title"]

pyautogui.PAUSE = 0.2
pyautogui.FAILSAFE = True

SEARCH_ANCHOR_X_OFFSET = MIS_COORDS["search_anchor_x_offset"]

DOB_REGION = tuple(MIS_COORDS["dob_region"])
ROW_HEIGHT = MIS_COORDS["row_height"]
MAX_PATIENT_ROWS = MIS_COORDS["max_patient_rows"]

WORK_PLUS_FALLBACK_POINT = tuple(MIS_COORDS["work_plus_fallback_point"])

VISIT_PLUS_OFFSET = tuple(MIS_COORDS.get("visit_plus_offset", (-18, 0)))
REASON_FIELD_OFFSET = tuple(MIS_COORDS.get("reason_field_offset", (95, 0)))
GOAL_DROPDOWN_OFFSET = tuple(MIS_COORDS.get("goal_dropdown_offset", (0, 0)))
HISTORY_MENU_OFFSET = tuple(MIS_COORDS.get("history_menu_offset", (0, 0)))
HISTORY_FLUORO_ITEM_OFFSET = tuple(MIS_COORDS.get("history_fluoro_item_offset", (0, 0)))
TEMPLATES_ANCHOR_OFFSET = tuple(MIS_COORDS.get("templates_anchor_offset", (0, 0)))
TEMPLATE_USE_OFFSET = tuple(MIS_COORDS.get("template_use_offset", (0, 0)))
DIAGNOSIS_DROP_OFFSET = tuple(MIS_COORDS.get("diagnosis_drop_offset", (0, 0)))
DIAGNOSIS_CODE_OFFSET = tuple(MIS_COORDS.get("diagnosis_code_offset", (0, 0)))
STUDY_DATE_LABEL_OFFSET = tuple(MIS_COORDS.get("study_date_label_offset", (220, 0)))
DIAGNOSIS_CANCEL_ITEM_OFFSET = tuple(MIS_COORDS.get("diagnosis_cancel_item_offset", (0, 0)))
SERVICE_PRICE_ZERO_OFFSET = tuple(MIS_COORDS.get("service_price_zero_offset", (0, 0)))
SEARCH_ANCHOR_OFFSET = tuple(MIS_COORDS.get("search_anchor_offset", (0, 0)))
WORK_PLUS_OFFSET = tuple(MIS_COORDS.get("work_plus_offset", (0, 0)))

XRAY_SERVICE_ITEM_OFFSET = tuple(MIS_COORDS.get("xray_service_item_offset", (0, 0)))
TEMPLATE_OWNER_DROPDOWN_OFFSET = tuple(MIS_COORDS.get("template_owner_dropdown_offset", (0, 0)))
TEMPLATE_OWNER_ONLY_MINE_OFFSET = tuple(MIS_COORDS.get("template_owner_only_mine_offset", (0, 0)))
TEMPLATE_DIAGNOSIS_CLEAR_CROSS_OFFSET = tuple(MIS_COORDS.get("template_diagnosis_clear_cross_offset", (0, 0)))
TEMPLATE_SELECT_BUTTON_OFFSET = tuple(MIS_COORDS.get("template_select_button_offset", (0, 0)))
XRAY_TEMPLATE_ROW_OFFSET = tuple(MIS_COORDS.get("xray_template_row_offset", (0, 0)))

SERVICE_WINDOW_WAIT = timings["service_window_wait"]
HISTORY_MENU_WAIT = timings["history_menu_wait"]
WITHOUT_REFERRAL_TIMEOUT = timings["without_referral_timeout"]
TEMPLATE_LOAD_WAIT = timings["template_load_wait"]

INPATIENT_YES_BUTTON_OFFSET = tuple(MIS_COORDS.get("inpatient_yes_button_offset", (0, 0)))
ADD_DIAGNOSIS_NO_BUTTON_OFFSET = tuple(MIS_COORDS.get("add_diagnosis_no_button_offset", (0, 0)))

XRAY_SERVICE_ITEM_OFFSET = tuple(MIS_COORDS.get("xray_service_item_offset", (0, 0)))
TEMPLATE_OWNER_DROPDOWN_OFFSET = tuple(MIS_COORDS.get("template_owner_dropdown_offset", (0, 0)))
TEMPLATE_OWNER_ONLY_MINE_OFFSET = tuple(MIS_COORDS.get("template_owner_only_mine_offset", (0, 0)))

WAIT_CHECKS = timings.get("wait_checks", 3)
WAIT_PAUSE = timings.get("wait_pause", 3.0)
WAIT_PROBE_TIMEOUT = timings.get("wait_probe_timeout", 0.5)

XRAY_FIELD_STUDY_NUMBER_OFFSET = tuple(MIS_COORDS.get("xray_field_study_number_offset", (260, 0)))
XRAY_FIELD_DESCRIPTION_OFFSET = tuple(MIS_COORDS.get("xray_field_description_offset", (260, 0)))
XRAY_FIELD_CONCLUSION_OFFSET = tuple(MIS_COORDS.get("xray_field_conclusion_offset", (260, 0)))

BETWEEN_PATIENTS_PAUSE = timings.get("between_patients_pause", 1.5)

MANUAL_PATIENT_SELECT_WAIT = timings.get("manual_patient_select_wait", 5)
SERVICE_LIST_TIMEOUT = timings.get("service_list_timeout", 10.0)
SERVICE_LIST_PROBE_TIMEOUT = timings.get("service_list_probe_timeout", 1.2)
USE_SMART_SERVICE_WAIT = timings.get("use_smart_service_wait", True)
PASTE_CONTEXT_MENU_WAIT = timings.get("paste_context_menu_wait", 0.7)

STOP_ON_CRITICAL = COMMON_SETTINGS["stop_on_critical"]

MODE_TEMPLATES = MIS_SETTINGS["mode_templates"]
VALID_MODES = set(MODE_TEMPLATES.keys())

# Включается из GUI
INTERACTIVE_CLICK_CALIBRATION = False

ACTIVE_CONTROLLER = None

def set_active_controller(ctrl):
    global ACTIVE_CONTROLLER
    ACTIVE_CONTROLLER = ctrl

def checkpoint():
    if ACTIVE_CONTROLLER is None:
        return
    try:
        ACTIVE_CONTROLLER.wait_if_paused()
        ACTIVE_CONTROLLER.raise_if_cancelled()
    except Exception:
        raise


def set_interactive_click_calibration(enabled: bool):
    global INTERACTIVE_CLICK_CALIBRATION
    INTERACTIVE_CLICK_CALIBRATION = bool(enabled)
    print("[BOT CONFIG] INTERACTIVE_CLICK_CALIBRATION =", INTERACTIVE_CLICK_CALIBRATION)


print("[BOT CONFIG] MIS_WINDOW_TITLE =", MIS_WINDOW_TITLE)
print("[BOT CONFIG] DOB_REGION =", DOB_REGION)
print("[BOT CONFIG] ROW_HEIGHT =", ROW_HEIGHT)
print("[BOT CONFIG] MAX_PATIENT_ROWS =", MAX_PATIENT_ROWS)
print("[BOT CONFIG] WAIT_CHECKS =", WAIT_CHECKS)
print("[BOT CONFIG] WAIT_PAUSE =", WAIT_PAUSE)
print("[BOT CONFIG] WAIT_PROBE_TIMEOUT =", WAIT_PROBE_TIMEOUT)
print("[BOT CONFIG] BETWEEN_PATIENTS_PAUSE =", BETWEEN_PATIENTS_PAUSE)


def template_file(key: str) -> Path:
    return TEMPLATES_DIR / MIS_TEMPLATES[key]["file"]


def template_conf(key: str, default: float = 0.82) -> float:
    return MIS_TEMPLATES[key].get("confidence", default)


def now_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_DIR / "bot.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_window_screenshot(win, prefix="screen"):
    out = LOG_DIR / f"{prefix}_{now_str()}.png"
    with mss.mss() as sct:
        shot = sct.grab({
            "left": win.left,
            "top": win.top,
            "width": win.width,
            "height": win.height,
        })
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(out)
    log(f"Скрин окна сохранен: {out}")
    return out


def save_region_screenshot(win, rel_region, prefix="region"):
    x = win.left + rel_region[0]
    y = win.top + rel_region[1]
    w = rel_region[2]
    h = rel_region[3]

    out = LOG_DIR / f"{prefix}_{now_str()}.png"
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(out)
    log(f"Скрин области сохранен: {out}")
    return out

def fail(win, message: str, rel_region=None):
    log(f"ОШИБКА: {message}")
    save_window_screenshot(win, "error_window")

    if rel_region:
        save_region_screenshot(win, rel_region, "error_region")

    action = ui_error(message)

    if action == "continue":
        log("Пользователь выбрал: продолжить")
        return "continue"

    if STOP_ON_CRITICAL:
        raise RuntimeError(message)

    return "cancel"


def find_mis_window():
    settings = load_json("settings.json")
    target_title = settings.get("mis", {}).get("window_title")

    if target_title:
        for w in gw.getAllWindows():
            if target_title.lower() in w.title.lower():
                try:
                    w.activate()
                except Exception:
                    pass
                return w

    raise RuntimeError(f"Окно МИС не найдено: {target_title}")

def find_rdp_window():
    return find_mis_window()

def abs_point(win, rel_xy):
    return win.left + rel_xy[0], win.top + rel_xy[1]


def abs_region(win, rel_region):
    x, y, w, h = rel_region
    return (win.left + x, win.top + y, w, h)


def click_rel(win, rel_xy, clicks=1, interval=0.15, button="left"):
    x, y = abs_point(win, rel_xy)
    checkpoint()
    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    checkpoint()


def screenshot_region(win, rel_region):
    x, y, w, h = abs_region(win, rel_region)
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        return Image.frombytes("RGB", shot.size, shot.rgb)


def debug_click_point(x, y):
    if x is None or y is None:
        log(f"[CLICK] Пропуск: координаты None ({x}, {y})")
        return False

    screen_w, screen_h = pyautogui.size()

    # защита от углов (fail-safe)
    if x < 5 or y < 5 or x > screen_w - 5 or y > screen_h - 5:
        log(f"[CLICK] Пропуск: координаты вне безопасной зоны ({x}, {y})")
        return False

    try:
        pyautogui.moveTo(x, y, duration=0.05)
        return True
    except pyautogui.FailSafeException:
        log("[CLICK] FailSafeException пойман — движение отменено")
        return False


def normalize_date_text(s: str):
    return s.replace(" ", "").replace(",", ".").replace("-", ".")


def normalize_date_digits(s: str):
    return "".join(ch for ch in normalize_date_text(s) if ch.isdigit())

def compare_birth_date_candidate(target_date: str, candidate_text: str):
    """
    Сравнение target даты с OCR-кандидатом.
    Возвращает:
    - bool: есть ли совпадение
    - str: тип совпадения ('exact', 'partial', 'weak', '')
    """
    target_digits = normalize_date_digits(target_date)
    cand_digits = normalize_date_digits(candidate_text)

    if not target_digits or not cand_digits:
        return False, ""

    if cand_digits == target_digits:
        return True, "exact"

    if target_digits in cand_digits:
        return True, "partial"

    # слабый fallback:
    # день+месяц совпали и хвост года похож
    if len(target_digits) == 8 and len(cand_digits) >= 6:
        if target_digits[:4] == cand_digits[:4] and target_digits[-2:] == cand_digits[-2:]:
            return True, "weak"

    return False, ""


def ocr_date_image(img: Image.Image):
    """
    Двойной OCR-проход для даты:
    1) быстрый проход — оригинал + мягкие бинаризации
    2) усиленный проход — контраст + resize + более жесткие бинаризации

    Возвращает лучшую найденную строку даты или пустую строку.
    """
    checkpoint()

    gray = img.convert("L")

    def cleanup_text(text: str) -> str:
        text = text.replace(",", ".").replace("-", ".").replace("/", ".")
        text = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        while ".." in text:
            text = text.replace("..", ".")
        return text.strip(" .")

    def score_date_candidate(text: str) -> int:
        if not text:
            return 0

        digits = "".join(ch for ch in text if ch.isdigit())
        dots = text.count(".")
        score = 0

        if len(digits) == 8:
            score += 100

        if dots == 2:
            score += 40
        elif dots == 1:
            score += 10

        if 8 <= len(text) <= 10:
            score += 20

        parts = text.split(".")
        if len(parts) == 3:
            d, m, y = parts
            if len(d) in (1, 2) and len(m) in (1, 2) and len(y) in (2, 4):
                score += 60

        return score

    def normalize_candidate(text: str) -> str:
        text = cleanup_text(text)
        if not text:
            return ""

        parts = [p for p in text.split(".") if p]
        if len(parts) != 3:
            return text

        d, m, y = parts

        if len(d) == 1:
            d = "0" + d
        if len(m) == 1:
            m = "0" + m
        if len(y) == 2:
            y = "20" + y

        return f"{d}.{m}.{y}"

    def run_ocr_variants(images, psm_list):
        found = []

        for prepared in images:
            checkpoint()
            for psm in psm_list:
                try:
                    raw = pytesseract.image_to_string(
                        prepared,
                        lang="eng",
                        config=f"--psm {psm} -c tessedit_char_whitelist=0123456789./,-",
                        timeout=2,
                    )
                except pytesseract.TesseractError as e:
                    log(f"OCR ошибка Tesseract: {e}")
                    continue
                except RuntimeError as e:
                    log(f"OCR timeout/runtime error: {e}")
                    continue
                except Exception as e:
                    log(f"OCR непредвиденная ошибка: {e}")
                    continue

                cleaned = cleanup_text(raw)
                normalized = normalize_candidate(cleaned)
                score = score_date_candidate(normalized)

                if normalized:
                    found.append((normalized, score, psm))

        return found

    # --- ПРОХОД 1: быстрый ---
    pass1_images = [gray]

    for threshold in (160, 175, 190):
        bw = gray.point(lambda x, t=threshold: 0 if x < t else 255, "1")
        pass1_images.append(bw.convert("L"))

    pass1_results = run_ocr_variants(pass1_images, psm_list=(7, 13))
    if pass1_results:
        best1 = max(pass1_results, key=lambda x: x[1])
        log(f"OCR pass1 best: text={best1[0]!r}, score={best1[1]}, psm={best1[2]}")
        if best1[1] >= 140:
            return best1[0]

    # --- ПРОХОД 2: усиленный ---
    big = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)

    stretched = big.point(
        lambda x: 0 if x < 100 else (255 if x > 200 else int((x - 100) * 255 / 100))
    )

    pass2_images = [big, stretched]

    for threshold in (145, 160, 175, 200):
        bw = stretched.point(lambda x, t=threshold: 0 if x < t else 255, "1")
        pass2_images.append(bw.convert("L"))

    pass2_results = run_ocr_variants(pass2_images, psm_list=(7, 13, 6))

    all_results = pass1_results + pass2_results
    if not all_results:
        return ""

    best = max(all_results, key=lambda x: x[1])
    log(f"OCR final best: text={best[0]!r}, score={best[1]}, psm={best[2]}")
    return best[0]

def wait_manual_patient_selection(wait_seconds=MANUAL_PATIENT_SELECT_WAIT):
    log(
        f"Ручной выбор пациента: выбери нужную строку левой кнопкой мыши, "
        f"ожидание {wait_seconds} сек"
    )
    time.sleep(wait_seconds)
    checkpoint()
    return True


def locate_image_on_screen(template_key: str, confidence=None, timeout=10.0):
    try:
        win = find_mis_window()
        return locate_template_in_window_cv(
            win=win,
            template_key=template_key,
            confidence=confidence,
            timeout=timeout,
        )
    except Exception as e:
        log(f"Оконный CV-поиск не сработал для {template_key}: {e}")

    # fallback старым способом
    path = template_file(template_key)
    conf = template_conf(template_key, 0.82) if confidence is None else confidence

    end = time.time() + timeout
    while time.time() < end:
        try:
            loc = pyautogui.locateCenterOnScreen(str(path), confidence=conf)
            if loc:
                return loc
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.25)
        checkpoint()

    return None

def locate_image_in_window(win, template_key: str, confidence=None, timeout=10.0):
    path = template_file(template_key)
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден на диске: {path}")

    conf = template_conf(template_key, 0.82) if confidence is None else confidence

    region = (
        int(win.left),
        int(win.top),
        int(win.width),
        int(win.height),
    )

    end = time.time() + timeout
    while time.time() < end:
        try:
            loc = pyautogui.locateCenterOnScreen(
                str(path),
                confidence=conf,
                region=region,
            )
            if loc:
                return loc
        except pyautogui.ImageNotFoundException:
            pass

        time.sleep(0.25)
        checkpoint()

    return None

def locate_image_in_window_safe(win, template_key: str, confidence=None, timeout=10.0):
    path = template_file(template_key)
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден на диске: {path}")

    conf = template_conf(template_key, 0.82) if confidence is None else confidence

    end = time.time() + timeout

    while time.time() < end:
        checkpoint()

        try:
            img_path = save_window_screenshot(win, prefix="window_probe")

            loc = pyautogui.locateCenterOnScreen(
                str(path),
                confidence=conf,
                region=(int(win.left), int(win.top), int(win.width), int(win.height)),
            )

            if loc:
                return loc

        except Exception:
            pass

        time.sleep(0.25)

    return None

def locate_template_in_window_cv(win, template_key: str, confidence=None, timeout=10.0):
    path = template_file(template_key)
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден на диске: {path}")

    conf = template_conf(template_key, 0.82) if confidence is None else confidence

    end = time.time() + timeout

    while time.time() < end:
        checkpoint()

        try:
            with mss.mss() as sct:
                shot = sct.grab({
                    "left": int(win.left),
                    "top": int(win.top),
                    "width": int(win.width),
                    "height": int(win.height),
                })

            screen_img = Image.frombytes("RGB", shot.size, shot.rgb)
            screen_np = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2BGR)

            template_img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if template_img is None:
                raise RuntimeError(f"Не удалось прочитать шаблон: {path}")

            result = cv2.matchTemplate(screen_np, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= conf:
                th, tw = template_img.shape[:2]
                x = int(win.left + max_loc[0] + tw / 2)
                y = int(win.top + max_loc[1] + th / 2)

                log(f"{template_key} найден в окне: score={max_val:.3f}, point=({x},{y})")
                return pyautogui.Point(x, y)

        except Exception as e:
            log(f"CV поиск шаблона {template_key}: ошибка {e}")

        time.sleep(0.25)

    return None

def paste_text_safe(text: str):
    import pyperclip

    pyperclip.copy(text or "")
    time.sleep(0.1)
    checkpoint()

    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    checkpoint()


def clear_current_field():
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    checkpoint()

    pyautogui.press("backspace")
    time.sleep(0.1)
    checkpoint()


def fill_xray_field_by_label(
    win,
    template_key,
    text,
    offset,
    offset_key,
    label,
):
    log(f"XRAY: заполнение поля {label}")

    ok = adaptive_click_template_target(
        win=win,
        template_key=template_key,
        offset=offset,
        offset_key=offset_key,
        timeout=8,
        label=label,
        clicks=1,
        expected_template=None,
        post_click_sleep=0.2,
    )
    if not ok:
        return False

    clear_current_field()
    paste_text_safe(text)
    return True


def fill_xray_protocol(win, task):
    log("XRAY: заполнение протокола")

    ok = fill_xray_field_by_label(
        win=win,
        template_key="xray_field_study_number",
        text="-",
        offset=XRAY_FIELD_STUDY_NUMBER_OFFSET,
        offset_key="xray_field_study_number_offset",
        label="Номер исследования",
    )
    if not ok:
        return False

    ok = fill_xray_field_by_label(
        win=win,
        template_key="xray_field_description",
        text=task.description,
        offset=XRAY_FIELD_DESCRIPTION_OFFSET,
        offset_key="xray_field_description_offset",
        label="Описание результатов",
    )
    if not ok:
        return False

    ok = fill_xray_field_by_label(
        win=win,
        template_key="xray_field_conclusion",
        text=task.conclusion,
        offset=XRAY_FIELD_CONCLUSION_OFFSET,
        offset_key="xray_field_conclusion_offset",
        label="Заключение",
    )
    if not ok:
        return False

    log("XRAY: протокол заполнен")
    return True


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
        checkpoint()
        loc = locate_image_on_screen(template_key, confidence=conf, timeout=probe_timeout)

        if loc:
            elapsed = time.time() - started
            log(f"{template_key} найден ({attempt}/{checks}) за {elapsed:.2f} сек")
            return loc

        log(f"{template_key} НЕ найден ({attempt}/{checks})")

        if attempt < checks:
            time.sleep(pause)
            checkpoint()

    elapsed = time.time() - started
    log(f"{template_key} не найден после {checks} проверок за {elapsed:.2f} сек")
    return None


def get_template_click_point(template_key: str, offset=(0, 0), confidence=None, timeout=8):
    loc = locate_image_on_screen(template_key, confidence=confidence, timeout=timeout)
    if not loc:
        return None, None, None

    final_x = loc.x + offset[0]
    final_y = loc.y + offset[1]
    return loc, final_x, final_y


def _read_coords_json():
    with open(CONFIG_COORDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_coords_json(data):
    with open(CONFIG_COORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def choose_xray_service(win):
    log("Выбор услуги: Рентгенографическое исследование")

    clicked = click_template_target(
        win,
        "xray_service_item",
        offset=XRAY_SERVICE_ITEM_OFFSET,
        offset_key="xray_service_item_offset",
        timeout=8,
        label="xray_service_item",
        clicks=1,
    )
    if not clicked:
        return False

    time.sleep(0.6)
    checkpoint()
    return True


def choose_only_my_templates(win):
    log("Фильтр шаблонов: Владелец -> Только свои")

    ok = adaptive_click_template_target(
        win=win,
        template_key="template_owner_dropdown",
        offset=TEMPLATE_OWNER_DROPDOWN_OFFSET,
        offset_key="template_owner_dropdown_offset",
        timeout=8,
        label="template_owner_dropdown",
        clicks=1,
        expected_template="template_owner_only_mine",
        expected_checks=3,
        expected_pause=0.4,
        expected_probe_timeout=1.2,
        post_click_sleep=0.4,
    )
    if not ok:
        return False

    clicked = click_template_target(
        win,
        "template_owner_only_mine",
        offset=TEMPLATE_OWNER_ONLY_MINE_OFFSET,
        offset_key="template_owner_only_mine_offset",
        timeout=5,
        label="template_owner_only_mine",
        clicks=1,
    )
    if not clicked:
        return False

    time.sleep(0.8)
    checkpoint()
    return True


def clear_template_diagnosis_if_exists(win):
    log("Проверяю красный крест диагноза в шаблоне")

    loc = locate_image_on_screen(
        "template_diagnosis_clear_cross",
        timeout=2.0,
    )

    if not loc:
        log("Красный крест диагноза в шаблоне не найден — пропускаю")
        return True

    final_x = loc.x + TEMPLATE_DIAGNOSIS_CLEAR_CROSS_OFFSET[0]
    final_y = loc.y + TEMPLATE_DIAGNOSIS_CLEAR_CROSS_OFFSET[1]

    log(f"Удаляю диагноз из шаблона: ({final_x}, {final_y})")

    if not debug_click_point(final_x, final_y):
        action = fail(win, f"Небезопасная точка крестика диагноза: ({final_x}, {final_y})")
        return action == "continue"

    pyautogui.click(final_x, final_y)
    time.sleep(0.5)
    checkpoint()
    return True


def choose_xray_template(win, task):
    template_key = getattr(task, "template_key", "") or ""
    template_name = getattr(task, "template_name", "") or template_key

    if not template_key:
        action = fail(
            win,
            f"Для исследования '{task.study_name}' не найден template_key.\n"
            f"Выбери шаблон вручную и нажми 'Продолжить'."
        )
        return action == "continue"

    log(f"Выбор рентген-шаблона: {template_name} ({template_key})")

    clicked = click_template_target(
        win,
        template_key,
        offset=TEMPLATE_USE_OFFSET,
        offset_key="template_use_offset",
        timeout=8,
        label=f"xray_template:{template_key}",
        clicks=1,
    )

    if not clicked:
        action = fail(
            win,
            f"Не удалось выбрать шаблон: {template_name} ({template_key}).\n"
            f"Выбери шаблон вручную и нажми 'Продолжить'."
        )
        return action == "continue"

    time.sleep(TEMPLATE_LOAD_WAIT)
    checkpoint()
    return True

def _save_template_offset(offset_key: str, dx: int, dy: int):
    data = _read_coords_json()
    data.setdefault("mis", {})
    data["mis"][offset_key] = [dx, dy]
    _write_coords_json(data)

    MIS_COORDS[offset_key] = [dx, dy]

    globals_map = {
        "visit_plus_offset": "VISIT_PLUS_OFFSET",
        "reason_field_offset": "REASON_FIELD_OFFSET",
        "goal_dropdown_offset": "GOAL_DROPDOWN_OFFSET",
        "history_menu_offset": "HISTORY_MENU_OFFSET",
        "history_fluoro_item_offset": "HISTORY_FLUORO_ITEM_OFFSET",
        "templates_anchor_offset": "TEMPLATES_ANCHOR_OFFSET",
        "template_use_offset": "TEMPLATE_USE_OFFSET",
        "diagnosis_drop_offset": "DIAGNOSIS_DROP_OFFSET",
        "diagnosis_code_offset": "DIAGNOSIS_CODE_OFFSET",
        "diagnosis_cancel_item_offset": "DIAGNOSIS_CANCEL_ITEM_OFFSET",
        "service_price_zero_offset": "SERVICE_PRICE_ZERO_OFFSET",
        "search_anchor_offset": "SEARCH_ANCHOR_OFFSET",
        "work_plus_offset": "WORK_PLUS_OFFSET",
        "study_date_label_offset": "STUDY_DATE_LABEL_OFFSET",
        "xray_service_item_offset": "XRAY_SERVICE_ITEM_OFFSET",
        "template_owner_dropdown_offset": "TEMPLATE_OWNER_DROPDOWN_OFFSET",
        "template_owner_only_mine_offset": "TEMPLATE_OWNER_ONLY_MINE_OFFSET",
        "template_diagnosis_clear_cross_offset": "TEMPLATE_DIAGNOSIS_CLEAR_CROSS_OFFSET",
        "template_select_button_offset": "TEMPLATE_SELECT_BUTTON_OFFSET",
        "xray_template_row_offset": "XRAY_TEMPLATE_ROW_OFFSET",
        "inpatient_yes_button_offset": "INPATIENT_YES_BUTTON_OFFSET",
        "add_diagnosis_no_button_offset": "ADD_DIAGNOSIS_NO_BUTTON_OFFSET",
    }
    if offset_key in globals_map:
        globals()[globals_map[offset_key]] = (dx, dy)


def _save_absolute_point(point_key: str, rel_x: int, rel_y: int):
    data = _read_coords_json()
    data.setdefault("mis", {})
    data["mis"][point_key] = [rel_x, rel_y]
    _write_coords_json(data)

    MIS_COORDS[point_key] = [rel_x, rel_y]

    globals_map = {
        "dob_click_point": "DOB_CLICK_POINT",
        "work_plus_fallback_point": "WORK_PLUS_FALLBACK_POINT",
    }
    if point_key in globals_map:
        globals()[globals_map[point_key]] = (rel_x, rel_y)


def interactive_template_click_adjustment(win, template_key, offset_key, loc, final_x, final_y, label):
    if not INTERACTIVE_CLICK_CALIBRATION:
        return final_x, final_y, False

    debug_click_point(final_x, final_y)

    choice = ui_adapt_action(f"{label}: что делать?")

    if choice == "skip":
        log(f"{label}: клик пропущен пользователем")
        return final_x, final_y, True

    if choice == "recalibrate":
        picked = pick_runtime_point(None, f"Выбери новую точку для {label}")
        if picked:
            picked_x, picked_y = picked
            dx = int(picked_x - loc.x)
            dy = int(picked_y - loc.y)
            _save_template_offset(offset_key, dx, dy)
            log(f"{label}: сохранён новый offset {offset_key} = [{dx}, {dy}]")
            return picked_x, picked_y, False

    if choice == "retry":
        log(f"{label}: повтор клика без изменения offset")
        return final_x, final_y, False

    # fallback
    return final_x, final_y, False


def interactive_absolute_point_adjustment(win, point_key, final_x, final_y, label):
    if not INTERACTIVE_CLICK_CALIBRATION:
        return final_x, final_y, False

    debug_click_point(final_x, final_y)

    choice = ui_adapt_action(f"{label}: что делать?")

    if choice == "skip":
        log(f"{label}: клик пропущен пользователем")
        return final_x, final_y, True

    if choice == "recalibrate":
        picked = pick_runtime_point(None, f"Выбери новую точку для {label}")
        if picked:
            picked_x, picked_y = picked
            rel_x = int(picked_x - win.left)
            rel_y = int(picked_y - win.top)
            _save_absolute_point(point_key, rel_x, rel_y)
            log(f"{label}: сохранена новая точка {point_key} = [{rel_x}, {rel_y}]")
            return picked_x, picked_y, False

    if choice == "retry":
        log(f"{label}: повтор клика")
        return final_x, final_y, False

    return final_x, final_y, False


def click_template_target(
    win,
    template_key,
    offset=(0, 0),
    offset_key=None,
    confidence=None,
    timeout=8,
    label=None,
    clicks=1
):
    loc, final_x, final_y = get_template_click_point(
        template_key=template_key,
        offset=offset,
        confidence=confidence,
        timeout=timeout,
    )

    if not loc:
        fail(win, f"Не найден шаблон: {template_key}")
        return None

    label = label or template_key

    log(
        f"Клик по {label}: "
        f"base=({loc.x},{loc.y}) offset=({offset[0]},{offset[1]}) final=({final_x},{final_y})"
    )

    if offset_key:
        final_x, final_y, skip_click = interactive_template_click_adjustment(
            win=win,
            template_key=template_key,
            offset_key=offset_key,
            loc=loc,
            final_x=final_x,
            final_y=final_y,
            label=label,
        )
        if skip_click:
            log(f"{label}: шаг пропущен пользователем")
            return final_x, final_y

    if not debug_click_point(final_x, final_y):
        fail(win, f"Небезопасная точка клика для {label}: ({final_x}, {final_y})")
        return None

    checkpoint()
    pyautogui.click(final_x, final_y, clicks=clicks, interval=0.15)
    checkpoint()
    time.sleep(0.3)
    checkpoint()
    return final_x, final_y

def adaptive_click_template_target(
    win,
    template_key: str,
    offset=(0, 0),
    offset_key=None,
    confidence=None,
    timeout=8,
    label=None,
    clicks=1,
    expected_template: str | None = None,
    expected_confidence=None,
    expected_checks=None,
    expected_pause=None,
    expected_probe_timeout=None,
    post_click_sleep=0.3,
):
    label = label or template_key

    while True:
        checkpoint()

        loc, final_x, final_y = get_template_click_point(
            template_key=template_key,
            offset=offset,
            confidence=confidence,
            timeout=timeout,
        )

        if not loc:
            action = fail(win, f"Не найден шаблон: {template_key}")
            if action == "continue":
                return True
            return False

        log(
            f"Адаптивный клик по {label}: "
            f"base=({loc.x},{loc.y}) offset=({offset[0]},{offset[1]}) final=({final_x},{final_y})"
        )

        if offset_key:
            final_x, final_y, skip_click = interactive_template_click_adjustment(
                win=win,
                template_key=template_key,
                offset_key=offset_key,
                loc=loc,
                final_x=final_x,
                final_y=final_y,
                label=label,
            )
            if skip_click:
                log(f"{label}: шаг пропущен пользователем")
                return True

        if not debug_click_point(final_x, final_y):
            action = fail(win, f"Небезопасная точка клика для {label}: ({final_x}, {final_y})")
            if action == "continue":
                return True
            return False

        checkpoint()
        pyautogui.click(final_x, final_y, clicks=clicks, interval=0.15)
        checkpoint()

        if post_click_sleep:
            time.sleep(post_click_sleep)
            checkpoint()

        if not expected_template:
            return True

        ok = wait_for_template_strict(
            expected_template,
            confidence=expected_confidence,
            checks=expected_checks,
            pause=expected_pause,
            probe_timeout=expected_probe_timeout,
        )
        checkpoint()

        if ok:
            log(f"{label}: ожидаемый шаблон подтвержден -> {expected_template}")
            return True

        action = ui_adapt_action(
            f"После клика по '{label}' не появился ожидаемый шаблон:\n"
            f"{expected_template}\n\n"
            f"Что делать?"
        )

        if action == "skip":
            log(f"{label}: пользователь выбрал пропуск шага")
            return True

        if action == "cancel":
            raise RuntimeError(f"Остановлено пользователем на шаге: {label}")

        if action == "recalibrate":
            picked = pick_runtime_point(None, f"Выбери новую точку для {label}")
            if picked:
                picked_x, picked_y = picked

                if offset_key:
                    dx = int(picked_x - loc.x)
                    dy = int(picked_y - loc.y)
                    _save_template_offset(offset_key, dx, dy)
                    log(f"{label}: сохранён новый offset {offset_key} = [{dx}, {dy}]")

                if not debug_click_point(picked_x, picked_y):
                    log(f"{label}: новая точка небезопасна, повторяю выбор")
                    continue

                checkpoint()
                pyautogui.click(picked_x, picked_y, clicks=clicks, interval=0.15)
                checkpoint()

                if post_click_sleep:
                    time.sleep(post_click_sleep)
                    checkpoint()

                ok2 = wait_for_template_strict(
                    expected_template,
                    confidence=expected_confidence,
                    checks=expected_checks,
                    pause=expected_pause,
                    probe_timeout=expected_probe_timeout,
                )
                checkpoint()

                if ok2:
                    log(f"{label}: после перекалибровки шаг подтвержден")
                    return True

                log(f"{label}: после перекалибровки ожидаемый шаблон всё ещё не найден")
                continue

        # retry
        log(f"{label}: повтор попытки")

def get_config_point(win, point_key):
    point = MIS_COORDS.get(point_key)
    if not point or len(point) != 2:
        raise RuntimeError(f"Не найдена точка в config: {point_key}")
    x = win.left + point[0]
    y = win.top + point[1]
    return x, y


def click_config_point(win, point_key, label=None, clicks=1):
    x, y = get_config_point(win, point_key)
    label = label or point_key

    log(f"Клик по точке {label}: final=({x},{y})")

    x, y, skip_click = interactive_absolute_point_adjustment(
        win=win,
        point_key=point_key,
        final_x=x,
        final_y=y,
        label=label,
    )
    if skip_click:
        return x, y

    if not debug_click_point(x, y):
        fail(win, f"Небезопасная точка: {label} ({x},{y})")
        return None

    checkpoint()
    pyautogui.click(x, y, clicks=clicks, interval=0.15)
    checkpoint()
    time.sleep(0.3)
    checkpoint()
    return x, y


def ask_user_checkpoint(label: str):
    ok = ui_checkpoint(f"{label}\n\nПродолжить?")
    if not ok:
        raise RuntimeError(f"Остановлено пользователем на этапе: {label}")


def ask_manual_edit_continue():
    ok = ui_manual_continue(
        "Внеси правки в протокол вручную,\nзатем нажми 'Продолжить'"
    )
    if not ok:
        raise RuntimeError("Остановлено пользователем на этапе ручной правки")


def press_seq(*keys, pause=0.35):
    for key in keys:
        pyautogui.press(key)
        log(f"Клавиша: {key}")
        time.sleep(pause)
        checkpoint()


def current_date_str():
    return datetime.now().strftime("%d.%m.%Y")


def normalize_study_date(study_date: str | None) -> str:
    if not study_date:
        return current_date_str()

    value = study_date.strip().replace(",", ".").replace("-", ".").replace("/", ".")
    parts = value.split(".")

    if len(parts) == 3:
        day, month, year = parts
        if len(day) == 1:
            day = "0" + day
        if len(month) == 1:
            month = "0" + month
        if len(year) == 2:
            year = "20" + year
        return f"{day}.{month}.{year}"

    return current_date_str()


def set_clipboard_text(text: str):
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID

    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL

    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL

    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    data = text + "\x00"
    data_size = len(data.encode("utf-16-le"))

    h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, data_size)
    if not h_global:
        raise RuntimeError("GlobalAlloc failed while setting clipboard")

    locked_mem = kernel32.GlobalLock(h_global)
    if not locked_mem:
        raise RuntimeError("GlobalLock failed while setting clipboard")

    ctypes.memmove(locked_mem, data.encode("utf-16-le"), data_size)
    kernel32.GlobalUnlock(h_global)

    if not user32.OpenClipboard(None):
        raise RuntimeError("OpenClipboard failed")

    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("EmptyClipboard failed")

        if not user32.SetClipboardData(CF_UNICODETEXT, h_global):
            raise RuntimeError("SetClipboardData failed")

        h_global = None
    finally:
        user32.CloseClipboard()


def paste_text_via_context_menu(field_x: int, field_y: int, text: str):
    log(f"Кладу ФИО в буфер: {text}")
    set_clipboard_text(text)
    time.sleep(0.25)
    checkpoint()

    log("Открываю контекстное меню поля поиска")
    pyautogui.rightClick(field_x, field_y)
    time.sleep(PASTE_CONTEXT_MENU_WAIT)
    checkpoint()

    loc = wait_for_template_strict(
        "paste_context_item",
        checks=3,
        pause=0.4,
        probe_timeout=1.2
    )
    checkpoint()
    if not loc:
        raise RuntimeError("Не найден пункт 'Вставить' в контекстном меню")

    pyautogui.click(loc.x, loc.y)
    checkpoint()
    time.sleep(0.8)
    checkpoint()

def search_patient(win, fio: str):
    log("Поиск якоря поиска пациента")
    anchor = locate_image_on_screen("search_anchor", timeout=8)
    if not anchor:
        fail(win, "Не найден search_anchor")
        return False

    anchor_x = anchor.x + SEARCH_ANCHOR_OFFSET[0]
    anchor_y = anchor.y + SEARCH_ANCHOR_OFFSET[1]

    field_x = anchor_x - SEARCH_ANCHOR_X_OFFSET
    field_y = anchor_y

    log(
        f"Клик в поле поиска: "
        f"anchor_base=({anchor.x},{anchor.y}) anchor_offset=({SEARCH_ANCHOR_OFFSET[0]},{SEARCH_ANCHOR_OFFSET[1]}) "
        f"final_field=({field_x},{field_y})"
    )
    ok = debug_click_point(field_x, field_y)
    if not ok:
        return False
    checkpoint()
    time.sleep(0.25)
    checkpoint()
    pyautogui.click(field_x, field_y)
    checkpoint()
    time.sleep(0.25)
    checkpoint()

    log("Очищаю поле поиска")
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    checkpoint()
    pyautogui.press("backspace")
    time.sleep(0.25)
    checkpoint()

    log("Стабилизирую фокус поля")
    pyautogui.press("right")
    time.sleep(0.1)
    checkpoint()
    pyautogui.press("left")
    time.sleep(0.1)
    checkpoint()

        
    try:
        paste_text_via_context_menu(field_x, field_y, fio)
    except Exception as e:
        fail(win, f"Не удалось вставить ФИО: {e}")
        return False

    log(f"ФИО отправлено в поле поиска: {fio}")
    return True

def find_patient_by_birth_date_and_click(win, birth_date: str, max_rows=MAX_PATIENT_ROWS):
    log(f"[V2 OCRx2] Поиск пациента по дате рождения: {birth_date}")

    time.sleep(1.0)
    checkpoint()

    exact_matches = []
    partial_matches = []
    weak_matches = []

    for i in range(max_rows):
        checkpoint()

        region = (
            DOB_REGION[0],
            DOB_REGION[1] + i * ROW_HEIGHT,
            DOB_REGION[2],
            DOB_REGION[3],
        )

        img = screenshot_region(win, region)

        try:
            raw_text = ocr_date_image(img)
        except Exception as e:
            log(f"OCR ошибка на строке {i + 1}: {e}")
            raw_text = ""

        matched, match_type = compare_birth_date_candidate(birth_date, raw_text)

        if i == 0:
            save_region_screenshot(win, region, "dob_row1_debug")

        log(
            f"[V2 OCRx2] Строка {i + 1}: OCR={repr(raw_text)} "
            f"| matched={matched} | match_type={match_type or '-'}"
        )

        if not matched:
            continue

        row_data = (i, region, raw_text)

        if match_type == "exact":
            exact_matches.append(row_data)
        elif match_type == "partial":
            partial_matches.append(row_data)
        elif match_type == "weak":
            weak_matches.append(row_data)

    chosen = None
    chosen_type = ""

    if exact_matches:
        chosen = exact_matches[0]
        chosen_type = "exact"
    elif partial_matches:
        chosen = partial_matches[0]
        chosen_type = "partial"
    elif weak_matches:
        # слабые совпадения опаснее — не кликаем молча
        log("[V2 OCRx2] Найдены только слабые совпадения")
        action = fail(
            win,
            f"Дата рождения {birth_date} распознана неуверенно. "
            f"Рекомендуется выбрать пациента вручную.",
            rel_region=DOB_REGION
        )
        if action == "continue":
            wait_manual_patient_selection(MANUAL_PATIENT_SELECT_WAIT)
            return True
        return False

    if not chosen:
        log("[V2 OCRx2] Совпадений не найдено")
        action = fail(win, f"Пациент с датой рождения {birth_date} не найден", rel_region=DOB_REGION)
        if action == "continue":
            log("[V2 OCRx2] Переход в ручной выбор пациента")
            wait_manual_patient_selection(MANUAL_PATIENT_SELECT_WAIT)
            return True
        return False

    i, region, raw_text = chosen

    click_point = (
        region[0] + 15,
        region[1] + region[3] // 2,
    )

    log(
        f"[V2 OCRx2] Выбрана строка {i + 1} ({chosen_type}) "
        f"OCR={repr(raw_text)} -> click={click_point}"
    )

    click_rel(win, click_point, clicks=1, button="left")
    time.sleep(0.6)
    checkpoint()

    return True


def open_visit(win, study_date=None):
    log("Открытие нового приема через плюс")
    ok = adaptive_click_template_target(
        win=win,
        template_key="visit_plus",
        offset=VISIT_PLUS_OFFSET,
        offset_key="visit_plus_offset",
        timeout=8,
        label="visit_plus",
        clicks=1,
        expected_template=None,
        expected_checks=WAIT_CHECKS,
        expected_pause=WAIT_PAUSE,
        expected_probe_timeout=WAIT_PROBE_TIMEOUT,
        post_click_sleep=0.8,
    )
    if not ok:
        return False

    checkpoint()

    dt = normalize_study_date(study_date)
    log(f"Ввожу дату в стартовом окне: {dt}")

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    checkpoint()

    pyautogui.press("backspace")
    time.sleep(0.1)
    checkpoint()

    pyautogui.write(dt, interval=0.02)
    time.sleep(0.3)
    checkpoint()

    return True


def handle_post_visit_plus_flow(win):
    log("Подтверждаю стартовую дату через Enter")
    pyautogui.press("enter")
    time.sleep(1.0)
    checkpoint()

    log("Проверяю, появилось ли окно направления")
    loc = wait_for_template_strict(
        "without_referral",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=min(WAIT_PROBE_TIMEOUT, WITHOUT_REFERRAL_TIMEOUT)
    )
    checkpoint()

    if loc:
        log("Найдено окно направления -> выбираю 'Прием без направления'")
        pyautogui.click(loc.x, loc.y)
        checkpoint()
        time.sleep(1.0)
        checkpoint()
    else:
        log("Окно направления не появилось")

    log("Жду открытия окна приема (reason_field)")
    ready = wait_for_template_strict(
        "reason_field",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()

    if not ready:
        fail(win, "Окно приема не открылось (reason_field не найден)")
        return False

    log("Окно приема открыто")
    return True


def handle_inpatient_popup_if_present(win):
    """
    Если после создания приема появляется окно:
    'Пациент стационарный, вести прием в рамках стационара?'
    — нажимаем Да.
    Затем, если появляется окно 'Добавить диагноз?' — нажимаем Нет.

    Возвращает:
    True  -> стационарное окно было обработано
    False -> стационарного окна не было
    """
    log("Проверяю окно стационарного пациента")

    loc = locate_image_on_screen(
        "inpatient_question",
        timeout=1.5,
    )

    if not loc:
        log("Окно стационарного пациента не появилось")
        return False

    log("Найдено окно стационарного пациента -> нажимаю Да")

    clicked = click_template_target(
        win,
        "inpatient_yes_button",
        offset=INPATIENT_YES_BUTTON_OFFSET,
        offset_key="inpatient_yes_button_offset",
        timeout=4,
        label="inpatient_yes_button",
        clicks=1,
    )
    if not clicked:
        fail(win, "Не удалось нажать Да в окне стационарного пациента")
        return False

    time.sleep(0.8)
    checkpoint()

    log("Проверяю окно добавления диагноза")

    loc2 = locate_image_on_screen(
        "add_diagnosis_question",
        timeout=2.0,
    )

    if loc2:
        log("Найдено окно добавления диагноза -> нажимаю Нет")

        clicked2 = click_template_target(
            win,
            "add_diagnosis_no_button",
            offset=ADD_DIAGNOSIS_NO_BUTTON_OFFSET,
            offset_key="add_diagnosis_no_button_offset",
            timeout=4,
            label="add_diagnosis_no_button",
            clicks=1,
        )
        if not clicked2:
            fail(win, "Не удалось нажать Нет в окне добавления диагноза")
            return False

        time.sleep(0.8)
        checkpoint()
    else:
        log("Окно добавления диагноза не появилось")

    return True



def fill_reason_code(win):
    log("Выбор 'Повод обращения' через ввод кода 8")

    click_template_target(
        win,
        "reason_field",
        offset=REASON_FIELD_OFFSET,
        offset_key="reason_field_offset",
        timeout=6,
        label="reason_field"
    )
    time.sleep(0.2)
    checkpoint()

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    checkpoint()
    pyautogui.press("backspace")
    time.sleep(0.1)
    checkpoint()

    pyautogui.write("8", interval=0.03)
    time.sleep(0.2)
    checkpoint()
    pyautogui.press("enter")
    time.sleep(0.5)
    checkpoint()

    log("Повод обращения выбран")


def fill_goal_complex(win):
    log("Выбор 'Цель обращения'")
    click_template_target(
        win,
        "goal_dropdown",
        offset=GOAL_DROPDOWN_OFFSET,
        offset_key="goal_dropdown_offset",
        timeout=6,
        label="goal_dropdown"
    )

    time.sleep(0.3)
    checkpoint()
    pyautogui.press("pgdn")
    time.sleep(0.2)
    checkpoint()
    pyautogui.press("up")
    time.sleep(0.2)
    checkpoint()
    pyautogui.press("enter")
    time.sleep(0.5)
    checkpoint()

    log("Цель обращения выбрана")


def open_work_service(win):
    log("Открытие выбора работы/услуги")

    ok = adaptive_click_template_target(
        win=win,
        template_key="work_plus",
        offset=WORK_PLUS_OFFSET,
        offset_key="work_plus_offset",
        timeout=6,
        label="work_plus",
        clicks=1,
        expected_template="service_price_zero",
        expected_checks=max(3, int(SERVICE_LIST_TIMEOUT // max(1.0, SERVICE_LIST_PROBE_TIMEOUT))),
        expected_pause=1.0,
        expected_probe_timeout=SERVICE_LIST_PROBE_TIMEOUT,
        post_click_sleep=SERVICE_WINDOW_WAIT,
    )

    if ok:
        return True

    log("Fallback: пробую координату work_plus_fallback_point")

    x, y = get_config_point(win, "work_plus_fallback_point")

    if not debug_click_point(x, y):
        fail(win, "Fallback точка work_plus небезопасна")
        return False

    pyautogui.click(x, y)
    checkpoint()
    time.sleep(SERVICE_WINDOW_WAIT)
    checkpoint()

    # проверяем открылось ли окно услуг
    loc = wait_for_template_strict(
        "service_price_zero",
        checks=3,
        pause=1.0,
        probe_timeout=SERVICE_LIST_PROBE_TIMEOUT
    )
    checkpoint()

    if not loc:
        fail(win, "После fallback не открылся список услуг")
        return False

    return True


def choose_first_service(win):
    log("Ожидание появления списка услуг / шаблона 0,00 РУБ")

    if USE_SMART_SERVICE_WAIT:
        checks = max(3, int(SERVICE_LIST_TIMEOUT // max(1.0, SERVICE_LIST_PROBE_TIMEOUT)))
        loc = wait_for_template_strict(
            "service_price_zero",
            checks=checks,
            pause=1.0,
            probe_timeout=SERVICE_LIST_PROBE_TIMEOUT
        )
        checkpoint()
    else:
        time.sleep(SERVICE_WINDOW_WAIT)
        checkpoint()
        loc = locate_image_on_screen("service_price_zero", timeout=3)

    if not loc:
        action = fail(win, "Не найден шаблон service_price_zero")
        if action != "continue":
            return False
        else:
            log("Продолжаю без выбора услуги")
            return True

    final_x = loc.x + SERVICE_PRICE_ZERO_OFFSET[0]
    final_y = loc.y + SERVICE_PRICE_ZERO_OFFSET[1]

    final_x, final_y, skip_click = interactive_template_click_adjustment(
        win=win,
        template_key="service_price_zero",
        offset_key="service_price_zero_offset",
        loc=loc,
        final_x=final_x,
        final_y=final_y,
        label="service_price_zero",
    )
    if not skip_click:
        pyautogui.click(final_x, final_y, clicks=2, interval=0.2)
        checkpoint()

    time.sleep(0.6)
    checkpoint()
    log("Подтверждаю выбор услуги: F2")
    pyautogui.press("f2")
    time.sleep(1.0)
    checkpoint()
    return True


def open_history_fluoro(win):
    log("Открытие меню История болезни")
    clicked = click_template_target(
        win,
        "history_menu",
        offset=HISTORY_MENU_OFFSET,
        offset_key="history_menu_offset",
        timeout=8,
        label="history_menu"
    )
    if not clicked:
        return False

    time.sleep(max(HISTORY_MENU_WAIT, 1.5))
    checkpoint()

    log("Выбор флюорографического исследования")
    clicked = click_template_target(
        win,
        "history_fluoro_item",
        offset=HISTORY_FLUORO_ITEM_OFFSET,
        offset_key="history_fluoro_item_offset",
        timeout=6,
        label="history_fluoro_item"
    )
    if not clicked:
        return False

    log("Проверяю открытие протокола по якорю 'Просмотр ИБ'")
    loc = wait_for_template_strict(
        "protocol_anchor",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()

    if not loc:
        fail(win, "Протокол не открылся: якорь 'Просмотр ИБ' не найден")
        return False

    log("Протокол открыт")
    time.sleep(0.6)
    checkpoint()
    return True


def choose_template(win, mode: str):
    if mode not in VALID_MODES:
        raise ValueError(f"Неизвестный режим: {mode}")

    row_key = MODE_TEMPLATES[mode]
    log(f"Открываю меню 'Шаблоны' для режима: {mode} -> {row_key}")

    ok = adaptive_click_template_target(
        win=win,
        template_key="templates_anchor",
        offset=TEMPLATES_ANCHOR_OFFSET,
        offset_key="templates_anchor_offset",
        timeout=8,
        label="templates_anchor",
        clicks=1,
        expected_template="template_use",
        expected_checks=WAIT_CHECKS,
        expected_pause=WAIT_PAUSE,
        expected_probe_timeout=WAIT_PROBE_TIMEOUT,
        post_click_sleep=0.8,
    )
    if not ok:
        return False

    log("Нажимаю 'Выбрать' адаптивно")
    ok = adaptive_click_template_target(
        win=win,
        template_key="template_use",
        offset=TEMPLATE_USE_OFFSET,
        offset_key="template_use_offset",
        timeout=5,
        label="template_use",
        clicks=1,
        expected_template=row_key,
        expected_checks=WAIT_CHECKS,
        expected_pause=WAIT_PAUSE,
        expected_probe_timeout=WAIT_PROBE_TIMEOUT,
        post_click_sleep=0.8,
    )
    if not ok:
        return False

    log(f"Выбор шаблона двойным кликом: {row_key}")
    row_loc = wait_for_template_strict(
        row_key,
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()
    if not row_loc:
        fail(win, f"Строка шаблона {row_key} не найдена")
        return False

    pyautogui.click(row_loc.x, row_loc.y, clicks=2, interval=0.2)
    checkpoint()
    time.sleep(0.5)
    checkpoint()

    log("После двойного клика: Space -> пауза -> Space")
    pyautogui.press("space")
    time.sleep(0.8)
    checkpoint()
    pyautogui.press("space")
    time.sleep(TEMPLATE_LOAD_WAIT)
    checkpoint()

    return True


def handle_sign_password_if_needed(win):
    log("Ожидание окна подписи")

    dialog = wait_for_template_strict(
        "sign_password_dialog",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()
    if not dialog:
        log("Окно подписи не появилось")
        return False

    log("Окно подписи найдено")

    field = wait_for_template_strict(
        "sign_password_field",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()
    if field:
        pyautogui.click(field.x, field.y)
        checkpoint()
        log("Поле пароля найдено по шаблону")
    else:
        log("Поле пароля не найдено по шаблону -> fallback-клик в центр диалога")
        pyautogui.click(dialog.x, dialog.y)
        checkpoint()
        time.sleep(0.5)
        checkpoint()

    time.sleep(0.2)
    checkpoint()

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    checkpoint()
    pyautogui.press("backspace")
    time.sleep(0.1)
    checkpoint()

    pyautogui.write(MIS_SETTINGS["sign_password"], interval=0.03)
    time.sleep(0.2)
    checkpoint()
    pyautogui.press("enter")
    time.sleep(1.0)
    checkpoint()

    log("Пароль подписи введен")
    return True


def fill_template_date_and_sign(win, study_date=None):
    dt = normalize_study_date(study_date)
    log(f"Ввод даты исследования: {dt}")

    ok = adaptive_click_template_target(
        win=win,
        template_key="study_date_label",
        offset=STUDY_DATE_LABEL_OFFSET,
        offset_key="study_date_label_offset",
        timeout=8,
        label="study_date_label",
        clicks=1,
        expected_template=None,
        post_click_sleep=0.3,
    )
    if not ok:
        fail(win, "Не удалось установить фокус в поле даты исследования")
        return False

    pyautogui.click()
    time.sleep(0.1)
    checkpoint()

    pyautogui.press("end")
    time.sleep(0.1)
    checkpoint()

    for _ in range(12):
        pyautogui.press("backspace")
        time.sleep(0.03)
    checkpoint()

    for _ in range(4):
        pyautogui.press("delete")
        time.sleep(0.03)
    checkpoint()

    pyautogui.write(dt, interval=0.02)
    time.sleep(0.4)
    checkpoint()

    log("Цепочка после даты: F2 -> Space")
    pyautogui.press("f2")
    time.sleep(0.8)
    checkpoint()

    pyautogui.press("space")
    time.sleep(0.8)
    checkpoint()

    handle_sign_password_if_needed(win)
    return True


def cancel_diagnosis(win):
    log("Отмена диагноза: шаг 1 -> diagnosis_drop")

    ok = adaptive_click_template_target(
        win=win,
        template_key="diagnosis_drop",
        offset=DIAGNOSIS_DROP_OFFSET,
        offset_key="diagnosis_drop_offset",
        timeout=6,
        label="diagnosis_drop",
        clicks=1,
        expected_template="diagnosis_code",
        expected_checks=WAIT_CHECKS,
        expected_pause=WAIT_PAUSE,
        expected_probe_timeout=WAIT_PROBE_TIMEOUT,
        post_click_sleep=0.5,
    )
    if not ok:
        return False

    log("Отмена диагноза: шаг 2 -> diagnosis_code")
    ok = adaptive_click_template_target(
        win=win,
        template_key="diagnosis_code",
        offset=DIAGNOSIS_CODE_OFFSET,
        offset_key="diagnosis_code_offset",
        timeout=6,
        label="diagnosis_code",
        clicks=1,
        expected_template="diagnosis_cancel_item",
        expected_checks=WAIT_CHECKS,
        expected_pause=WAIT_PAUSE,
        expected_probe_timeout=WAIT_PROBE_TIMEOUT,
        post_click_sleep=0.5,
    )
    if not ok:
        return False

    log("Отмена диагноза: шаг 3 -> diagnosis_cancel_item")
    ok = adaptive_click_template_target(
        win=win,
        template_key="diagnosis_cancel_item",
        offset=DIAGNOSIS_CANCEL_ITEM_OFFSET,
        offset_key="diagnosis_cancel_item_offset",
        timeout=6,
        label="diagnosis_cancel_item",
        clicks=1,
        expected_template=None,
        post_click_sleep=0.8,
    )
    if not ok:
        return False

    return True


def final_save_chain():
    log("Финальная цепочка: F2 -> Space -> Space")
    press_seq("f2", pause=0.8)
    press_seq("space", pause=0.8)
    press_seq("space", pause=0.8)


def nudge_search_selection():
    log("Сбрасываю выделение/фокус на экране поиска")
    pyautogui.press("left")
    time.sleep(0.15)
    checkpoint()
   


def ensure_search_screen_ready(win):
    log("Проверка: МИС вернулась на экран поиска пациента")

    anchor = wait_for_template_strict(
        "search_anchor",
        checks=max(WAIT_CHECKS, 4),
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()
    if not anchor:
        fail(win, "МИС не вернулась на экран поиска пациента")
        return False

    nudge_search_selection()
    log("Экран поиска пациента подтвержден")
    return True


def clear_focus_after_finish(win):
    log("Сброс фокуса (ESC + клик)")
    pyautogui.press("esc")
    time.sleep(0.2)
    checkpoint()

    x, y = win.center
    pyautogui.click(x, y)
    checkpoint()
    time.sleep(0.3)
    checkpoint()


def stop_at_stage(win, stage_name: str, stop_stage: str | None, label: str) -> bool:
    if stop_stage != stage_name:
        return False

    log(f"Остановка на этапе: {label}")
    save_window_screenshot(win, f"stop_{stage_name}")
    clear_focus_after_finish(win)
    return True


def stop_at_stage_open_card(win, stage_name: str, stop_stage: str | None, label: str) -> bool:
    if stop_stage != stage_name:
        return False

    log(f"Остановка в режиме открытой карточки на этапе: {label}")
    save_window_screenshot(win, f"open_card_stop_{stage_name}")
    clear_focus_after_finish(win)
    return True


def ensure_open_patient_card(win):
    log("Проверка: открыта ли карточка пациента / окно приема")

    loc = wait_for_template_strict(
        "reason_field",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT
    )
    checkpoint()

    if not loc:
        action = fail(win, "Не найдено окно открытой карточки пациента (reason_field)")
        if action == "continue":
            return True
        return False

    log("Открытая карточка пациента подтверждена")
    return True


def continue_from_open_patient_card(task, step_mode=False, stop_stage: str | None = None):
    if task.mode not in VALID_MODES:
        raise ValueError(f"Неизвестный режим: {task.mode}. Допустимые: {sorted(VALID_MODES)}")

    win = find_mis_window()
    log(f"Продолжение из открытой карточки. Режим: {task.mode}")

    ok = ensure_open_patient_card(win)
    checkpoint()
    if not ok:
        return

    fill_reason_code(win)
    checkpoint()
    fill_goal_complex(win)
    checkpoint()

    if stop_at_stage_open_card(win, "after_fill_basic", stop_stage, "После заполнения повода и цели"):
        return

    if step_mode:
        ask_user_checkpoint("После заполнения повода и цели")



    ok = open_work_service(win)
    checkpoint()
    if not ok:
        return

    ok = choose_first_service(win)
    checkpoint()
    if not ok:
        return

    if stop_at_stage_open_card(win, "after_service", stop_stage, "После выбора услуги"):
        return

    if step_mode:
        ask_user_checkpoint("После выбора услуги")

    ok = open_history_fluoro(win)
    checkpoint()
    if not ok:
        return

    if stop_at_stage_open_card(win, "after_protocol", stop_stage, "После открытия протокола"):
        return

    ok = choose_template(win, mode=task.mode)
    checkpoint()
    if not ok:
        return

    ok = fill_template_date_and_sign(win, study_date=task.study_date)
    checkpoint()
    if not ok:
        return

    if stop_at_stage_open_card(win, "after_template_date", stop_stage, "После шаблона и ввода даты"):
        return

    if task.mode == "manual_edit":
        log("Режим manual_edit: остановка для ручной правки")
        ask_manual_edit_continue()
    elif step_mode:
        ask_user_checkpoint("После шаблона и ввода даты")

    ok = cancel_diagnosis(win)
    checkpoint()
    if not ok:
        return

    if stop_at_stage_open_card(win, "after_cancel_diagnosis", stop_stage, "После отмены диагноза"):
        return

    final_save_chain()

    log("Сценарий из открытой карточки завершен успешно")
    save_window_screenshot(win, "success_open_card")
    clear_focus_after_finish(win)

    if not ensure_search_screen_ready(win):
        return

    time.sleep(BETWEEN_PATIENTS_PAUSE)
    checkpoint()


def full_run(
    fio: str,
    birth_date: str,
    study_date=None,
    mode="normal",
    step_mode=False,
    stop_stage: str | None = None,
    controller=None,
    manual_patient_select=False,
):
    if controller is None:
        controller = RunController()
    set_active_controller(controller)

    try:
        if mode not in VALID_MODES:
            raise ValueError(f"Неизвестный режим: {mode}. Допустимые: {sorted(VALID_MODES)}")

        win = find_mis_window()
        log(f"Окно МИС активировано. Режим: {mode}")

        ok = search_patient(win, fio)
        checkpoint()
        if not ok:
            return

        if manual_patient_select:
            wait_manual_patient_selection(MANUAL_PATIENT_SELECT_WAIT)
            checkpoint()
        else:
            found = find_patient_by_birth_date_and_click(win, birth_date)
            checkpoint()
            if not found:
                return

        if stop_at_stage(win, "after_search", stop_stage, "После поиска пациента"):
            return

        if step_mode:
            ask_user_checkpoint("После ввода ФИО")

        # --- Открытие приема ---
        ok = open_visit(win, study_date=study_date)
        checkpoint()
        if not ok:
            return

        ok = handle_post_visit_plus_flow(win)
        checkpoint()
        if not ok:
            return

        if stop_at_stage(win, "after_open_visit", stop_stage, "После открытия приема"):
            return

        # --- Повод и цель ---
        fill_reason_code(win)
        checkpoint()

        fill_goal_complex(win)
        checkpoint()

        if stop_at_stage(win, "after_fill_basic", stop_stage, "После повода и цели"):
            return

        # --- Услуга ---
        ok = open_work_service(win)
        checkpoint()
        if not ok:
            return

        ok = choose_first_service(win)
        checkpoint()
        if not ok:
            return

        if stop_at_stage(win, "after_service", stop_stage, "После выбора услуги"):
            return

        # --- Протокол ---
        ok = open_history_fluoro(win)
        checkpoint()
        if not ok:
            return

        if stop_at_stage(win, "after_protocol", stop_stage, "После протокола"):
            return

        ok = choose_template(win, mode=mode)
        checkpoint()
        if not ok:
            return

        ok = fill_template_date_and_sign(win, study_date=study_date)
        checkpoint()
        if not ok:
            return

        if stop_at_stage(win, "after_template_date", stop_stage, "После шаблона"):
            return

        # --- Ручной режим ---
        if mode == "manual_edit":
            ask_manual_edit_continue()

        # --- Диагноз ---
        ok = cancel_diagnosis(win)
        checkpoint()
        if not ok:
            return

        if stop_at_stage(win, "after_cancel_diagnosis", stop_stage, "После диагноза"):
            return

        # --- Финал ---
        final_save_chain()

        log("Сценарий завершен успешно")
        save_window_screenshot(win, "success_window")
        clear_focus_after_finish(win)

        if not ensure_search_screen_ready(win):
            return

        time.sleep(BETWEEN_PATIENTS_PAUSE)
        checkpoint()

    finally:
        set_active_controller(None)


if __name__ == "__main__":
    fio = "ТАРАКАНОВ СТАНИСЛАВ РОМАНОВИЧ"
    birth_date = "21.02.1996"
    study_date = "15.03.2026"
    mode = "normal"

    try:
        full_run(fio, birth_date, study_date=study_date, mode=mode, step_mode=False)
    except Exception as e:
        print("КРИТИЧЕСКАЯ ОШИБКА:", e)