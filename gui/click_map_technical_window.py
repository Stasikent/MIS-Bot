import json
import time
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui
from PIL import Image, ImageGrab, ImageTk

from config.loader import CONFIG_DIR
from services.runtime_paths import TEMPLATES_DIR
from gui.mis_window_overlay import pick_point_in_mis, pick_rect_in_mis
from project.bot_mode1_current import (
    find_mis_window,
    locate_image_on_screen,
    debug_click_point,
)

COORDS_PATH = CONFIG_DIR / "coordinates.json"
TEMPLATES_PATH = CONFIG_DIR / "templates.json"
PROTOCOLS_PATH = CONFIG_DIR / "protocols.json"

# Friendly names for the most important runtime objects.
FRIENDLY = {
    "search_anchor": "Поиск пациента / якорь",
    "visit_plus": "Открытие приёма",
    "without_referral": "Без направления",
    "reason_field": "Повод обращения",
    "goal_dropdown": "Цель обращения",
    "goal_active_visit_item": "Цель обращения → Активное посещение",
    "work_plus": "Добавление услуги",
    "service_price_zero": "Строка услуги 0,00",
    "history_menu": "История болезни",
    "history_fluoro_item": "Флюорографическое исследование",
    "history_xray_item": "Рентгенографическое исследование",
    "protocol_anchor": "Протокол / якорь",
    "templates_anchor": "Кнопка «Шаблоны»",
    "template_use": "Выбрать шаблон",
    "sign_password_dialog": "Окно пароля подписи",
    "sign_password_field": "Поле пароля подписи",
    "diagnosis_drop": "Меню диагноза",
    "diagnosis_code": "Строка диагноза",
    "paste_context_item": "Контекстное меню «Вставить»",
    "study_date_label": "Дата исследования",
    "diagnosis_cancel_item": "Отмена диагноза",
    "diagnosis_close_item": "Закрытие диагноза",
    "xray_service_item": "Рентген — строка услуги",
    "template_owner_dropdown": "Шаблоны — владелец",
    "template_owner_only_mine": "Шаблоны — только мои",
    "template_diagnosis_clear_cross": "Очистка диагноза шаблона",
    "xray_field_study_number": "Рентген — номер исследования",
    "xray_field_description": "Рентген — описание",
    "xray_field_conclusion": "Рентген — заключение",
    "close_case_title": "Закрытие случая",
    "epicrisis_question": "Вопрос об эпикризе",
    "epicrisis_no": "Эпикриз — Нет",
    "epicrisis_yes_signed": "Эпикриз — Да / подписан",
    "close_with_current_diagnosis": "Закрыть с текущим диагнозом",
    "diagnosis_active_z0": "Активный диагноз Z0",
    "inpatient_question": "Вопрос стационара",
    "inpatient_yes_button": "Стационар — Да",
    "add_diagnosis_question": "Вопрос добавления диагноза",
    "add_diagnosis_no_button": "Добавить диагноз — Нет",
    "case_result_label": "Исход случая",
    "case_outcome_label": "Результат случая",
    "case_close_current_diagnosis": "Закрыть текущий диагноз",
}

# Some templates have a click offset with a non-obvious key.
SPECIAL_OFFSET_KEYS = {
    "search_anchor": "search_anchor_offset",
    "visit_plus": "visit_plus_offset",
    "reason_field": "reason_field_offset",
    "goal_dropdown": "goal_dropdown_offset",
    "goal_active_visit_item": "goal_active_visit_item_offset",
    "work_plus": "work_plus_offset",
    "service_price_zero": "service_price_zero_offset",
    "history_menu": "history_menu_offset",
    "history_fluoro_item": "history_fluoro_item_offset",
    "history_xray_item": "history_xray_item_offset",
    "templates_anchor": "templates_anchor_offset",
    "template_use": "template_use_offset",
    "diagnosis_drop": "diagnosis_drop_offset",
    "diagnosis_code": "diagnosis_code_offset",
    "study_date_label": "study_date_label_offset",
    "diagnosis_cancel_item": "diagnosis_cancel_item_offset",
    "diagnosis_close_item": "diagnosis_close_item_offset",
    "xray_service_item": "xray_service_item_offset",
    "template_owner_dropdown": "template_owner_dropdown_offset",
    "template_owner_only_mine": "template_owner_only_mine_offset",
    "template_diagnosis_clear_cross": "template_diagnosis_clear_cross_offset",
    "xray_field_study_number": "xray_field_study_number_offset",
    "xray_field_description": "xray_field_description_offset",
    "xray_field_conclusion": "xray_field_conclusion_offset",
    "inpatient_yes_button": "inpatient_yes_button_offset",
    "add_diagnosis_no_button": "add_diagnosis_no_button_offset",
    "case_result_label": "case_result_label_offset",
    "case_outcome_label": "case_outcome_label_offset",
    "case_close_current_diagnosis": "case_close_current_diagnosis_offset",
    "epicrisis_yes_signed": "epicrisis_yes_signed_offset",
}


# Working targets that must be configurable even if this workstation has not
# yet created their PNG entry in templates.json.
#
# This prevents the recurring problem where runtime starts using a new anchor,
# but Click Map cannot configure it because it does not yet exist in templates.json.
REQUIRED_WORKING_TEMPLATES = {
    "goal_active_visit_item": {
        "title": "Цель обращения → Активное посещение",
        "file": "goal_active_visit_item.png",
        "confidence": 0.82,
        "type": "template_offset",
        "offset_key": "goal_active_visit_item_offset",
    },
    "inpatient_question": {
        "title": "Пациент в стационаре? — вопрос",
        "file": "inpatient_question.png",
        "confidence": 0.82,
        "type": "template_only",
        "offset_key": None,
    },
    "inpatient_yes_button": {
        "title": "Пациент в стационаре? — Да",
        "file": "inpatient_yes_button.png",
        "confidence": 0.82,
        "type": "template_offset",
        "offset_key": "inpatient_yes_button_offset",
    },
    "add_diagnosis_question": {
        "title": "Добавить диагноз? — вопрос",
        "file": "add_diagnosis_question.png",
        "confidence": 0.82,
        "type": "template_only",
        "offset_key": None,
    },
    "add_diagnosis_no_button": {
        "title": "Добавить диагноз? — Нет",
        "file": "add_diagnosis_no_button.png",
        "confidence": 0.82,
        "type": "template_offset",
        "offset_key": "add_diagnosis_no_button_offset",
    },
}

ABSOLUTE_POINTS = [
    {
        "key": "dob_click_point",
        "title": "Выбор пациента по дате рождения",
        "type": "absolute_point",
        "point_key": "dob_click_point",
    },
    {
        "key": "work_plus_fallback_point",
        "title": "Запасная точка добавления услуги",
        "type": "absolute_point",
        "point_key": "work_plus_fallback_point",
    },
]


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_protocol_template_keys(obj):
    """
    Recursively collect every template_key referenced by protocols.json.
    This lets Click Map know that patient-specific XRAY row templates
    are actionable, even though they do not have a predefined offset key.
    """
    result = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "template_key" and isinstance(value, str) and value.strip():
                result.add(value.strip())
            else:
                result.update(_collect_protocol_template_keys(value))
    elif isinstance(obj, list):
        for value in obj:
            result.update(_collect_protocol_template_keys(value))

    return result



def build_all_targets(coords):
    """
    Build Click Map from the UNION of:
      - every MIS template already registered in templates.json;
      - every template_key referenced by protocols.json;
      - required runtime anchors that must be configurable before their PNG exists.

    This means a newly introduced required runtime anchor can be configured
    directly from Click Map instead of first manually editing templates.json.
    """
    try:
        templates = _load_json(TEMPLATES_PATH).get("mis", {})
    except Exception:
        templates = {}

    mis_coords = coords.get("mis", {})

    try:
        protocol_template_keys = _collect_protocol_template_keys(
            _load_json(PROTOCOLS_PATH)
        )
    except Exception:
        protocol_template_keys = set()

    all_keys = set(templates)
    all_keys.update(protocol_template_keys)
    all_keys.update(REQUIRED_WORKING_TEMPLATES)

    targets = []

    for key in sorted(all_keys):
        conf = dict(templates.get(key, {}) or {})
        required = REQUIRED_WORKING_TEMPLATES.get(key, {})

        if not conf and required:
            conf = {
                "file": required.get("file", f"{key}.png"),
                "confidence": required.get("confidence", 0.82),
            }

        offset_key = SPECIAL_OFFSET_KEYS.get(key)

        generic = f"{key}_offset"
        if not offset_key and generic in mis_coords:
            offset_key = generic

        # Required registry wins when it explicitly defines click semantics.
        required_type = required.get("type")
        if required.get("offset_key"):
            offset_key = required["offset_key"]

        if key == "search_anchor":
            item_type = "search_field"
        elif key in protocol_template_keys:
            item_type = "protocol_template"
            if not offset_key:
                offset_key = f"{key}_offset"
        elif required_type:
            item_type = required_type
        elif offset_key:
            item_type = "template_offset"
        else:
            item_type = "template_only"

        targets.append({
            "key": key,
            "title": required.get("title") or FRIENDLY.get(key, key),
            "type": item_type,
            "template_key": key,
            "offset_key": offset_key,
            "file": conf.get("file", f"{key}.png"),
            "confidence": conf.get("confidence", 0.82),
            "registered": key in templates,
        })

    targets.extend(ABSOLUTE_POINTS)
    return targets


class TechnicalClickMapWindow(tk.Toplevel):
    """
    Карта кликов 2.0.

    Показывает ВСЕ шаблоны из templates.json, а не только заранее
    перечисленные точки клика. Для шаблонов с offset показывает и
    фактическую точку действия. Для search_anchor отдельно вычисляет
    реальное поле поиска пациента.
    """

    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Карта кликов 2.0 — все шаблоны и точки")
        self.geometry("1220x760")
        self.minsize(1050, 650)
        self.transient(parent)

        self.on_saved = on_saved
        self.data = self._load_coords()
        self.targets = build_all_targets(self.data)
        self.current = None

        self._build_ui()
        self._fill_list()
        self._select_first()

    def _load_coords(self):
        return _load_json(COORDS_PATH)

    def _save_coords(self):
        with open(COORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text=(
                "Полная техническая карта МИС. В список автоматически попадают ВСЕ "
                "шаблоны из templates.json, protocol template_key и обязательные runtime-якоря. "
                "Новый обязательный якорь можно настроить даже до создания его PNG."
            ),
            wraplength=1160,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        toolbar = ttk.Frame(root)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="Диагностика всех", command=self.verify_all).pack(side="left")
        ttk.Button(toolbar, text="Обновить", command=self.reload_data).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Закрыть", command=self.destroy).pack(side="right")

        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        body.add(left, weight=1)
        body.add(right, weight=2)

        ttk.Label(left, text="Все элементы", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._fill_list())
        ttk.Entry(left, textvariable=self.filter_var).pack(fill="x", pady=(5, 6))

        self.listbox = tk.Listbox(left, width=44, exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.title_label = ttk.Label(right, text="", font=("Segoe UI", 13, "bold"))
        self.title_label.pack(anchor="w")

        self.desc_label = ttk.Label(right, text="", wraplength=720, justify="left")
        self.desc_label.pack(anchor="w", fill="x", pady=(7, 8))

        self.value_label = ttk.Label(right, text="", justify="left")
        self.value_label.pack(anchor="w", fill="x", pady=(0, 8))

        # Preview of the PNG template selected in the map.
        self.preview_frame = ttk.LabelFrame(right, text="Предпросмотр шаблона", padding=8)
        self.preview_frame.pack(fill="x", pady=(0, 10))

        self.preview_label = ttk.Label(
            self.preview_frame,
            text="Нажмите «Показать шаблон», чтобы увидеть PNG.",
            anchor="center",
            justify="center",
        )
        self.preview_label.pack(fill="x", expand=True)

        self.preview_info = ttk.Label(
            self.preview_frame,
            text="",
            anchor="w",
            justify="left",
        )
        self.preview_info.pack(fill="x", pady=(6, 0))

        # Keep a Python reference to PhotoImage, otherwise Tk disposes it.
        self._preview_photo = None

        buttons = ttk.Frame(right)
        buttons.pack(fill="x", pady=(0, 10))

        ttk.Button(buttons, text="Показать шаблон", command=self.show_template).pack(side="left")
        ttk.Button(buttons, text="Изменить шаблон", command=self.replace_template).pack(side="left", padx=6)
        ttk.Button(buttons, text="Показать точку", command=self.show_point).pack(side="left")
        ttk.Button(buttons, text="Пробный клик", command=self.test_click).pack(side="left", padx=6)
        ttk.Button(buttons, text="Перенастроить точку", command=self.calibrate).pack(side="left")

        self.log_text = tk.Text(right, height=22, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.update_idletasks()

    def _fill_list(self):
        selected_key = self.current["key"] if self.current else None
        query = self.filter_var.get().strip().casefold() if hasattr(self, "filter_var") else ""

        self.listbox.delete(0, "end")
        self.visible_targets = []

        for item in self.targets:
            hay = f"{item['key']} {item.get('title','')} {item.get('file','')}".casefold()
            if query and query not in hay:
                continue
            self.visible_targets.append(item)
            marker = {
                "template_only": "□",
                "template_offset": "●",
                "search_field": "★",
                "protocol_template": "▶",
                "absolute_point": "◆",
            }.get(item["type"], "•")
            self.listbox.insert("end", f"{marker} {item['key']} — {item.get('title', item['key'])}")

        if selected_key:
            for i, item in enumerate(self.visible_targets):
                if item["key"] == selected_key:
                    self.listbox.selection_set(i)
                    break

    def _select_first(self):
        if self.listbox.size():
            self.listbox.selection_set(0)
            self.listbox.event_generate("<<ListboxSelect>>")

    def _on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.visible_targets):
            return
        self.current = self.visible_targets[idx]
        self._render_current()

    def _render_current(self):
        if not self.current:
            return

        self._clear_template_preview()

        item = self.current
        kind_names = {
            "template_only": "только шаблон / контроль",
            "template_offset": "шаблон + offset + точка действия",
            "search_field": "расчётная точка поля поиска",
            "protocol_template": "кликабельный шаблон протокола/рентгена",
            "absolute_point": "абсолютная точка относительно окна МИС",
        }

        self.title_label.config(text=f"{item['key']} — {item.get('title', item['key'])}")

        if item["type"] == "absolute_point":
            point = self.data.get("mis", {}).get(item["point_key"])
            self.desc_label.config(text=f"Тип: {kind_names[item['type']]}")
            self.value_label.config(
                text=f"point_key: {item['point_key']}\nСохранено: {point}"
            )
            return

        offset_key = item.get("offset_key")
        offset = self.data.get("mis", {}).get(offset_key) if offset_key else None
        extra = ""
        if item["key"] == "search_anchor":
            extra = (
                f"\nsearch_anchor_x_offset: "
                f"{self.data.get('mis', {}).get('search_anchor_x_offset')}"
            )

        registration = (
            "зарегистрирован в templates.json"
            if item.get("registered", True)
            else "ещё не зарегистрирован — создайте через «Изменить шаблон»"
        )

        self.desc_label.config(
            text=(
                f"Тип: {kind_names[item['type']]}\n"
                f"Файл: {item.get('file') or '-'}\n"
                f"Confidence: {item.get('confidence')}\n"
                f"Статус: {registration}"
            )
        )
        self.value_label.config(
            text=(
                f"template_key: {item['template_key']}\n"
                f"offset_key: {offset_key or '-'}\n"
                f"offset: {offset if offset is not None else '-'}"
                f"{extra}"
            )
        )

    def _clear_template_preview(self):
        if not hasattr(self, "preview_label"):
            return

        self._preview_photo = None
        self.preview_label.configure(
            image="",
            text="Нажмите «Показать шаблон», чтобы увидеть PNG.",
        )
        self.preview_info.configure(text="")

    def _template_png_path(self, item=None):
        item = item or self.current
        if not item or item.get("type") == "absolute_point":
            return None

        file_name = str(item.get("file") or "").strip()

        # Re-read templates.json so a just-replaced template is reflected immediately.
        try:
            cfg = _load_json(TEMPLATES_PATH).get("mis", {}).get(
                item.get("template_key"),
                {},
            )
            file_name = str(cfg.get("file") or file_name).strip()
        except Exception:
            pass

        if not file_name:
            file_name = f"{item.get('template_key')}.png"

        return TEMPLATES_DIR / file_name

    def _show_template_preview(self, item=None):
        item = item or self.current

        if not item or item.get("type") == "absolute_point":
            self._clear_template_preview()
            if hasattr(self, "preview_label"):
                self.preview_label.configure(
                    text="У этого элемента нет PNG-шаблона."
                )
            return False

        path = self._template_png_path(item)

        if path is None or not path.exists():
            self._preview_photo = None
            self.preview_label.configure(
                image="",
                text=f"PNG-шаблон не найден на диске:\n{path}",
            )
            self.preview_info.configure(text="")
            return False

        try:
            image = Image.open(path).convert("RGB")
            original_w, original_h = image.size

            # Large enough to inspect details, but do not blow up the whole window.
            max_w = 620
            max_h = 220
            scale = min(
                max_w / max(1, original_w),
                max_h / max(1, original_h),
                1.0,
            )

            if scale < 1.0:
                preview = image.resize(
                    (
                        max(1, int(original_w * scale)),
                        max(1, int(original_h * scale)),
                    ),
                    Image.Resampling.LANCZOS,
                )
            else:
                preview = image

            self._preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(
                image=self._preview_photo,
                text="",
            )
            self.preview_info.configure(
                text=(
                    f"{path.name}   |   исходный размер: "
                    f"{original_w}×{original_h}px   |   {path}"
                )
            )
            return True

        except Exception as e:
            self._preview_photo = None
            self.preview_label.configure(
                image="",
                text=f"Не удалось открыть PNG:\n{e}",
            )
            self.preview_info.configure(text=str(path))
            return False

    def reload_data(self):
        self.data = self._load_coords()
        self.targets = build_all_targets(self.data)
        self._fill_list()
        self._render_current()
        self._log("Конфигурация перечитана. Список шаблонов обновлён.")

    def _locate(self, timeout=5):
        if not self.current or self.current["type"] == "absolute_point":
            return None
        return locate_image_on_screen(self.current["template_key"], timeout=timeout)

    def _calc(self, timeout=5):
        item = self.current

        if item["type"] == "absolute_point":
            win = find_mis_window()
            point = self.data.get("mis", {}).get(item["point_key"])
            if not point or len(point) != 2:
                raise RuntimeError(f"Не настроено: {item['point_key']}")
            return {
                "base": (win.left, win.top),
                "final": (win.left + int(point[0]), win.top + int(point[1])),
                "loc": None,
            }

        loc = self._locate(timeout)
        if not loc:
            raise RuntimeError(f"Шаблон сейчас не найден: {item['template_key']}")

        base = (int(loc.x), int(loc.y))

        if item["type"] == "template_only":
            return {"base": base, "final": None, "loc": loc}

        if item["type"] == "search_field":
            offset = self.data.get("mis", {}).get("search_anchor_offset", [0, 0])
            xoff = int(self.data.get("mis", {}).get("search_anchor_x_offset", 0))
            anchor_x = base[0] + int(offset[0])
            anchor_y = base[1] + int(offset[1])
            final = (anchor_x - xoff, anchor_y)
            return {"base": base, "final": final, "loc": loc}

        if item["type"] == "protocol_template":
            offset = self.data.get("mis", {}).get(item["offset_key"], [0, 0])
            final = (base[0] + int(offset[0]), base[1] + int(offset[1]))
            return {"base": base, "final": final, "loc": loc}

        offset = self.data.get("mis", {}).get(item["offset_key"], [0, 0])
        final = (base[0] + int(offset[0]), base[1] + int(offset[1]))
        return {"base": base, "final": final, "loc": loc}

    def replace_template(self):
        if not self.current:
            return

        item = self.current

        if item["type"] == "absolute_point":
            messagebox.showinfo(
                "Изменить шаблон",
                "У этого элемента нет шаблона — это абсолютная точка.",
                parent=self,
            )
            return

        key = item["template_key"]
        templates_data = _load_json(TEMPLATES_PATH)
        current_cfg = templates_data.get("mis", {}).get(key, {})

        file_name = str(current_cfg.get("file") or item.get("file") or f"{key}.png")
        confidence = current_cfg.get("confidence", item.get("confidence") or 0.82)
        description = current_cfg.get(
            "description",
            f"Карта кликов 2.0: {item.get('title', key)}",
        )

        self.withdraw()
        self.update()

        saved = False

        try:
            rect = pick_rect_in_mis(
                self.master,
                f"{item.get('title', key)}: выделите новый шаблон",
                rect_color="yellow",
            )

            if rect is None:
                return

            left, top, width, height = rect
            if width <= 2 or height <= 2:
                raise RuntimeError("Слишком маленькая область.")

            TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            target = TEMPLATES_DIR / file_name

            backup = None
            if target.exists():
                stamp = time.strftime("%Y%m%d_%H%M%S")
                backup = target.with_name(f"{target.stem}_old_{stamp}{target.suffix}")
                shutil.copy2(target, backup)

            try:
                image = ImageGrab.grab(
                    bbox=(left, top, left + width, top + height),
                    all_screens=True,
                )
            except TypeError:
                image = ImageGrab.grab(
                    bbox=(left, top, left + width, top + height)
                )

            image.save(target)

            templates_data.setdefault("mis", {})[key] = {
                "file": file_name,
                "confidence": confidence,
                "description": description,
            }

            with open(TEMPLATES_PATH, "w", encoding="utf-8") as f:
                json.dump(templates_data, f, ensure_ascii=False, indent=2)

            if item.get("offset_key"):
                coords = self._load_coords()
                coords.setdefault("mis", {}).setdefault(item["offset_key"], [0, 0])
                with open(COORDS_PATH, "w", encoding="utf-8") as f:
                    json.dump(coords, f, ensure_ascii=False, indent=2)
                self.data = coords

            self._log(
                f"[TEMPLATE SAVED] {key}: "
                f"rect=({left},{top},{width},{height}) -> {target}"
            )
            if backup:
                self._log(f"[BACKUP] {backup}")

            saved = True

        except Exception as e:
            messagebox.showerror("Изменить шаблон", str(e), parent=self)

        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

        if not saved:
            return

        self.reload_data()
        self._show_template_preview(self.current)

        if item["type"] in {"template_offset", "search_field", "protocol_template"}:
            if messagebox.askyesno(
                "Шаблон обновлён",
                "Новый шаблон сохранён.\n\n"
                "Сразу перенастроить точку действия относительно нового шаблона?",
                parent=self,
            ):
                self.calibrate()

    def show_template(self):
        if not self.current:
            return

        if self.current["type"] == "absolute_point":
            self._show_template_preview(self.current)
            messagebox.showinfo(
                "Карта кликов",
                "У этого элемента нет шаблона.",
                parent=self,
            )
            return

        # Show the stored PNG first. This works even when the template
        # cannot currently be found on the MIS screen.
        preview_ok = self._show_template_preview(self.current)

        try:
            result = self._calc(timeout=6)
            x, y = result["base"]
            self._log(
                f"[ШАБЛОН] {self.current['key']}: найден в ({x}, {y}); "
                f"PNG preview={'OK' if preview_ok else 'NO'}"
            )
            debug_click_point(x, y)
        except Exception as e:
            # Do not lose the preview just because live matching failed.
            self._log(
                f"[ШАБЛОН НЕ НАЙДЕН НА ЭКРАНЕ] {self.current['key']}: {e}"
            )
            messagebox.showwarning(
                "Шаблон",
                f"{e}\n\nPNG-предпросмотр показан справа, если файл существует.",
                parent=self,
            )

    def show_point(self):
        if not self.current:
            return
        try:
            result = self._calc(timeout=6)
            if result["final"] is None:
                x, y = result["base"]
                self._log(
                    f"[ТОЛЬКО ШАБЛОН] {self.current['key']}: "
                    f"base=({x},{y}); отдельной точки действия нет"
                )
                debug_click_point(x, y)
                return

            x, y = result["final"]
            self._log(
                f"[ТОЧКА] {self.current['key']}: "
                f"base={result['base']} -> final=({x},{y})"
            )
            debug_click_point(x, y)
        except Exception as e:
            messagebox.showerror("Точка", str(e), parent=self)

    def test_click(self):
        if not self.current:
            return
        try:
            result = self._calc(timeout=6)
            if result["final"] is None:
                messagebox.showinfo(
                    "Пробный клик",
                    "Это контрольный шаблон. Бот по нему не кликает.",
                    parent=self,
                )
                return

            x, y = result["final"]
            if not messagebox.askyesno(
                "Пробный клик",
                f"{self.current['key']}\n\nКликнуть в ({x}, {y})?",
                parent=self,
            ):
                return

            self._log(
                f"[TEST] {self.current['key']}: base={result['base']} final=({x},{y})"
            )
            debug_click_point(x, y)
            time.sleep(0.25)
            pyautogui.click(x, y)
        except Exception as e:
            messagebox.showerror("Пробный клик", str(e), parent=self)

    def calibrate(self):
        if not self.current:
            return

        item = self.current

        if item["type"] == "template_only":
            messagebox.showinfo(
                "Перенастройка",
                "Это контрольный шаблон без точки клика. "
                "Его изображение меняется через настройку/захват шаблонов.",
                parent=self,
            )
            return

        try:
            if item["type"] == "absolute_point":
                win = find_mis_window()
                self.withdraw()
                try:
                    picked = pick_point_in_mis(
                        self.master,
                        f"Кликни правильную точку: {item['title']}",
                    )
                finally:
                    self.deiconify()
                    self.lift()

                if not picked:
                    return
                value = [int(picked[0] - win.left), int(picked[1] - win.top)]
                self.data.setdefault("mis", {})[item["point_key"]] = value
                self._save_coords()
                self._log(f"[SAVED] {item['point_key']} = {value}")
            else:
                loc = self._locate(timeout=6)
                if not loc:
                    self.deiconify()
                    self.lift()
                    self.focus_force()

                    if messagebox.askyesno(
                        "Шаблон не найден",
                        f"Шаблон '{item['template_key']}' сейчас не найден.\n\n"
                        "Выделить новый шаблон прямо сейчас?",
                        parent=self,
                    ):
                        self.replace_template()
                    return

                self.withdraw()
                try:
                    picked = pick_point_in_mis(
                        self.master,
                        f"Кликни правильную точку: {item['title']}",
                    )
                finally:
                    self.deiconify()
                    self.lift()

                if not picked:
                    return

                if item["type"] == "search_field":
                    # Keep search_anchor_offset and calculate the X distance used
                    # by the real runtime search code.
                    off = self.data.get("mis", {}).get("search_anchor_offset", [0, 0])
                    anchor_x = int(loc.x) + int(off[0])
                    anchor_y = int(loc.y) + int(off[1])
                    xoff = int(anchor_x - picked[0])
                    self.data.setdefault("mis", {})["search_anchor_x_offset"] = xoff
                    self._save_coords()
                    self._log(
                        f"[SAVED] search_anchor_x_offset={xoff}; "
                        f"anchor=({anchor_x},{anchor_y}) picked={picked}"
                    )
                else:
                    dx = int(picked[0] - loc.x)
                    dy = int(picked[1] - loc.y)
                    self.data.setdefault("mis", {})[item["offset_key"]] = [dx, dy]
                    self._save_coords()
                    self._log(
                        f"[SAVED] {item['offset_key']}=[{dx},{dy}]; "
                        f"base=({loc.x},{loc.y}) picked={picked}"
                    )

            self.reload_data()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            messagebox.showerror("Перенастройка", str(e), parent=self)

    def verify_all(self):
        self._log("")
        self._log("=== ДИАГНОСТИКА ВСЕХ ШАБЛОНОВ И ТОЧЕК ===")
        self._log(
            "Важно: некоторые шаблоны появляются только на определённом шаге МИС, "
            "поэтому статус НЕ НАЙДЕН не всегда означает ошибку."
        )

        ok = 0
        absent = 0
        errors = 0

        # Do not use self.current during iteration; restore it afterwards.
        previous = self.current

        for item in self.targets:
            self.current = item
            try:
                if item["type"] == "absolute_point":
                    result = self._calc(timeout=0.1)
                    self._log(
                        f"[POINT] {item['key']}: final={result['final']}"
                    )
                    ok += 1
                    continue

                loc = self._locate(timeout=0.45)
                if not loc:
                    self._log(f"[НЕ НАЙДЕН] {item['key']}")
                    absent += 1
                    continue

                result = self._calc(timeout=0.1)
                if result["final"] is None:
                    self._log(
                        f"[FOUND] {item['key']}: template={result['base']}"
                    )
                else:
                    self._log(
                        f"[FOUND] {item['key']}: template={result['base']} "
                        f"-> action={result['final']}"
                    )
                ok += 1

            except Exception as e:
                self._log(f"[ERROR] {item['key']}: {e}")
                errors += 1

        self.current = previous
        self._render_current()

        self._log(
            f"=== ИТОГ: найдено/настроено {ok}; "
            f"сейчас не видно {absent}; ошибок {errors} ==="
        )


# Compatibility: old imports may still expect this name.
CLICK_TARGETS = []
