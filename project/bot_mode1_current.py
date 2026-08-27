import time
import json
import re
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
from services.mode_mapper import get_protocol_template_key, get_protocol_names, load_protocols
from services.runtime_paths import TEMPLATES_DIR, LOG_DIR, config_path, template_path

from gui.ui_helper import (
    ui_error,
    ui_checkpoint,
    ui_manual_continue,
    ui_adapt_action,
)


LOG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_COORDS_PATH = config_path("coordinates.json")

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
GOAL_COMPLEX_ITEM_OFFSET = tuple(MIS_COORDS.get("goal_active_visit_item_offset", (0, 0)))
HISTORY_MENU_OFFSET = tuple(MIS_COORDS.get("history_menu_offset", (0, 0)))
HISTORY_FLUORO_ITEM_OFFSET = tuple(MIS_COORDS.get("history_fluoro_item_offset", (0, 0)))
HISTORY_XRAY_ITEM_OFFSET = tuple(MIS_COORDS.get("history_xray_item_offset", (0, 0)))
TEMPLATES_ANCHOR_OFFSET = tuple(MIS_COORDS.get("templates_anchor_offset", (0, 0)))
TEMPLATE_USE_OFFSET = tuple(MIS_COORDS.get("template_use_offset", (0, 0)))
DIAGNOSIS_DROP_OFFSET = tuple(MIS_COORDS.get("diagnosis_drop_offset", (0, 0)))
DIAGNOSIS_CODE_OFFSET = tuple(MIS_COORDS.get("diagnosis_code_offset", (0, 0)))
STUDY_DATE_LABEL_OFFSET = tuple(MIS_COORDS.get("study_date_label_offset", (220, 0)))
DIAGNOSIS_CANCEL_ITEM_OFFSET = tuple(MIS_COORDS.get("diagnosis_cancel_item_offset", (0, 0)))
DIAGNOSIS_CLOSE_ITEM_OFFSET = tuple(MIS_COORDS.get("diagnosis_close_item_offset", (0, 0)))
CASE_RESULT_LABEL_OFFSET = tuple(MIS_COORDS.get("case_result_label_offset", (125, 0)))
CASE_OUTCOME_LABEL_OFFSET = tuple(MIS_COORDS.get("case_outcome_label_offset", (125, 0)))
CASE_CLOSE_CURRENT_DIAGNOSIS_OFFSET = tuple(MIS_COORDS.get("case_close_current_diagnosis_offset", (0, 0)))
EPICRISIS_YES_SIGNED_OFFSET = tuple(MIS_COORDS.get("epicrisis_yes_signed_offset", (0, 0)))
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

# Старое settings.json оставляем только как fallback для совместимости.
LEGACY_MODE_TEMPLATES = dict(MIS_SETTINGS.get("mode_templates", {}))



# v34 naming migration:
# old v33 key goal_complex_item was renamed to goal_active_visit_item.
# Runtime uses only the new name; workplace coordinates can be migrated by UI reconfiguration.

def resolve_protocol_template_key(mode: str) -> str | None:
    """
    Источник истины для флюорографических протоколов — config/protocols.json.
    Старый settings.json используется только если protocols.json недоступен
    или в нём нет указанного режима.
    """
    row_key = get_protocol_template_key(mode, section="fluoro")
    if row_key:
        return row_key

    return LEGACY_MODE_TEMPLATES.get(mode)


def get_valid_modes() -> set[str]:
    modes = {
        str(item.get("key", "")).strip()
        for item in load_protocols("fluoro")
        if str(item.get("key", "")).strip()
    }

    # Fallback не ломает старые сохранённые сессии.
    modes.update(LEGACY_MODE_TEMPLATES.keys())
    return modes


def validate_protocol_mode(mode: str):
    row_key = resolve_protocol_template_key(mode)
    if row_key:
        return row_key

    valid = sorted(get_valid_modes())
    raise ValueError(
        f"Неизвестный протокол: {mode}. "
        f"Доступные режимы: {valid}"
    )


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


def _live_mis_templates() -> dict:
    try:
        return load_json("templates.json").get("mis", {})
    except Exception:
        return MIS_TEMPLATES


def template_file(key: str) -> Path:
    templates = _live_mis_templates()
    if key not in templates:
        raise KeyError(f"Шаблон не зарегистрирован в templates.json: {key}")
    return template_path(templates[key]["file"])


def template_conf(key: str, default: float = 0.82) -> float:
    templates = _live_mis_templates()
    return templates.get(key, {}).get("confidence", default)


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



def manual_recover_step(win, message: str, instruction: str | None = None) -> bool:
    """
    Универсальное ручное продолжение для любого этапа сценария.

    Если автоматический поиск/клик/проверка не сработали:
      1) пользователь выполняет текущий шаг вручную в МИС;
      2) нажимает "Продолжить";
      3) бот переходит к следующему этапу.

    Возвращает True при продолжении и False при отмене.
    """
    log(f"[MANUAL RECOVERY] {message}")

    text = message
    if instruction:
        text += f"\n\n{instruction}"
    text += "\n\nПосле выполнения нажмите «Продолжить»."

    ok = ui_manual_continue(text)

    if not ok:
        log("[MANUAL RECOVERY] Пользователь отменил сценарий")
        return False

    log("[MANUAL RECOVERY] Шаг выполнен вручную, продолжаю")
    checkpoint()
    return True


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


def _virtual_screen_bounds():
    """
    Physical bounds of the entire Windows virtual desktop.
    Supports negative coordinates and any monitor layout.
    """
    user32 = ctypes.windll.user32

    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    return left, top, left + width, top + height


def _win32_move_to(x, y):
    """
    Move cursor using physical Windows desktop coordinates.
    This deliberately bypasses pyautogui's primary-monitor assumptions.
    """
    user32 = ctypes.windll.user32

    left, top, right, bottom = _virtual_screen_bounds()

    if not (left <= int(x) < right and top <= int(y) < bottom):
        log(
            f"[WIN32] Координата вне виртуального рабочего стола: "
            f"({x},{y}); bounds=({left},{top})-({right},{bottom})"
        )
        return False

    ok = user32.SetCursorPos(int(x), int(y))
    if not ok:
        log(f"[WIN32] SetCursorPos не сработал для ({x},{y})")
        return False

    return True


def _win32_click(x, y, clicks=1, interval=0.15, button="left"):
    """
    Physical-coordinate click for multi-monitor Windows.
    """
    user32 = ctypes.windll.user32

    if not _win32_move_to(x, y):
        return False

    if button == "right":
        down_flag = 0x0008  # MOUSEEVENTF_RIGHTDOWN
        up_flag = 0x0010    # MOUSEEVENTF_RIGHTUP
    else:
        down_flag = 0x0002  # MOUSEEVENTF_LEFTDOWN
        up_flag = 0x0004    # MOUSEEVENTF_LEFTUP

    for i in range(max(1, int(clicks))):
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(up_flag, 0, 0, 0, 0)

        if i < clicks - 1:
            time.sleep(interval)

    return True


def _win32_press_key(key: str, presses=1, interval=0.12):
    """
    Send physical Windows keyboard events.
    More reliable for an RDP/MIS window than pyautogui.press on this workstation.
    """
    user32 = ctypes.windll.user32

    vk_map = {
        "pgdn": 0x22,      # VK_NEXT
        "pagedown": 0x22,
        "down": 0x28,      # VK_DOWN
        "up": 0x26,        # VK_UP
        "left": 0x25,
        "right": 0x27,
        "enter": 0x0D,
        "space": 0x20,
        "backspace": 0x08,
        "f2": 0x71,           # VK_F2
        "esc": 0x1B,          # VK_ESCAPE
    }

    vk = vk_map.get(str(key).lower())
    if vk is None:
        raise ValueError(f"Неизвестная Win32-клавиша: {key}")

    KEYEVENTF_KEYUP = 0x0002

    for i in range(max(1, int(presses))):
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.035)
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

        if i < presses - 1:
            time.sleep(interval)

    return True


def _live_mis_coord(key, fallback=None):
    """
    Read the current coordinates.json value immediately before an action.
    This prevents stale offsets after recalibration.
    """
    try:
        data = load_json("coordinates.json")
        value = data.get("mis", {}).get(key, fallback)
        return value
    except Exception as e:
        log(f"[COORDS] Не удалось перечитать {key}: {e}")
        return fallback


def debug_click_point(x, y):
    if x is None or y is None:
        log(f"[CLICK] Пропуск: координаты None ({x}, {y})")
        return False

    left, top, right, bottom = _virtual_screen_bounds()

    margin = 1
    if (
        int(x) < left + margin
        or int(y) < top + margin
        or int(x) >= right - margin
        or int(y) >= bottom - margin
    ):
        log(
            f"[CLICK] Пропуск: координаты вне виртуального рабочего стола "
            f"({x}, {y}); bounds=({left},{top})-({right},{bottom})"
        )
        return False

    ok = _win32_move_to(int(x), int(y))
    if ok:
        log(f"[CLICK] Курсор установлен Win32: ({int(x)}, {int(y)})")

    return ok


def sanitize_fio(value: str) -> str:
    """
    Нормализация ФИО перед поиском пациента.

    Разрешены только:
    - кириллица А-Я / а-я / Ё / ё
    - пробел
    - дефис

    Латиница, цифры, кавычки, слэши, вертикальные черты
    и прочие посторонние символы удаляются.
    """
    value = str(value or "")
    value = re.sub(r"[^А-Яа-яЁё\s-]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip(" -")


def validate_fio(value: str) -> bool:
    value = sanitize_fio(value)
    if not value:
        return False

    parts = value.split()
    if len(parts) < 2:
        return False

    if any(len(part.strip("-")) < 2 for part in parts):
        return False

    return True


def normalize_date_text(value: str) -> str:
    value = str(value or "").strip()

    value = (
        value
        .replace(",", ".")
        .replace("-", ".")
        .replace("/", ".")
        .replace("\\", ".")
        .replace("|", ".")
        .replace(":", ".")
        .replace(";", ".")
    )

    # Частые OCR-подмены буквами похожих цифр.
    replacements = {
        "O": "0", "o": "0", "О": "0", "о": "0",
        "I": "1", "i": "1", "l": "1", "L": "1", "І": "1",
        "З": "3", "з": "3",
        "Ч": "4", "ч": "4",
        "Б": "6", "б": "6",
        "В": "8", "в": "8",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^0-9.]", "", value)
    value = re.sub(r"\.{2,}", ".", value)
    return value.strip(".")


def normalize_birth_date(value: str) -> str:
    """
    Приводит распознанную дату к DD.MM.YYYY.
    Некорректная или нереалистичная дата -> пустая строка.
    """
    value = normalize_date_text(value)
    if not value:
        return ""

    digits = re.sub(r"\D", "", value)
    candidates = []

    if len(digits) == 8:
        candidates.append(f"{digits[0:2]}.{digits[2:4]}.{digits[4:8]}")

    elif len(digits) == 6:
        yy = int(digits[4:6])
        current_yy = datetime.now().year % 100
        year = 2000 + yy if yy <= current_yy else 1900 + yy
        candidates.append(f"{digits[0:2]}.{digits[2:4]}.{year}")

    parts = [p for p in value.split(".") if p]
    if len(parts) == 3:
        day, month, year = parts

        if len(day) == 1:
            day = "0" + day
        if len(month) == 1:
            month = "0" + month
        if len(year) == 2:
            yy = int(year)
            current_yy = datetime.now().year % 100
            year = str(2000 + yy if yy <= current_yy else 1900 + yy)

        candidates.append(f"{day}.{month}.{year}")

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)

        try:
            parsed = datetime.strptime(candidate, "%d.%m.%Y")
        except (ValueError, TypeError):
            continue

        if parsed.year < 1900:
            continue
        if parsed.date() > datetime.now().date():
            continue

        return parsed.strftime("%d.%m.%Y")

    return ""


def normalize_date_digits(value: str) -> str:
    normalized = normalize_birth_date(value)
    return normalized.replace(".", "") if normalized else ""


def compare_birth_date_candidate(target_date: str, candidate_text: str):
    """
    Безопасное сравнение даты рождения.

    Для автоматического выбора принимаем только нормализованную
    календарно корректную дату. Слабое совпадение по части года
    больше не используется.
    """
    target = normalize_birth_date(target_date)
    candidate = normalize_birth_date(candidate_text)

    if not target or not candidate:
        return False, ""

    if target == candidate:
        return True, "exact"

    target_digits = target.replace(".", "")
    candidate_digits = candidate.replace(".", "")

    if target_digits in candidate_digits:
        return True, "partial"

    return False, ""


def ocr_date_image(img: Image.Image):
    """
    Усиленный OCR даты рождения.

    Использует несколько масштабов, порогов и PSM.
    Возвращает только календарно корректную DD.MM.YYYY.
    Побеждает вариант, полученный независимыми OCR-проходами чаще всего.
    """
    checkpoint()

    gray = img.convert("L")
    found = []

    def add_candidate(raw: str, source: str):
        if not raw:
            return

        normalized = normalize_birth_date(raw)
        log(f"[DOB OCR] {source}: raw={raw!r} -> normalized={normalized!r}")

        if not normalized:
            return

        score = 100
        cleaned = normalize_date_text(raw)

        if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", cleaned):
            score += 100

        raw_digits = re.sub(r"\D", "", raw)
        if len(raw_digits) == 8:
            score += 50

        found.append((normalized, score, source))

    big2 = gray.resize(
        (gray.width * 2, gray.height * 2),
        Image.Resampling.LANCZOS,
    )
    big3 = gray.resize(
        (gray.width * 3, gray.height * 3),
        Image.Resampling.LANCZOS,
    )

    images = [
        ("gray", gray),
        ("x2", big2),
        ("x3", big3),
    ]

    for threshold in (120, 140, 155, 170, 185, 200, 215):
        bw = big3.point(
            lambda x, t=threshold: 0 if x < t else 255,
            "1",
        ).convert("L")
        images.append((f"threshold_{threshold}", bw))

    # Для даты цифры и привычные разделители.
    configs = (
        (7, "0123456789./,-"),
        (8, "0123456789./,-"),
        (11, "0123456789./,-"),
        (13, "0123456789./,-"),
    )

    for image_name, prepared in images:
        checkpoint()

        for psm, whitelist in configs:
            try:
                raw = pytesseract.image_to_string(
                    prepared,
                    lang="eng",
                    config=(
                        f"--psm {psm} "
                        f"-c tessedit_char_whitelist={whitelist}"
                    ),
                    timeout=2,
                )
            except pytesseract.TesseractError as e:
                log(f"[DOB OCR] Tesseract error: {e}")
                continue
            except RuntimeError as e:
                log(f"[DOB OCR] timeout: {e}")
                continue
            except Exception as e:
                log(f"[DOB OCR] unexpected: {e}")
                continue

            add_candidate(raw, f"{image_name}/psm{psm}")

    if not found:
        log("[DOB OCR] Корректная дата не найдена")
        return ""

    counts = {}

    for date_value, score, source in found:
        info = counts.setdefault(
            date_value,
            {"count": 0, "score": 0, "sources": []},
        )
        info["count"] += 1
        info["score"] += score
        info["sources"].append(source)

    ranked = sorted(
        counts.items(),
        key=lambda item: (item[1]["count"], item[1]["score"]),
        reverse=True,
    )

    best_date, best_info = ranked[0]

    log(
        f"[DOB OCR] BEST: {best_date} "
        f"| count={best_info['count']} "
        f"| score={best_info['score']} "
        f"| sources={best_info['sources']}"
    )

    return best_date


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
    """
    XRAY protocol after patient-specific template is loaded.

    There is no separate "Номер исследования" step in this route.
    Fill only:
      1. Описание
      2. Заключение
    """
    log("XRAY: заполнение протокола — только Описание и Заключение")

    ok = fill_xray_field_by_label(
        win=win,
        template_key="xray_field_description",
        text=task.description,
        offset=XRAY_FIELD_DESCRIPTION_OFFSET,
        offset_key="xray_field_description_offset",
        label="Описание",
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

    log("XRAY: Описание и Заключение заполнены")
    return True


def save_and_sign_xray_protocol(win):
    """
    XRAY protocol has no study-date field at this stage.
    Save/sign directly: F2 -> Space -> password dialog if present.
    """
    log("XRAY: сохранение и подпись без поиска поля даты исследования")

    pyautogui.press("f2")
    time.sleep(0.8)
    checkpoint()

    pyautogui.press("space")
    time.sleep(0.8)
    checkpoint()

    handle_sign_password_if_needed(win)
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

    # Ищем строку услуги отдельно, чтобы после медленной загрузки
    # не переходить сразу в ручной режим.
    loc = _wait_template_with_delayed_retry(
        "xray_service_item",
        first_checks=3,
        first_pause=0.8,
        first_probe_timeout=1.2,
        retry_delay=5.0,
        second_checks=5,
        second_pause=1.0,
        second_probe_timeout=1.2,
        label="xray_service_item",
    )

    if not loc:
        return manual_recover_step(
            win,
            "Не найден элемент xray_service_item после двух попыток.",
            "Выберите «Рентгенографическое исследование» вручную и нажмите «Продолжить».",
        )

    live_offset = _live_mis_coord(
        "xray_service_item_offset",
        list(XRAY_SERVICE_ITEM_OFFSET),
    )
    if not isinstance(live_offset, (list, tuple)) or len(live_offset) != 2:
        live_offset = list(XRAY_SERVICE_ITEM_OFFSET)

    final_x = int(loc.x) + int(live_offset[0])
    final_y = int(loc.y) + int(live_offset[1])

    log(
        f"xray_service_item: base=({loc.x},{loc.y}) "
        f"offset=({int(live_offset[0])},{int(live_offset[1])}) "
        f"final=({final_x},{final_y})"
    )

    if not _win32_click(final_x, final_y):
        return manual_recover_step(
            win,
            "Не удалось нажать найденное «Рентгенографическое исследование».",
            "Выберите его вручную и нажмите «Продолжить».",
        )

    time.sleep(0.8)
    checkpoint()
    return True



def open_templates_selector(win):
    """
    Explicitly performs:
      Шаблоны -> Выбрать

    XRAY flow previously skipped this and jumped directly to
    template_owner_dropdown.
    """
    log("Открываю 'Шаблоны'")

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
        post_click_sleep=0.6,
    )
    if not ok:
        return False

    log("Нажимаю 'Выбрать'")

    ok = click_template_target(
        win,
        "template_use",
        offset=TEMPLATE_USE_OFFSET,
        offset_key="template_use_offset",
        timeout=6,
        label="template_use",
        clicks=1,
    )
    if not ok:
        return False

    time.sleep(0.8)
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
    """
    Select the patient-specific XRAY template row.

    The template itself is NOT a control-only detector:
    if task.template_key points to its PNG, that PNG is a clickable row.
    We click its detected centre directly (no TEMPLATE_USE_OFFSET).
    """
    template_key = getattr(task, "template_key", "") or ""
    template_name = getattr(task, "template_name", "") or template_key

    if not template_key:
        action = fail(
            win,
            f"Для исследования '{task.study_name}' не найден template_key.\n"
            f"Выбери шаблон вручную и нажми 'Продолжить'.",
        )
        return action == "continue"

    log(f"Выбор рентген-шаблона: {template_name} ({template_key})")

    # Optional per-template offset if such a key was configured;
    # otherwise the action point is the centre of the found row PNG.
    dynamic_offset_key = f"{template_key}_offset"
    dynamic_offset = _live_mis_coord(dynamic_offset_key, [0, 0])
    if not isinstance(dynamic_offset, (list, tuple)) or len(dynamic_offset) != 2:
        dynamic_offset = [0, 0]

    clicked = click_template_target(
        win,
        template_key,
        offset=(int(dynamic_offset[0]), int(dynamic_offset[1])),
        offset_key=dynamic_offset_key,
        timeout=8,
        label=f"xray_template:{template_key}",
        clicks=2,
    )

    if not clicked:
        action = fail(
            win,
            f"Не удалось выбрать шаблон: {template_name} ({template_key}).\n"
            f"Выбери шаблон вручную и нажми 'Продолжить'.",
        )
        return action == "continue"

    # Keep the same post-selection behavior used by the fluoro template flow.
    time.sleep(0.45)
    checkpoint()

    log("После выбора рентген-шаблона: Space -> пауза -> Space")
    _win32_press_key("space")
    time.sleep(0.8)
    checkpoint()
    _win32_press_key("space")
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
        "goal_active_visit_item_offset": "GOAL_COMPLEX_ITEM_OFFSET",
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
        "diagnosis_close_item_offset": "DIAGNOSIS_CLOSE_ITEM_OFFSET",
        "case_result_label_offset": "CASE_RESULT_LABEL_OFFSET",
        "case_outcome_label_offset": "CASE_OUTCOME_LABEL_OFFSET",
        "case_close_current_diagnosis_offset": "CASE_CLOSE_CURRENT_DIAGNOSIS_OFFSET",
        "epicrisis_yes_signed_offset": "EPICRISIS_YES_SIGNED_OFFSET",
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
    current_offset = offset
    if offset_key:
        current_offset = _live_mis_coord(offset_key, list(offset))
        if isinstance(current_offset, (list, tuple)) and len(current_offset) == 2:
            offset = (int(current_offset[0]), int(current_offset[1]))

    loc, final_x, final_y = get_template_click_point(
        template_key=template_key,
        offset=offset,
        confidence=confidence,
        timeout=timeout,
    )

    if not loc:
        if manual_recover_step(
            win,
            f"Не найден элемент: {label or template_key}",
            "Выполните этот шаг вручную и оставьте МИС в состоянии, "
            "в котором бот должен перейти к следующему действию.",
        ):
            return (0, 0)
        return None

    label = label or template_key

    log(
        f"Клик по {label}: "
        f"base=({loc.x},{loc.y}) offset=({current_offset[0]},{current_offset[1]}) final=({final_x},{final_y})"
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
        if manual_recover_step(
            win,
            f"Не удалось автоматически нажать: {label}",
            "Нажмите нужный элемент вручную.",
        ):
            return (0, 0)
        return None

    checkpoint()
    if not _win32_click(final_x, final_y, clicks=clicks, interval=0.15):
        return manual_recover_step(
            win,
            f"Не удалось физически нажать: {label}",
            "Нажмите нужный элемент вручную.",
        )
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

        current_offset = offset
        if offset_key:
            live_value = _live_mis_coord(offset_key, list(offset))
            if isinstance(live_value, (list, tuple)) and len(live_value) == 2:
                current_offset = (int(live_value[0]), int(live_value[1]))

        loc, final_x, final_y = get_template_click_point(
            template_key=template_key,
            offset=current_offset,
            confidence=confidence,
            timeout=timeout,
        )

        if not loc:
            return manual_recover_step(
                win,
                f"Не найден элемент: {label}",
                "Выполните текущий шаг вручную и подготовьте экран к следующему этапу.",
            )

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
            return manual_recover_step(
                win,
                f"Не удалось автоматически нажать: {label}",
                "Нажмите нужный элемент вручную.",
            )

        checkpoint()
        if not _win32_click(final_x, final_y, clicks=clicks, interval=0.15):
            return manual_recover_step(
                win,
                f"Не удалось физически нажать: {label}",
                "Нажмите нужный элемент вручную.",
            )
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
                if not _win32_click(picked_x, picked_y, clicks=clicks, interval=0.15):
                    log(f"{label}: Win32-клик по новой точке не выполнен")
                    continue
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
        if manual_recover_step(
            win,
            f"Не удалось автоматически нажать точку: {label}",
            "Выполните этот клик вручную.",
        ):
            return (0, 0)
        return None

    checkpoint()
    if not _win32_click(x, y, clicks=clicks, interval=0.15):
        return manual_recover_step(
            win,
            f"Не удалось физически нажать точку: {label}",
            "Выполните этот клик вручную.",
        )
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
    """
    Patient FIO paste:
      focus field -> clipboard -> RMB -> template 'Вставить' -> click.

    The old Right/Left key stabilization is NOT restored.
    """
    log(f"Кладу ФИО в буфер: {text}")
    set_clipboard_text(text)
    time.sleep(0.2)
    checkpoint()

    # Reassert focus and clear previous text before RMB.
    if not _win32_click(field_x, field_y):
        raise RuntimeError(
            f"Не удалось установить фокус поля поиска ({field_x},{field_y})"
        )

    time.sleep(0.12)
    checkpoint()

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.08)
    checkpoint()

    _win32_press_key("backspace")
    time.sleep(0.12)
    checkpoint()

    log("Открываю контекстное меню поля поиска")
    if not _win32_click(field_x, field_y, button="right"):
        raise RuntimeError(
            f"Не удалось открыть контекстное меню в ({field_x},{field_y})"
        )

    time.sleep(PASTE_CONTEXT_MENU_WAIT)
    checkpoint()

    loc = wait_for_template_strict(
        "paste_context_item",
        checks=4,
        pause=0.35,
        probe_timeout=1.2,
    )
    checkpoint()

    if not loc:
        raise RuntimeError("Не найден пункт 'Вставить' в контекстном меню")

    if not _win32_click(loc.x, loc.y):
        raise RuntimeError(
            f"Не удалось нажать пункт Вставить в ({loc.x},{loc.y})"
        )

    time.sleep(0.55)
    checkpoint()



def search_patient(win, fio: str):
    original_fio = str(fio or "")
    fio = sanitize_fio(original_fio)

    log(f"ФИО перед поиском: raw={original_fio!r} -> normalized={fio!r}")

    if not validate_fio(fio):
        return manual_recover_step(
            win,
            f"Не удалось подготовить корректное ФИО автоматически.\n"
            f"Исходное: {original_fio}\n"
            f"После очистки: {fio}",
            "Введите ФИО пациента в поле поиска вручную.",
        )

    log("Поиск якоря поиска пациента")
    anchor = locate_image_on_screen("search_anchor", timeout=8)
    if not anchor:
        return manual_recover_step(
            win,
            "Не найдено поле поиска пациента.",
            f"Введите ФИО вручную: {fio}",
        )

    live_anchor_offset = _live_mis_coord(
        "search_anchor_offset",
        list(SEARCH_ANCHOR_OFFSET),
    )
    if not isinstance(live_anchor_offset, (list, tuple)) or len(live_anchor_offset) != 2:
        live_anchor_offset = list(SEARCH_ANCHOR_OFFSET)

    live_x_offset = _live_mis_coord(
        "search_anchor_x_offset",
        SEARCH_ANCHOR_X_OFFSET,
    )

    anchor_x = anchor.x + int(live_anchor_offset[0])
    anchor_y = anchor.y + int(live_anchor_offset[1])

    field_x = anchor_x - int(live_x_offset)
    field_y = anchor_y

    log(
        f"Клик в поле поиска: "
        f"anchor_base=({anchor.x},{anchor.y}) "
        f"anchor_offset=({int(live_anchor_offset[0])},{int(live_anchor_offset[1])}) "
        f"x_offset={int(live_x_offset)} "
        f"final_field=({field_x},{field_y})"
    )

    if not debug_click_point(field_x, field_y):
        return manual_recover_step(
            win,
            "Не удалось автоматически установить курсор в поле поиска пациента.",
            f"Введите ФИО вручную: {fio}",
        )

    checkpoint()
    time.sleep(0.25)

    if not _win32_click(field_x, field_y):
        return manual_recover_step(
            win,
            "Не удалось физически нажать поле поиска пациента.",
            f"Введите ФИО вручную: {fio}",
        )

    checkpoint()
    time.sleep(0.25)

    try:
        paste_text_via_context_menu(field_x, field_y, fio)
    except Exception as e:
        return manual_recover_step(
            win,
            f"Не удалось автоматически вставить ФИО: {e}",
            f"Введите ФИО вручную: {fio}",
        )

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
        return manual_recover_step(
            win,
            f"Дата рождения {birth_date} распознана неуверенно.",
            "Выберите нужную строку пациента вручную.",
        )

    if not chosen:
        log("[V2 OCRx2] Совпадений не найдено")
        if manual_recover_step(
            win,
            f"Пациент с датой рождения {birth_date} не найден автоматически.",
            "Выберите нужную строку пациента вручную.",
        ):
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


def _wait_reason_field_after_visit(win, label="Окно приёма"):
    """
    Heavy MIS point: wait for reason_field with three delayed retries.
    """
    ready = _wait_template_with_delayed_retry(
        "reason_field",
        first_checks=2,
        first_pause=0.8,
        first_probe_timeout=WAIT_PROBE_TIMEOUT,
        retry_delay=5.0,
        retry_rounds=3,
        second_checks=2,
        second_pause=0.8,
        second_probe_timeout=WAIT_PROBE_TIMEOUT,
        label=label,
    )
    checkpoint()
    return bool(ready)


def _locate_optional_template(template_key: str, timeout=1.5):
    """Optional detector: missing/unconfigured PNG must never crash the flow."""
    try:
        return locate_image_on_screen(template_key, timeout=timeout)
    except (FileNotFoundError, KeyError) as e:
        log(f"[OPTIONAL TEMPLATE] {template_key}: шаблон не настроен; пропускаю ({e})")
        return None
    except Exception as e:
        log(f"[OPTIONAL TEMPLATE] {template_key}: ошибка проверки; пропускаю ({e})")
        return None


def _find_visit_branch_once():
    """
    Detect which screen appeared after confirming the start date.

    Priority:
      inpatient_question -> without_referral -> reason_field

    Missing optional inpatient PNG must not crash normal workplaces.
    """
    inpatient = _locate_optional_template("inpatient_question", timeout=0.8)
    if inpatient:
        return "inpatient", inpatient

    try:
        without_ref = locate_image_on_screen("without_referral", timeout=0.8)
    except Exception:
        without_ref = None
    if without_ref:
        return "without_referral", without_ref

    try:
        reason = locate_image_on_screen("reason_field", timeout=0.8)
    except Exception:
        reason = None
    if reason:
        return "ready", reason

    return None, None


def _wait_visit_branch_after_enter():
    """
    Heavy MIS point after Enter:
    immediate check + three repeats with 5-second gaps.

    Returns:
      ("inpatient" | "without_referral" | "ready", location)
      or (None, None)
    """
    for round_no in range(0, 4):
        checkpoint()

        branch, loc = _find_visit_branch_once()
        if branch:
            log(
                f"[VISIT] Определена ветка после Enter: {branch} "
                f"(проверка {round_no + 1}/4)"
            )
            return branch, loc

        if round_no < 3:
            log(
                f"[VISIT] МИС ещё не показала стационар/направление/Повод. "
                f"Жду 5 секунд ({round_no + 1}/3)"
            )
            waited = 0.0
            while waited < 5.0:
                checkpoint()
                step = min(0.25, 5.0 - waited)
                time.sleep(step)
                waited += step

    log("[VISIT] После Enter не удалось определить ветку открытия приёма")
    return None, None


def handle_visit_opening_flow(win):
    """
    Unified opening of a NEW visit for FLUORO and XRAY.

    Correct order:
      visit_plus -> enter date [done by open_visit()]
      -> Enter
      -> detect one of:
           1) inpatient_question
           2) without_referral
           3) reason_field

    Returns:
      "inpatient" -> inpatient branch was processed
      "normal"    -> ordinary visit is ready
      False       -> failed/manual recovery declined
    """
    log("[VISIT] Подтверждаю стартовую дату через Enter")
    _win32_press_key("enter")
    checkpoint()

    branch, _ = _wait_visit_branch_after_enter()

    if branch is None:
        recovered = manual_recover_step(
            win,
            "Не удалось распознать результат открытия приёма.",
            "Подготовьте окно приёма вручную до поля «Повод обращения».",
        )
        return "normal" if recovered else False

    # --------------------------------------------------------------
    # Inpatient branch.
    # --------------------------------------------------------------
    if branch == "inpatient":
        log("[VISIT] Пациент в стационаре -> нажимаю «Да»")

        clicked = click_template_target(
            win,
            "inpatient_yes_button",
            offset=INPATIENT_YES_BUTTON_OFFSET,
            offset_key="inpatient_yes_button_offset",
            timeout=6,
            label="inpatient_yes_button",
            clicks=1,
        )
        if not clicked:
            recovered = manual_recover_step(
                win,
                "Не удалось нажать «Да» в окне стационарного пациента.",
                "Нажмите «Да» вручную и оставьте сценарий на следующем окне.",
            )
            if not recovered:
                return False

        checkpoint()
        time.sleep(0.5)

        # The second popup is optional. Give MIS time to show it.
        add_diag = _wait_template_with_delayed_retry(
            "add_diagnosis_question",
            first_checks=1,
            first_pause=0.2,
            first_probe_timeout=0.8,
            retry_delay=5.0,
            retry_rounds=1,
            second_checks=1,
            second_pause=0.2,
            second_probe_timeout=0.8,
            label="Добавить диагноз?",
        )

        if add_diag:
            log("[VISIT] Найдено «Добавить диагноз?» -> нажимаю «Нет»")
            clicked2 = click_template_target(
                win,
                "add_diagnosis_no_button",
                offset=ADD_DIAGNOSIS_NO_BUTTON_OFFSET,
                offset_key="add_diagnosis_no_button_offset",
                timeout=6,
                label="add_diagnosis_no_button",
                clicks=1,
            )
            if not clicked2:
                recovered = manual_recover_step(
                    win,
                    "Не удалось нажать «Нет» в окне добавления диагноза.",
                    "Нажмите «Нет» вручную.",
                )
                if not recovered:
                    return False
        else:
            log("[VISIT] Окно «Добавить диагноз?» не появилось — продолжаю")

        if not _wait_reason_field_after_visit(
            win,
            label="Стационар: ожидание поля «Повод обращения»",
        ):
            recovered = manual_recover_step(
                win,
                "После стационарных окон не найдено поле «Повод обращения».",
                "Подготовьте окно приёма вручную до поля «Повод обращения».",
            )
            if not recovered:
                return False

        log("[VISIT] Стационарный приём открыт")
        return "inpatient"

    # --------------------------------------------------------------
    # Ordinary referral popup branch.
    # --------------------------------------------------------------
    if branch == "without_referral":
        log("[VISIT] Найдено окно направления -> «Прием без направления»")

        # Use current image location/offset logic instead of raw pyautogui.
        clicked = click_template_target(
            win,
            "without_referral",
            offset=(0, 0),
            offset_key=None,
            timeout=4,
            label="without_referral",
            clicks=1,
        )
        if not clicked:
            recovered = manual_recover_step(
                win,
                "Не удалось выбрать «Прием без направления».",
                "Выберите вариант вручную.",
            )
            if not recovered:
                return False

        if not _wait_reason_field_after_visit(
            win,
            label="Обычный приём: ожидание поля «Повод обращения»",
        ):
            recovered = manual_recover_step(
                win,
                "После окна направления не найдено поле «Повод обращения».",
                "Подготовьте окно приёма вручную до поля «Повод обращения».",
            )
            if not recovered:
                return False

        log("[VISIT] Обычный приём открыт")
        return "normal"

    # reason_field was already visible immediately.
    log("[VISIT] Поле «Повод обращения» уже открыто")
    return "normal"


def handle_post_visit_plus_flow(win):
    """
    Backward-compatible wrapper for old call sites.
    New code should call handle_visit_opening_flow().
    """
    result = handle_visit_opening_flow(win)
    return bool(result)


def handle_inpatient_popup_if_present(win):
    """
    Legacy compatibility only.

    In v32 the inpatient question is intentionally NOT checked before Enter.
    The real handling is inside handle_visit_opening_flow().
    """
    log(
        "[VISIT] legacy handle_inpatient_popup_if_present вызван отдельно; "
        "статус стационара теперь определяется только после Enter"
    )
    return False


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
    """Выбор цели обращения только кликами по шаблонам-якорям."""
    log("Выбор 'Цель обращения' по шаблонам-якорям")

    clicked = click_template_target(
        win,
        "goal_dropdown",
        offset=GOAL_DROPDOWN_OFFSET,
        offset_key="goal_dropdown_offset",
        timeout=6,
        label="Цель обращения: раскрыть список",
    )
    if not clicked:
        return False

    time.sleep(0.5)
    checkpoint()

    log("Цель обращения: кликаю вариант 'Активное посещение' по goal_active_visit_item")
    clicked = click_template_target(
        win,
        "goal_active_visit_item",
        offset=GOAL_COMPLEX_ITEM_OFFSET,
        offset_key="goal_active_visit_item_offset",
        timeout=6,
        label="Цель обращения: Активное посещение",
    )
    if not clicked:
        return False

    time.sleep(0.5)
    checkpoint()
    log("Цель обращения выбрана")
    return True


def _wait_template_with_delayed_retry(
    template_key: str,
    *,
    first_checks=2,
    first_pause=0.8,
    first_probe_timeout=1.2,
    retry_delay=5.0,
    retry_rounds=3,
    second_checks=2,
    second_pause=0.8,
    second_probe_timeout=1.2,
    label=None,
):
    """
    Поиск для тяжёлых мест МИС:
    обычная попытка + retry_rounds повторных проверок через retry_delay секунд.
    """
    name = label or template_key

    for round_no in range(0, int(retry_rounds) + 1):
        if round_no:
            log(
                f"{name}: МИС ещё не готова. "
                f"Жду {retry_delay:.1f} сек перед повтором {round_no}/{retry_rounds}"
            )
            waited = 0.0
            while waited < retry_delay:
                checkpoint()
                step = min(0.25, retry_delay - waited)
                time.sleep(step)
                waited += step

        checks = first_checks if round_no == 0 else second_checks
        pause = first_pause if round_no == 0 else second_pause
        probe = first_probe_timeout if round_no == 0 else second_probe_timeout

        log(f"{name}: проверка {round_no + 1}/{int(retry_rounds) + 1}")
        loc = wait_for_template_strict(
            template_key,
            checks=max(1, int(checks)),
            pause=float(pause),
            probe_timeout=float(probe),
        )
        checkpoint()

        if loc:
            log(f"{name}: найден на проверке {round_no + 1}")
            return loc

    log(f"{name}: не найден после {int(retry_rounds) + 1} серий проверок")
    return None


def _wait_template_disappear_with_retries(
    template_key: str,
    *,
    retry_delay=5.0,
    retry_rounds=3,
    probe_timeout=1.0,
    label=None,
):
    """Ждёт исчезновения модального окна в тяжёлых местах МИС."""
    name = label or template_key

    for round_no in range(0, int(retry_rounds) + 1):
        loc = locate_image_on_screen(template_key, timeout=probe_timeout)
        checkpoint()
        if not loc:
            log(f"{name}: окно исчезло / следующий этап готов")
            return True

        if round_no >= int(retry_rounds):
            break

        log(
            f"{name}: окно всё ещё открыто. "
            f"Жду {retry_delay:.1f} сек, повтор {round_no + 1}/{retry_rounds}"
        )
        waited = 0.0
        while waited < retry_delay:
            checkpoint()
            step = min(0.25, retry_delay - waited)
            time.sleep(step)
            waited += step

    log(f"{name}: окно не исчезло после повторных проверок")
    return False


def open_work_service(win):
    log("Открытие выбора работы/услуги")

    # Нажимаем Work Plus без раннего expected_template.
    # Раньше adaptive_click_template_target слишком быстро проверял 0,00
    # и мог считать открытие неудачным ещё во время загрузки окна услуг.
    clicked = click_template_target(
        win,
        "work_plus",
        offset=WORK_PLUS_OFFSET,
        offset_key="work_plus_offset",
        timeout=6,
        label="work_plus",
        clicks=1,
    )

    if not clicked:
        log("Work Plus не удалось нажать по шаблону -> fallback coordinate")

        try:
            x, y = get_config_point(win, "work_plus_fallback_point")
        except Exception:
            x = y = None

        if x is None or y is None or not _win32_click(x, y):
            return manual_recover_step(
                win,
                "Не удалось автоматически открыть список услуг.",
                "Откройте список услуг вручную.",
            )

    checkpoint()

    # Дать интерфейсу начать открываться.
    time.sleep(max(0.5, SERVICE_WINDOW_WAIT))
    checkpoint()

    # Обязательное подтверждение открытия окна услуг:
    # первая попытка, затем ещё одна через 5 секунд.
    loc = _wait_template_with_delayed_retry(
        "service_price_zero",
        first_checks=2,
        first_pause=0.8,
        first_probe_timeout=SERVICE_LIST_PROBE_TIMEOUT,
        retry_delay=5.0,
        retry_rounds=3,
        second_checks=2,
        second_pause=1.0,
        second_probe_timeout=SERVICE_LIST_PROBE_TIMEOUT,
        label="Список услуг / 0,00",
    )

    if not loc:
        return manual_recover_step(
            win,
            "Список услуг не распознан даже после повторной проверки через 5 секунд.",
            "Откройте список услуг вручную и оставьте его открытым.",
        )

    log("Список услуг подтверждён")
    return True



def choose_first_service(win):
    """
    Выбор первой услуги по шаблону 0,00.

    Важно: координата клика вычисляется непосредственно перед кликом
    из АКТУАЛЬНОГО service_price_zero_offset из coordinates.json.
    Это устраняет рассинхрон между настройкой/пробным кликом и рабочим сценарием.
    """
    log("Ожидание списка услуг / 0,00")

    loc = _wait_template_with_delayed_retry(
        "service_price_zero",
        first_checks=2,
        first_pause=0.8,
        first_probe_timeout=SERVICE_LIST_PROBE_TIMEOUT,
        retry_delay=5.0,
        retry_rounds=3,
        second_checks=2,
        second_pause=0.8,
        second_probe_timeout=SERVICE_LIST_PROBE_TIMEOUT,
        label="Выбор услуги / 0,00",
    )
    if not loc:
        action = fail(win, "Не найден шаблон service_price_zero")
        if action != "continue":
            return False
        log("Продолжаю без автоматического выбора услуги")
        return True

    # Не используем загруженную при старте SERVICE_PRICE_ZERO_OFFSET:
    # перечитываем coordinates.json прямо сейчас.
    live_offset = _live_mis_coord(
        "service_price_zero_offset",
        list(SERVICE_PRICE_ZERO_OFFSET),
    )
    if not isinstance(live_offset, (list, tuple)) or len(live_offset) != 2:
        live_offset = SERVICE_PRICE_ZERO_OFFSET

    final_x = int(loc.x + int(live_offset[0]))
    final_y = int(loc.y + int(live_offset[1]))

    log(
        f"service_price_zero: template_center=({loc.x},{loc.y}) "
        f"LIVE offset=({int(live_offset[0])},{int(live_offset[1])}) "
        f"click=({final_x},{final_y})"
    )

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
        # Тот же Win32-механизм, что используется стабильными кликами бота.
        if not debug_click_point(final_x, final_y):
            return manual_recover_step(
                win,
                "Точка клика service_price_zero оказалась вне рабочего стола.",
                "Дважды нажмите нужную услугу вручную.",
            )
        if not _win32_click(final_x, final_y, clicks=2, interval=0.2):
            return manual_recover_step(
                win,
                "Не удалось физически нажать service_price_zero.",
                "Дважды нажмите нужную услугу вручную.",
            )
        checkpoint()

    time.sleep(0.6)
    checkpoint()
    log("Подтверждаю выбор услуги: F2")
    _win32_press_key("f2")
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
        return manual_recover_step(
            win,
            "Не удалось подтвердить открытие протокола.",
            "Откройте нужный протокол вручную.",
        )

    log("Протокол открыт")
    time.sleep(0.6)
    checkpoint()
    return True



def open_history_xray(win):
    """
    Открывает Историю болезни и выбирает именно
    «Рентгенографическое исследование».
    """
    log("Открытие меню История болезни")

    clicked = click_template_target(
        win,
        "history_menu",
        offset=HISTORY_MENU_OFFSET,
        offset_key="history_menu_offset",
        timeout=8,
        label="history_menu",
    )
    if not clicked:
        return False

    time.sleep(max(HISTORY_MENU_WAIT, 1.5))
    checkpoint()

    log("Выбор рентгенографического исследования")
    clicked = click_template_target(
        win,
        "history_xray_item",
        offset=HISTORY_XRAY_ITEM_OFFSET,
        offset_key="history_xray_item_offset",
        timeout=6,
        label="history_xray_item",
    )
    if not clicked:
        return False

    log("Проверяю открытие рентген-протокола по якорю 'Просмотр ИБ'")
    loc = wait_for_template_strict(
        "protocol_anchor",
        checks=WAIT_CHECKS,
        pause=WAIT_PAUSE,
        probe_timeout=WAIT_PROBE_TIMEOUT,
    )
    checkpoint()

    if not loc:
        return manual_recover_step(
            win,
            "Не удалось подтвердить открытие рентген-протокола.",
            "Откройте рентгенографический протокол вручную.",
        )

    log("Рентген-протокол открыт")
    time.sleep(0.6)
    checkpoint()
    return True


def choose_template(win, mode: str):
    row_key = validate_protocol_mode(mode)
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
        return manual_recover_step(
            win,
            f"Не найден нужный шаблон: {row_key}",
            "Выберите нужный шаблон вручную так, чтобы протокол уже был загружен.",
        )

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
    log("Ожидание окна подписи — тяжёлое место, до 3 повторов через 5 секунд")

    dialog = _wait_template_with_delayed_retry(
        "sign_password_dialog",
        first_checks=2,
        first_pause=0.8,
        first_probe_timeout=WAIT_PROBE_TIMEOUT,
        retry_delay=5.0,
        retry_rounds=3,
        second_checks=2,
        second_pause=0.8,
        second_probe_timeout=WAIT_PROBE_TIMEOUT,
        label="Окно подписи протокола",
    )
    checkpoint()
    if not dialog:
        log("Окно подписи протокола не появилось после повторных проверок")
        return False

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
        log("Поле пароля найдено")
    else:
        pyautogui.click(dialog.x, dialog.y)
        checkpoint()
        time.sleep(0.5)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.1)
    pyautogui.write(MIS_SETTINGS["sign_password"], interval=0.03)
    time.sleep(0.2)
    checkpoint()
    pyautogui.press("enter")
    checkpoint()

    # Не считаем Enter мгновенным успехом: ИК может подвиснуть на подписи.
    _wait_template_disappear_with_retries(
        "sign_password_dialog",
        retry_delay=5.0,
        retry_rounds=3,
        probe_timeout=1.0,
        label="Подпись протокола",
    )

    log("Подпись протокола обработана")
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
        return manual_recover_step(
            win,
            "Не удалось автоматически установить фокус в поле даты исследования.",
            f"Введите дату {dt} вручную, сохраните/подпишите протокол "
            "и оставьте МИС на следующем этапе.",
        )

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
    """
    СТАРЫЙ сценарий отмены диагноза.
    Оставлен для совместимости/отладки, но основной full_run флюорографии
    и рентген используют close_xray_diagnosis_314_304().
    """
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

def close_xray_diagnosis_314_304(win):
    """
    Закрытие активного диагноза для флюорографии/рентгена.

    V6:
    - если нужный элемент не найден, предлагается выполнить действие вручную
      и нажать "Продолжить";
    - после ручного действия сценарий идёт дальше, а не обрывается;
    - пауза после подтверждения подписи перед F2 = 10 секунд.
    """

    print("### XRAY/FLUORO DIAG V6 MANUAL CONTINUE ###")
    log("### XRAY/FLUORO DIAG V6 MANUAL CONTINUE ###")
    log("[DIAG V6] Начинаю закрытие диагноза")

    def manual_continue(message: str) -> bool:
        """
        Просит пользователя выполнить текущий шаг вручную.
        True  -> продолжить со следующего шага.
        False -> остановить сценарий.
        """
        log(f"[DIAG V6] Ручное вмешательство: {message}")

        ok = ui_manual_continue(
            f"{message}\n\n"
            f"Выполните действие вручную в МИС,\n"
            f"затем нажмите «Продолжить»."
        )

        if not ok:
            log("[DIAG V6] Пользователь отменил продолжение")
            return False

        log("[DIAG V6] Пользователь подтвердил ручное выполнение шага")
        checkpoint()
        return True

    # ---------------------------------------------------------
    # 1. diagnosis_drop
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 1: ищу diagnosis_drop")

    drop = locate_image_on_screen(
        "diagnosis_drop",
        timeout=4.0,
    )

    if drop:
        drop_x = drop.x + DIAGNOSIS_DROP_OFFSET[0]
        drop_y = drop.y + DIAGNOSIS_DROP_OFFSET[1]

        log(
            f"[DIAG V6] diagnosis_drop: "
            f"base=({drop.x},{drop.y}) final=({drop_x},{drop_y})"
        )

        if debug_click_point(drop_x, drop_y):
            pyautogui.click(drop_x, drop_y)
            log("[DIAG V6] Клик по diagnosis_drop выполнен")
            time.sleep(0.6)
            checkpoint()
        else:
            if not manual_continue(
                "Не удалось автоматически нажать кнопку открытия списка диагнозов."
            ):
                return False
    else:
        if not manual_continue(
            "Не найдено поле/кнопка открытия списка диагнозов.\n"
            "Откройте список диагнозов вручную."
        ):
            return False

    # ---------------------------------------------------------
    # 2. Активный диагноз
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 2: ищу активный диагноз diagnosis_code")

    diagnosis = locate_image_on_screen(
        "diagnosis_code",
        timeout=4.0,
    )

    if diagnosis:
        diagnosis_x = diagnosis.x + DIAGNOSIS_CODE_OFFSET[0]
        diagnosis_y = diagnosis.y + DIAGNOSIS_CODE_OFFSET[1]

        log(
            f"[DIAG V6] diagnosis_code: "
            f"base=({diagnosis.x},{diagnosis.y}) "
            f"final=({diagnosis_x},{diagnosis_y})"
        )

        if debug_click_point(diagnosis_x, diagnosis_y):
            pyautogui.click(diagnosis_x, diagnosis_y)
            log("[DIAG V6] Клик по активному диагнозу выполнен")
            time.sleep(0.7)
            checkpoint()
        else:
            if not manual_continue(
                "Не удалось автоматически нажать на активный диагноз.\n"
                "Нажмите на активный диагноз вручную."
            ):
                return False
    else:
        if not manual_continue(
            "Активный диагноз не найден автоматически.\n"
            "Нажмите на нужный активный диагноз вручную."
        ):
            return False

    # ---------------------------------------------------------
    # 3. Пункт "Закрыть"
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 3: ищу пункт 'Закрыть'")

    close_item = locate_image_on_screen(
        "diagnosis_close_item",
        timeout=4.0,
    )

    if close_item:
        close_x = close_item.x + DIAGNOSIS_CLOSE_ITEM_OFFSET[0]
        close_y = close_item.y + DIAGNOSIS_CLOSE_ITEM_OFFSET[1]

        log(
            f"[DIAG V6] diagnosis_close_item: "
            f"base=({close_item.x},{close_item.y}) "
            f"final=({close_x},{close_y})"
        )

        if debug_click_point(close_x, close_y):
            pyautogui.click(close_x, close_y)
            log("[DIAG V6] Клик по 'Закрыть' выполнен")
            time.sleep(0.9)
            checkpoint()
        else:
            if not manual_continue(
                "Не удалось автоматически нажать пункт «Закрыть».\n"
                "Нажмите «Закрыть» вручную."
            ):
                return False
    else:
        if not manual_continue(
            "Пункт «Закрыть» не найден автоматически.\n"
            "Нажмите «Закрыть» вручную."
        ):
            return False

    # ---------------------------------------------------------
    # 4. Окно закрытия случая / коды 314 и 304
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 4: ищу окно закрытия случая")

    close_anchor = locate_image_on_screen(
        "case_close_current_diagnosis",
        timeout=5.0,
    )

    manual_codes_done = False

    if not close_anchor:
        # Если окно не смогли распознать, пользователь может заполнить
        # оба кода вручную и оставить окно открытым на следующем шаге.
        if not manual_continue(
            "Окно «Закрытие случая» не распознано автоматически.\n"
            "Вручную заполните:\n"
            "• Результат случая — 314 + Enter\n"
            "• Исход заболевания — 304 + Enter\n"
            "После этого оставьте окно открытым."
        ):
            return False

        manual_codes_done = True
    else:
        log(
            f"[DIAG V6] Окно закрытия случая подтверждено: "
            f"anchor=({close_anchor.x},{close_anchor.y})"
        )

    def fill_case_code(code: str, dx: int, dy: int, label: str):
        field_x = int(close_anchor.x + dx)
        field_y = int(close_anchor.y + dy)

        log(
            f"[DIAG V6] {label}: "
            f"поле=({field_x},{field_y}), код={code}"
        )

        if not debug_click_point(field_x, field_y):
            return manual_continue(
                f"Не удалось автоматически попасть в поле «{label}».\n"
                f"Введите вручную код {code} и нажмите Enter."
            )

        pyautogui.click(field_x, field_y)
        time.sleep(0.35)
        checkpoint()

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.12)
        pyautogui.press("backspace")
        time.sleep(0.12)

        pyautogui.write(code, interval=0.18)
        log(f"[DIAG V6] {label}: код {code} набран")
        time.sleep(0.45)

        pyautogui.press("enter")
        log(f"[DIAG V6] {label}: Enter")
        time.sleep(0.9)
        checkpoint()

        return True

    if not manual_codes_done:
        if not fill_case_code(
            code="314",
            dx=-82,
            dy=-72,
            label="Результат случая",
        ):
            return False

        if not fill_case_code(
            code="304",
            dx=-82,
            dy=-44,
            label="Исход заболевания",
        ):
            return False

    # ---------------------------------------------------------
    # 5. Закрыть с текущим диагнозом
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 5: Закрыть с текущим диагнозом")

    close_anchor = locate_image_on_screen(
        "case_close_current_diagnosis",
        timeout=5.0,
    )

    if close_anchor:
        close_btn_x = close_anchor.x + CASE_CLOSE_CURRENT_DIAGNOSIS_OFFSET[0]
        close_btn_y = close_anchor.y + CASE_CLOSE_CURRENT_DIAGNOSIS_OFFSET[1]

        if debug_click_point(close_btn_x, close_btn_y):
            pyautogui.click(close_btn_x, close_btn_y)
            log("[DIAG V6] Нажато 'Закрыть с текущим диагнозом'")
            time.sleep(0.9)
            checkpoint()
        else:
            if not manual_continue(
                "Не удалось автоматически нажать «Закрыть с текущим диагнозом».\n"
                "Нажмите эту кнопку вручную."
            ):
                return False
    else:
        if not manual_continue(
            "Кнопка «Закрыть с текущим диагнозом» не найдена.\n"
            "Нажмите её вручную."
        ):
            return False

    # ---------------------------------------------------------
    # 6. Да, с подписью
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 6: ищу 'Да, с подписью'")

    signed = locate_image_on_screen(
        "epicrisis_yes_signed",
        timeout=6.0,
    )

    if signed:
        signed_x = signed.x + EPICRISIS_YES_SIGNED_OFFSET[0]
        signed_y = signed.y + EPICRISIS_YES_SIGNED_OFFSET[1]

        if debug_click_point(signed_x, signed_y):
            pyautogui.click(signed_x, signed_y)
            log("[DIAG V6] Нажато 'Да, с подписью'")
            time.sleep(1.0)
            checkpoint()
        else:
            if not manual_continue(
                "Не удалось автоматически нажать «Да, с подписью».\n"
                "Нажмите эту кнопку вручную."
            ):
                return False
    else:
        if not manual_continue(
            "Кнопка «Да, с подписью» не найдена автоматически.\n"
            "Нажмите «Да, с подписью» вручную."
        ):
            return False

    # ---------------------------------------------------------
    # 7. Окно подписи
    # ---------------------------------------------------------
    # После клика "Да, с подписью" окно подписи появляется не мгновенно.
    # Если отправить Space сразу, клавиша может уйти в предыдущее окно.
    log("[DIAG V6] Шаг 7: жду окно подписи эпикриза — до 3 повторов через 5 секунд")
    epic_sign_dialog = _wait_template_with_delayed_retry(
        "sign_password_dialog",
        first_checks=2,
        first_pause=0.8,
        first_probe_timeout=WAIT_PROBE_TIMEOUT,
        retry_delay=5.0,
        retry_rounds=3,
        second_checks=2,
        second_pause=0.8,
        second_probe_timeout=WAIT_PROBE_TIMEOUT,
        label="Окно подписи эпикриза",
    )

    if not epic_sign_dialog:
        log("[DIAG V6] Шаблон окна подписи эпикриза не найден; оставляю старый fallback Space")
        time.sleep(1.0)
        checkpoint()

    log("[DIAG V6] Подтверждение подписи эпикриза -> Space")
    pyautogui.press("space")
    checkpoint()

    if epic_sign_dialog:
        _wait_template_disappear_with_retries(
            "sign_password_dialog",
            retry_delay=5.0,
            retry_rounds=3,
            probe_timeout=1.0,
            label="Подпись эпикриза",
        )
    else:
        # Если конкретный шаблон диалога не распознан, всё равно даём ИК
        # три пятисекундных интервала на завершение тяжёлой операции.
        for retry_no in range(1, 4):
            log(f"[DIAG V6] Эпикриз: ожидание ИК 5 сек ({retry_no}/3)")
            time.sleep(5.0)
            checkpoint()

    # RDP/МИС иногда теряет клавиатурный фокус после модального окна подписи.
    # Перед финальной клавиатурной цепочкой явно возвращаем фокус окну МИС.
    log("[DIAG V6] Возвращаю фокус окну МИС перед F2")
    try:
        win.activate()
        time.sleep(0.8)
        checkpoint()
    except Exception as e:
        log(f"[DIAG V6] Не удалось явно активировать окно МИС: {e}")

    # ---------------------------------------------------------
    # 8. Финальная цепочка
    # ---------------------------------------------------------
    log("[DIAG V6] Шаг 8: отправляю F2")
    pyautogui.press("f2")
    log("[DIAG V6] F2 отправлен")
    time.sleep(1.2)
    checkpoint()

    log("[DIAG V6] Шаг 8: отправляю первый Space")
    pyautogui.press("space")
    log("[DIAG V6] Первый Space отправлен")
    time.sleep(1.0)
    checkpoint()

    log("[DIAG V6] Шаг 8: отправляю второй Space")
    pyautogui.press("space")
    log("[DIAG V6] Второй Space отправлен")
    time.sleep(1.0)
    checkpoint()

    log("[DIAG V6] Диагноз закрыт успешно")
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
        return manual_recover_step(
            win,
            "МИС не вернулась на экран поиска пациента автоматически.",
            "Перейдите на экран поиска пациента вручную.",
        )

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
        return manual_recover_step(
            win,
            "Не удалось распознать открытую карточку пациента.",
            "Откройте карточку/окно приема вручную.",
        )

    log("Открытая карточка пациента подтверждена")
    return True


def continue_from_open_patient_card(task, step_mode=False, stop_stage: str | None = None):
    validate_protocol_mode(task.mode)

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

    log("[FLUORO] Закрытие диагноза: 314 / 304")
    ok = close_xray_diagnosis_314_304(win)
    checkpoint()
    if not ok:
        return

    if stop_at_stage_open_card(
        win,
        "after_cancel_diagnosis",
        stop_stage,
        "После закрытия диагноза 314/304",
    ):
        return

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
        validate_protocol_mode(mode)

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

        visit_flow = handle_visit_opening_flow(win)
        checkpoint()
        if visit_flow is False:
            return

        is_inpatient_flow = (visit_flow == "inpatient")
        if is_inpatient_flow:
            log("[FLUORO] Приём открыт по стационарной ветке")
        else:
            log("[FLUORO] Приём открыт по обычной ветке")

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
        if is_inpatient_flow:
            log("[FLUORO] Стационарный пациент: закрытие диагноза 314/304 пропущено")
        else:
            log("[FLUORO] Закрытие диагноза: 314 / 304")
            ok = close_xray_diagnosis_314_304(win)
            checkpoint()
            if not ok:
                return

        if stop_at_stage(
            win,
            "after_cancel_diagnosis",
            stop_stage,
            "После закрытия диагноза 314/304",
        ):
            return

        # Финальная F2 -> Space -> Space уже выполняется
        # внутри close_xray_diagnosis_314_304().
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