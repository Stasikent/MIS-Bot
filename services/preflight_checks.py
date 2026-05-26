from dataclasses import dataclass
from typing import Callable, Optional

from project.bot_mode1_current import find_rdp_window, locate_image_on_screen, log as mis_log
from project.browser_ris_flow import locate_image_on_screen as ris_locate_image_on_screen


@dataclass
class CheckItemResult:
    name: str
    ok: bool
    details: str = ""


@dataclass
class PreflightResult:
    title: str
    ok: bool
    items: list[CheckItemResult]


def _safe_check(name: str, fn: Callable[[], tuple[bool, str]]) -> CheckItemResult:
    try:
        ok, details = fn()
        return CheckItemResult(name=name, ok=ok, details=details)
    except Exception as e:
        return CheckItemResult(name=name, ok=False, details=str(e))


def _window_check() -> tuple[bool, str]:
    win = find_rdp_window()
    return True, f"Окно найдено: {win.title}"


def _mis_template_check(template_key: str, timeout: float = 3.0) -> tuple[bool, str]:
    loc = locate_image_on_screen(template_key, timeout=timeout)
    if not loc:
        return False, f"Шаблон '{template_key}' не найден"
    return True, f"Найден: ({loc.x}, {loc.y})"


def _ris_template_check(template_key: str, timeout: float = 3.0) -> tuple[bool, str]:
    loc = ris_locate_image_on_screen(template_key, timeout=timeout)
    if not loc:
        return False, f"Шаблон '{template_key}' не найден"
    return True, f"Найден: ({loc.x}, {loc.y})"


def run_mis_preflight() -> PreflightResult:
    items = [
        _safe_check("Окно RDP", _window_check),
        _safe_check("Якорь поиска пациента", lambda: _mis_template_check("search_anchor")),
        _safe_check("Кнопка '+' приёма", lambda: _mis_template_check("visit_plus")),
    ]
    ok = all(item.ok for item in items)
    return PreflightResult(title="Проверка МИС", ok=ok, items=items)


def run_ris_preflight() -> PreflightResult:
    items = [
        _safe_check("Кнопка поиска РИС", lambda: _ris_template_check("ris_search_button_active")),
    ]
    ok = all(item.ok for item in items)
    return PreflightResult(title="Проверка РИС", ok=ok, items=items)


def run_open_card_preflight() -> PreflightResult:
    items = [
        _safe_check("Окно RDP", _window_check),
        _safe_check("Поле 'Повод обращения'", lambda: _mis_template_check("reason_field")),
        _safe_check("Кнопка 'Шаблоны'", lambda: _mis_template_check("templates_anchor")),
        _safe_check("Меню истории", lambda: _mis_template_check("history_menu")),
    ]
    ok = all(item.ok for item in items)
    return PreflightResult(title="Проверка открытой карточки", ok=ok, items=items)