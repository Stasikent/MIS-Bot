import json
from pathlib import Path
from services.runtime_paths import CONFIG_DIR, TEMPLATES_DIR
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import ImageGrab

from gui.mis_window_overlay import pick_rect_in_mis, pick_point_in_mis
from project.bot_mode1_current import locate_image_on_screen

TEMPLATES_PATH = CONFIG_DIR / "templates.json"
COORDS_PATH = CONFIG_DIR / "coordinates.json"


SETUP_STEPS = [
    {
        "key": "search_anchor",
        "title": "Поле поиска пациента",
        "kind": "template_only",
        "description": (
            "Откройте экран поиска пациента в МИС. "
            "Выделите устойчивую область рядом с полем ввода ФИО."
        ),
    },
    {
        "key": "visit_plus",
        "title": "Плюс открытия приёма",
        "kind": "template_offset",
        "offset_key": "visit_plus_offset",
        "description": (
            "Откройте карточку пациента так, чтобы был виден плюс добавления/открытия приёма. "
            "Сначала выделите устойчивый якорь, затем укажите фактическую точку клика."
        ),
    },
    {
        "key": "reason_field",
        "title": "Поле «Повод обращения»",
        "kind": "template_offset",
        "offset_key": "reason_field_offset",
        "description": (
            "Откройте окно приёма. Выделите устойчивую часть поля «Повод обращения», "
            "затем укажите точку, куда бот должен кликать."
        ),
    },
    {
        "key": "goal_dropdown",
        "title": "Поле «Цель обращения»",
        "kind": "template_offset",
        "offset_key": "goal_dropdown_offset",
        "description": (
            "Откройте окно приёма. Выделите область выпадающего списка цели обращения, "
            "затем кликните по фактической точке."
        ),
    },
    {
        "key": "work_plus",
        "title": "Плюс добавления услуги",
        "kind": "template_offset",
        "offset_key": "work_plus_offset",
        "description": (
            "Перейдите к блоку услуг. Выделите плюс добавления услуги, "
            "затем укажите реальную точку клика."
        ),
    },
    {
        "key": "service_price_zero",
        "title": "Строка услуги 0,00",
        "kind": "template_offset",
        "offset_key": "service_price_zero_offset",
        "description": (
            "Откройте список услуг. Выделите устойчивую часть нужной строки услуги, "
            "затем укажите точку клика."
        ),
    },
    {
        "key": "history_menu",
        "title": "Меню «История болезни»",
        "kind": "template_offset",
        "offset_key": "history_menu_offset",
        "description": (
            "Откройте протокол/карточку так, чтобы было видно меню «История болезни». "
            "Выделите якорь и затем точку клика."
        ),
    },
    {
        "key": "history_fluoro_item",
        "title": "Пункт «Флюорографическое исследование»",
        "kind": "template_offset",
        "offset_key": "history_fluoro_item_offset",
        "description": (
            "Откройте меню «История болезни» и выделите пункт флюорографического исследования. "
            "После этого укажите точку клика."
        ),
    },
    {
        "key": "history_xray_item",
        "title": "Пункт «Рентгенографическое исследование»",
        "kind": "template_offset",
        "offset_key": "history_xray_item_offset",
        "description": (
            "Откройте меню «История болезни» и выделите пункт рентгенографического исследования. "
            "После этого укажите точку клика."
        ),
    },
    {
        "key": "templates_anchor",
        "title": "Кнопка «Шаблоны»",
        "kind": "template_offset",
        "offset_key": "templates_anchor_offset",
        "description": (
            "Откройте протокол. Выделите кнопку «Шаблоны» и затем укажите реальную точку клика."
        ),
    },
    {
        "key": "template_owner_dropdown",
        "title": "Сортировка по владельцу",
        "kind": "template_only",
        "description": (
            "После открытия списка шаблонов выделите элемент выбора владельца."
        ),
    },
    {
        "key": "template_owner_only_mine",
        "title": "«Только свои»",
        "kind": "template_only",
        "description": (
            "Откройте список владельца и выделите пункт «Только свои»."
        ),
    },
    {
        "key": "diagnosis_drop",
        "title": "Выпадающее меню диагноза",
        "kind": "template_offset",
        "offset_key": "diagnosis_drop_offset",
        "description": (
            "Перейдите к диагнозу. Выделите кнопку/область открытия списка диагнозов, "
            "затем укажите точку клика."
        ),
    },
    {
        "key": "diagnosis_code",
        "title": "Активный диагноз",
        "kind": "template_offset",
        "offset_key": "diagnosis_code_offset",
        "description": (
            "После открытия списка диагнозов выделите активный диагноз, "
            "затем кликните по точке выбора."
        ),
    },
    {
        "key": "diagnosis_close_item",
        "title": "Пункт «Закрыть»",
        "kind": "template_offset",
        "offset_key": "diagnosis_close_item_offset",
        "description": (
            "После клика по активному диагнозу выделите пункт «Закрыть» "
            "и укажите точку клика."
        ),
    },
    {
        "key": "case_result_label",
        "title": "«Результат случая»",
        "kind": "template_offset",
        "offset_key": "case_result_label_offset",
        "description": (
            "В окне закрытия случая выделите устойчивый якорь рядом с полем «Результат случая»."
        ),
    },
    {
        "key": "case_outcome_label",
        "title": "«Исход заболевания»",
        "kind": "template_offset",
        "offset_key": "case_outcome_label_offset",
        "description": (
            "В том же окне выделите устойчивый якорь рядом с полем «Исход заболевания»."
        ),
    },
    {
        "key": "case_close_current_diagnosis",
        "title": "«Закрыть с текущим диагнозом»",
        "kind": "template_offset",
        "offset_key": "case_close_current_diagnosis_offset",
        "description": (
            "Выделите кнопку «Закрыть с текущим диагнозом»."
        ),
    },
    {
        "key": "epicrisis_yes_signed",
        "title": "«Да, с подписью»",
        "kind": "template_offset",
        "offset_key": "epicrisis_yes_signed_offset",
        "description": (
            "Откройте вопрос формирования эпикриза и выделите кнопку «Да, с подписью»."
        ),
    },
    {
        "key": "protocol_anchor",
        "title": "Якорь открытого протокола",
        "kind": "template_only",
        "description": "Откройте протокол и выделите устойчивую область, подтверждающую, что протокол действительно открылся.",
    },
    {
        "key": "template_use",
        "title": "Пункт «Выбрать» в меню шаблонов",
        "kind": "template_offset",
        "offset_key": "template_use_offset",
        "description": "Откройте меню шаблонов, выделите пункт «Выбрать» и затем укажите точку клика.",
    },
    {
        "key": "study_date_label",
        "title": "Метка даты исследования",
        "kind": "template_offset",
        "offset_key": "study_date_label_offset",
        "description": "Выделите подпись/якорь рядом с датой исследования и затем кликните в само поле даты.",
    },
    {
        "key": "sign_password_field",
        "title": "Поле пароля подписи",
        "kind": "template_only",
        "description": "В окне подписи выделите само поле ввода пароля.",
    },
    {
        "key": "sign_password_dialog",
        "title": "Окно подписи",
        "kind": "template_only",
        "description": (
            "Откройте окно подписи и выделите устойчивую область окна."
        ),
    },
]


class WorkplaceSetupWizard(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Первоначальная настройка рабочего места")
        self.geometry("920x620")
        self.minsize(850, 560)
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self.index = 0

        self.templates = self._load_json(TEMPLATES_PATH, {"mis": {}, "ris": {}})
        self.coords = self._load_json(COORDS_PATH, {"mis": {}, "ris": {}})

        self._build_ui()
        self._render_step()

    def _load_json(self, path: Path, fallback: dict):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return fallback

    def _save_all(self):
        TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        COORDS_PATH.parent.mkdir(parents=True, exist_ok=True)

        TEMPLATES_PATH.write_text(
            json.dumps(self.templates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        COORDS_PATH.write_text(
            json.dumps(self.coords, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if self.on_saved:
            self.on_saved()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        self.step_label = ttk.Label(
            root,
            text="",
            font=("Segoe UI", 13, "bold"),
        )
        self.step_label.pack(anchor="w")

        self.title_label = ttk.Label(
            root,
            text="",
            font=("Segoe UI", 11, "bold"),
        )
        self.title_label.pack(anchor="w", pady=(12, 4))

        self.desc_label = ttk.Label(
            root,
            text="",
            wraplength=830,
            justify="left",
        )
        self.desc_label.pack(anchor="w", pady=(0, 12))

        self.status_label = ttk.Label(
            root,
            text="",
            foreground="#444444",
            justify="left",
        )
        self.status_label.pack(anchor="w", pady=(0, 12))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(0, 12))

        self.capture_btn = ttk.Button(
            btns,
            text="Настроить текущий шаг",
            command=self._configure_current,
        )
        self.capture_btn.pack(side="left")

        ttk.Button(
            btns,
            text="Проверить",
            command=self._verify_current,
        ).pack(side="left", padx=6)

        ttk.Button(
            btns,
            text="Пропустить",
            command=self._skip,
        ).pack(side="left", padx=6)

        ttk.Button(
            btns,
            text="Назад",
            command=self._prev,
        ).pack(side="right")

        ttk.Button(
            btns,
            text="Далее",
            command=self._next,
        ).pack(side="right", padx=6)

        self.log_text = tk.Text(root, height=20, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Button(
            bottom,
            text="Проверить все настроенные элементы",
            command=self._verify_all,
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="Закрыть",
            command=self.destroy,
        ).pack(side="right")

    def _step(self):
        return SETUP_STEPS[self.index]

    def _render_step(self):
        step = self._step()

        self.step_label.config(
            text=f"Шаг {self.index + 1} / {len(SETUP_STEPS)}"
        )
        self.title_label.config(text=step["title"])
        self.desc_label.config(text=step["description"])

        template_item = self.templates.get("mis", {}).get(step["key"])
        template_status = "есть" if template_item else "нет"

        offset_status = ""
        if step["kind"] == "template_offset":
            offset = self.coords.get("mis", {}).get(step["offset_key"])
            offset_status = f"\nOffset {step['offset_key']}: {offset if offset is not None else 'нет'}"

        self.status_label.config(
            text=(
                f"Шаблон {step['key']}: {template_status}"
                f"{offset_status}"
            )
        )

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _configure_current(self):
        step = self._step()

        self.withdraw()
        self.update()

        try:
            rect = pick_rect_in_mis(
                self.master,
                f"{step['title']}: выделите область-якорь",
                rect_color="yellow",
            )

            if rect is None:
                raise RuntimeError("Выделение отменено.")

            left, top, width, height = rect
            if width <= 2 or height <= 2:
                raise RuntimeError("Слишком маленькая область.")

            TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

            file_name = f"{step['key']}.png"
            target = TEMPLATES_DIR / file_name

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

            self.templates.setdefault("mis", {})[step["key"]] = {
                "file": file_name,
                "confidence": 0.82,
                "description": f"Мастер рабочего места: {step['title']}",
            }

            if step["kind"] == "template_offset":
                point = pick_point_in_mis(
                    self.master,
                    f"{step['title']}: теперь кликните по фактической точке действия",
                )

                if point is None:
                    raise RuntimeError("Выбор точки отменён.")

                click_x, click_y = point

                # locateCenterOnScreen() возвращает ЦЕНТР шаблона.
                # Поэтому offset обязан считаться от центра выделенной области.
                base_x = left + width / 2
                base_y = top + height / 2
                dx = int(round(click_x - base_x))
                dy = int(round(click_y - base_y))

                self.coords.setdefault("mis", {})[step["offset_key"]] = [dx, dy]

            self._save_all()
            self._log(f"[OK] {step['key']} настроен.")

        except Exception as e:
            self._log(f"[ERROR] {step['key']}: {e}")
            messagebox.showerror("Ошибка настройки", str(e), parent=self)

        finally:
            self.deiconify()
            self.lift()
            self.focus_force()
            self._render_step()

    def _verify_current(self):
        step = self._step()

        self.withdraw()
        self.update()

        try:
            loc = locate_image_on_screen(step["key"], timeout=4)

            if not loc:
                self._log(f"[FAIL] {step['key']} не найден.")
                messagebox.showwarning(
                    "Проверка",
                    f"{step['title']}: шаблон не найден.",
                    parent=self,
                )
                return

            self._log(
                f"[OK] {step['key']} найден в точке ({loc.x}, {loc.y})."
            )

            messagebox.showinfo(
                "Проверка",
                f"{step['title']}: найден.",
                parent=self,
            )

        except Exception as e:
            self._log(f"[ERROR] Проверка {step['key']}: {e}")

        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

    def _verify_all(self):
        self.withdraw()
        self.update()

        results = []

        try:
            for step in SETUP_STEPS:
                try:
                    loc = locate_image_on_screen(step["key"], timeout=1.2)
                    ok = bool(loc)
                except Exception:
                    ok = False

                results.append((step["key"], step["title"], ok))

        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

        self._log("")
        self._log("=== Проверка всех элементов ===")

        ok_count = 0

        for key, title, ok in results:
            mark = "OK" if ok else "FAIL"
            self._log(f"[{mark}] {key} — {title}")
            if ok:
                ok_count += 1

        messagebox.showinfo(
            "Результат проверки",
            f"Найдено {ok_count} из {len(results)} элементов.\n"
            f"Подробности — в журнале мастера.",
            parent=self,
        )

    def _next(self):
        if self.index < len(SETUP_STEPS) - 1:
            self.index += 1
            self._render_step()
        else:
            messagebox.showinfo(
                "Готово",
                "Все шаги мастера пройдены.",
                parent=self,
            )

    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._render_step()

    def _skip(self):
        self._log(f"[SKIP] {self._step()['key']}")
        self._next()
