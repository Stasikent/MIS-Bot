import time
import subprocess
from datetime import datetime
from pathlib import Path

import mss
import pyautogui
import pygetwindow as gw
import pytesseract
from PIL import Image

# =========================
# CONFIG
# =========================

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

RDP_TITLE_PART = "Инфоклиника"
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = BASE_DIR / "templates"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

pyautogui.PAUSE = 0.2
pyautogui.FAILSAFE = True

# Поиск пациента
SEARCH_ANCHOR_X_OFFSET = 210

# Даты рождения в списке найденных пациентов
DOB_REGION = (618, 272, 135, 34)
DOB_CLICK_POINT = (670, 287)
ROW_HEIGHT = 28
MAX_PATIENT_ROWS = 6

# Координаты
WORK_PLUS_FALLBACK_POINT = (935, 395)

# Тайминги
SERVICE_WINDOW_WAIT = 1.5
HISTORY_MENU_WAIT = 0.8
WITHOUT_REFERRAL_TIMEOUT = 2.5
TEMPLATE_LOAD_WAIT = 2.5

STOP_ON_CRITICAL = True

# =========================
# LOGGING / DEBUG
# =========================

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
    if STOP_ON_CRITICAL:
        raise RuntimeError(message)

# =========================
# WINDOW / SCREEN HELPERS
# =========================

def find_rdp_window():
    wins = gw.getWindowsWithTitle(RDP_TITLE_PART)
    if not wins:
        raise RuntimeError(f"Окно RDP не найдено: {RDP_TITLE_PART}")
    win = wins[0]
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.8)
    return win

def abs_point(win, rel_xy):
    return win.left + rel_xy[0], win.top + rel_xy[1]

def abs_region(win, rel_region):
    x, y, w, h = rel_region
    return (win.left + x, win.top + y, w, h)

def click_rel(win, rel_xy, clicks=1, interval=0.15, button="left"):
    x, y = abs_point(win, rel_xy)
    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)

def screenshot_region(win, rel_region):
    x, y, w, h = abs_region(win, rel_region)
    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        return Image.frombytes("RGB", shot.size, shot.rgb)

# =========================
# OCR / IMAGE HELPERS
# =========================

def ocr_date_image(img: Image.Image):
    # Увеличиваем контраст и приводим к черно-белому для OCR даты
    gray = img.convert("L")
    bw = gray.point(lambda x: 0 if x < 170 else 255, "1")

    text = pytesseract.image_to_string(
        bw,
        lang="eng",
        config="--psm 7 -c tessedit_char_whitelist=0123456789."
    )
    return " ".join(text.replace("\n", " ").split())

def normalize_date_text(s: str):
    return s.replace(" ", "").replace(",", ".").replace("-", ".")

def locate_image_on_screen(name: str, confidence=0.82, timeout=10.0):
    path = TEMPLATES / name
    if not path.exists():
        raise FileNotFoundError(f"Шаблон не найден на диске: {path}")

    end = time.time() + timeout
    while time.time() < end:
        try:
            loc = pyautogui.locateCenterOnScreen(str(path), confidence=confidence)
            if loc:
                return loc
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.25)
    return None

def click_image(win, name: str, confidence=0.82, timeout=10.0, clicks=1, offset=(0, 0)):
    loc = locate_image_on_screen(name, confidence=confidence, timeout=timeout)
    if not loc:
        fail(win, f"Не найден шаблон на экране: {name}")
        return False

    x = loc.x + offset[0]
    y = loc.y + offset[1]
    pyautogui.click(x, y, clicks=clicks, interval=0.2)
    log(f"Клик по шаблону: {name} с offset={offset}")
    return True

def double_click_image(win, name: str, confidence=0.82, timeout=10.0, offset=(0, 0)):
    return click_image(win, name, confidence=confidence, timeout=timeout, clicks=2, offset=offset)

def click_template_with_offset(win, template_name, offset=(0, 0), confidence=0.82, timeout=8):
    loc = locate_image_on_screen(template_name, confidence=confidence, timeout=timeout)
    if not loc:
        fail(win, f"Не найден шаблон: {template_name}")
        return None

    x = loc.x + offset[0]
    y = loc.y + offset[1]
    pyautogui.click(x, y)
    log(f"Клик по {template_name} с offset={offset}")
    time.sleep(0.3)
    return (x, y)

def wait_for_template_3_checks(name: str, confidence=0.80, checks=3, pause=1.0):
    """
    Проверяет наличие шаблона до checks раз.
    Как только шаблон найден — сразу True.
    Если после всех попыток не найден — False.
    """
    for attempt in range(1, checks + 1):
        loc = locate_image_on_screen(name, confidence=confidence, timeout=0.3)
        if loc:
            log(f"{name} найден на попытке {attempt}/{checks}")
            return True

        log(f"{name} не найден на попытке {attempt}/{checks}")
        if attempt < checks:
            time.sleep(pause)

    return False

def ask_user_checkpoint(label: str):
    print()
    ans = input(f"[CHECKPOINT] {label}. Продолжить? (y/n): ").strip().lower()
    if ans not in ("y", "yes", "д", "да"):
        raise RuntimeError(f"Остановлено пользователем на этапе: {label}")

def press_seq(*keys, pause=0.35):
    for key in keys:
        pyautogui.press(key)
        log(f"Клавиша: {key}")
        time.sleep(pause)

def current_date_str():
    return datetime.now().strftime("%d.%m.%Y")

# =========================
# CLIPBOARD INPUT
# =========================

def set_clipboard_text(text: str):
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Set-Clipboard -Value @'\n{text}\n'@"
        ],
        check=True,
        capture_output=True,
        text=True
    )

def paste_text_shift_insert(text: str):
    set_clipboard_text(text)
    time.sleep(0.2)
    pyautogui.hotkey("shift", "insert")
    time.sleep(0.5)

# =========================
# BUSINESS FLOW
# =========================

def search_patient(win, fio: str):
    log("Поиск якоря поиска пациента")
    anchor = locate_image_on_screen("search_anchor.png", confidence=0.80, timeout=8)
    if not anchor:
        fail(win, "Не найден search_anchor.png")
        return

    field_x = anchor.x - SEARCH_ANCHOR_X_OFFSET
    field_y = anchor.y

    log(f"Клик в поле поиска: ({field_x}, {field_y})")
    pyautogui.click(field_x, field_y)
    time.sleep(0.2)
    pyautogui.click(field_x, field_y)
    time.sleep(0.2)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    pyautogui.press("backspace")
    time.sleep(0.2)

    log("Вставляю ФИО через Shift+Insert")
    paste_text_shift_insert(fio)
    time.sleep(1.5)

    log(f"ФИО вставлено: {fio}")

def find_patient_by_birth_date_and_click(win, birth_date: str, max_rows=MAX_PATIENT_ROWS):
    log(f"Поиск пациента по дате рождения: {birth_date}")
    target = normalize_date_text(birth_date)

    # Даем поиску время стабильно отрисоваться
    time.sleep(1.0)

    for i in range(max_rows):
        region = (
            DOB_REGION[0],
            DOB_REGION[1] + i * ROW_HEIGHT,
            DOB_REGION[2],
            DOB_REGION[3],
        )

        img = screenshot_region(win, region)
        text = normalize_date_text(ocr_date_image(img))
        log(f"Строка {i + 1}: OCR даты = {repr(text)} | region={region}")

        if target in text:
            click_point = (
                DOB_CLICK_POINT[0],
                DOB_CLICK_POINT[1] + i * ROW_HEIGHT,
            )
            log(f"Найден нужный пациент в строке {i + 1}, кликаю по дате: {click_point}")
            click_rel(win, click_point, clicks=1, button="left")
            time.sleep(0.4)
            return True

    # сохраним проблемную область первой строки для разбора
    save_region_screenshot(win, DOB_REGION, "dob_debug")
    fail(win, f"Пациент с датой рождения {birth_date} не найден", rel_region=DOB_REGION)

def open_visit(win):
    log("Открытие нового приема через плюс")
    click_image(
        win,
        "visit_plus.png",
        confidence=0.80,
        timeout=8,
        offset=(-18, 0)
    )
    time.sleep(0.8)

def handle_post_visit_plus_flow(win):
    log("После нажатия плюса: подтверждаю дату через Enter")
    pyautogui.press("enter")
    time.sleep(1.0)

    log("Проверяю, появилось ли окно направления")
    loc = locate_image_on_screen("without_referral.png", confidence=0.80, timeout=WITHOUT_REFERRAL_TIMEOUT)
    if loc:
        log("Найдено окно направления -> выбираю 'Прием без направления'")
        pyautogui.click(loc.x, loc.y)
        time.sleep(1.0)
        return "with_referral_popup"

    log("Окно направления не появилось")
    return "no_referral_popup"

def fill_reason_code(win):
    log("Выбор 'Повод обращения' через ввод кода 8")

    # Ищем надпись/якорь и кликаем правее нее, в само поле
    click_image(
        win,
        "reason_field.png",
        confidence=0.80,
        timeout=6,
        offset=(95, 0)   # подбирается
    )
    time.sleep(0.2)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.1)

    pyautogui.write("8", interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.5)

    log("Повод обращения выбран")

def fill_goal_complex(win):
    log("Выбор 'Цель обращения'")
    click_template_with_offset(win, "goal_dropdown.png", offset=(0, 0), confidence=0.80, timeout=6)

    time.sleep(0.3)
    pyautogui.press("pgdn")
    time.sleep(0.2)
    pyautogui.press("up")
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.5)

    log("Цель обращения выбрана")

def open_work_service(win):
    log("Открытие выбора работы/услуги")
    loc = locate_image_on_screen("work_plus.png", confidence=0.80, timeout=6)
    if loc:
        pyautogui.click(loc.x, loc.y)
        time.sleep(SERVICE_WINDOW_WAIT)
        return

    log("Шаблон work_plus не найден, пробую запасную координату")
    x = win.left + WORK_PLUS_FALLBACK_POINT[0]
    y = win.top + WORK_PLUS_FALLBACK_POINT[1]
    pyautogui.click(x, y)
    time.sleep(SERVICE_WINDOW_WAIT)

def choose_first_service(win):
    log("Выбор услуги по шаблону 0,00 РУБ двойным кликом")
    double_click_image(win, "service_price_zero.png", confidence=0.80, timeout=8)
    time.sleep(0.6)

    log("Подтверждаю выбор услуги: F2")
    pyautogui.press("f2")
    time.sleep(1.0)

def open_history_fluoro(win):
    log("Открытие меню История болезни")
    click_image(win, "History_menu.png", confidence=0.78, timeout=8)
    time.sleep(HISTORY_MENU_WAIT)

    log("Выбор флюорографического исследования")
    click_image(win, "history_fluoro_item.png", confidence=0.78, timeout=6)

    log("Проверяю открытие протокола по якорю 'Просмотр ИБ'")
    ok = wait_for_template_3_checks(
        "protocol_anchor.png",
        confidence=0.80,
        checks=3,
        pause=1.0
    )

    if not ok:
        fail(win, "Протокол не открылся: якорь 'Просмотр ИБ' не найден после 3 проверок")
        return

    log("Протокол открыт")
    time.sleep(0.6)

def choose_template(win):
    log("Открываю меню 'Шаблоны'")
    click_image(win, "templates_anchor.png", confidence=0.80, timeout=8)
    time.sleep(0.8)

    log("Жду появления пункта 'Выбрать'")
    ok = wait_for_template_3_checks(
        "template_use.png",
        confidence=0.78,
        checks=3,
        pause=0.8
    )
    if not ok:
        fail(win, "После нажатия 'Шаблоны' пункт template_use.png не появился")
        return

    log("Нажимаю 'Выбрать'")
    click_image(win, "template_use.png", confidence=0.78, timeout=5)
    time.sleep(0.8)

    log("Жду появления строки шаблона")
    ok = wait_for_template_3_checks(
        "template_row.png",
        confidence=0.78,
        checks=3,
        pause=1.0
    )
    if not ok:
        fail(win, "После нажатия 'Выбрать' строка template_row.png не появилась")
        return

    log("Выбор шаблона двойным кликом")
    double_click_image(win, "template_row.png", confidence=0.78, timeout=6)
    time.sleep(0.5)

    log("После двойного клика: Space -> пауза -> Space")
    pyautogui.press("space")
    time.sleep(0.8)
    pyautogui.press("space")
    time.sleep(TEMPLATE_LOAD_WAIT)

def handle_sign_password_if_needed(win):
    log("Пауза перед проверкой окна подписи")
    time.sleep(1.0)  # ← можно 0.8–1.5 подобрать

    log("Проверяю, появилось ли окно подписи документа")

    loc = locate_image_on_screen("sign_password_dialog.png", confidence=0.80, timeout=1.5)
    if not loc:
        log("Окно подписи не появилось")
        return False

    log("Окно подписи найдено")

    field = locate_image_on_screen("sign_password_field.png", confidence=0.80, timeout=3.0)
    if not field:
        fail(win, "Окно подписи найдено, но поле пароля не найдено")
        return False

    pyautogui.click(field.x, field.y)
    time.sleep(0.2)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.1)

    pyautogui.write("12345678", interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.8)

    log("Пароль подписи введен")
    return True

def fill_template_date_and_save(win):
    dt = current_date_str()
    log(f"Ввод текущей даты: {dt}")
    pyautogui.write(dt, interval=0.02)
    time.sleep(0.4)

    log("Цепочка после даты: F2 -> Tab -> Space")
    pyautogui.press("f2")
    time.sleep(0.8)
    pyautogui.press("tab")
    time.sleep(0.5)
    pyautogui.press("space")
    time.sleep(0.8)

    # ВОТ ТУТ вызываем
    handle_sign_password_if_needed(win)


def cancel_diagnosis(win):
    log("Открытие раздела диагноза")
    click_image(win, "diagnosis_drop.png", confidence=0.80, timeout=8)
    time.sleep(0.5)

    log("Жду появления diagnosis_code")
    ok = wait_for_template_3_checks(
        "diagnosis_code.png",
        confidence=0.80,
        checks=3,
        pause=0.6
    )
    if not ok:
        fail(win, "После клика по diagnosis_drop не появился diagnosis_code.png")
        return

    log("Кликаю по diagnosis_code")
    click_image(win, "diagnosis_code.png", confidence=0.80, timeout=4)
    time.sleep(0.5)

    log("Жду появления пункта Отменить")
    ok = wait_for_template_3_checks(
        "diagnosis_cancel_item.png",
        confidence=0.80,
        checks=3,
        pause=0.6
    )
    if not ok:
        fail(win, "После клика по diagnosis_code не появился diagnosis_cancel_item.png")
        return

    log("Выбор пункта Отменить")
    click_image(win, "diagnosis_cancel_item.png", confidence=0.80, timeout=4, offset=(0, 12))
    time.sleep(0.8)

def final_save_chain():
    log("Финальная цепочка: F2 -> Space -> Space")
    press_seq("f2", pause=0.8)
    press_seq("space", pause=0.8)
    press_seq("space", pause=0.8)

def full_run(fio: str, birth_date: str, step_mode=True):
    win = find_rdp_window()
    log("Окно RDP активировано")

    search_patient(win, fio)
    if step_mode:
        ask_user_checkpoint("После ввода ФИО и ожидания поиска")

    find_patient_by_birth_date_and_click(win, birth_date)
    if step_mode:
        ask_user_checkpoint("После поиска нужной даты рождения и клика по дате")

    open_visit(win)
    handle_post_visit_plus_flow(win)
    if step_mode:
        ask_user_checkpoint("После открытия приема")

    fill_reason_code(win)
    fill_goal_complex(win)
    if step_mode:
        ask_user_checkpoint("После заполнения повода и цели")

    open_work_service(win)
    choose_first_service(win)
    if step_mode:
        ask_user_checkpoint("После выбора услуги")

    open_history_fluoro(win)
    choose_template(win)
    fill_template_date_and_save(win)
    if step_mode:
        ask_user_checkpoint("После шаблона и ввода даты")

    cancel_diagnosis(win)
    final_save_chain()

    log("Сценарий завершен успешно")
    save_window_screenshot(win, "success_window")

if __name__ == "__main__":
    fio = "ТАРАКАНОВ СТАНИСЛАВ РОМАНОВИЧ"
    birth_date = "21.02.1996"

    try:
        full_run(fio, birth_date, step_mode=True)
    except Exception as e:
        print("КРИТИЧЕСКАЯ ОШИБКА:", e)