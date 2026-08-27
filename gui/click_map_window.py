import json
import time
import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui

from config.loader import CONFIG_DIR
from gui.mis_window_overlay import pick_point_in_mis
from project.bot_mode1_current import (
    find_mis_window,
    locate_image_on_screen,
    debug_click_point,
)

COORDS_PATH = CONFIG_DIR / "coordinates.json"

CLICK_TARGETS = [
    {
        "key": "visit_plus",
        "title": "Открытие приёма",
        "type": "template_offset",
        "template_key": "visit_plus",
        "offset_key": "visit_plus_offset",
        "description": "Клик по плюсу открытия приема.",
    },
    {
        "key": "reason_field",
        "title": "Повод обращения",
        "type": "template_offset",
        "template_key": "reason_field",
        "offset_key": "reason_field_offset",
        "description": "Клик в поле Повод обращения.",
    },
    {
        "key": "goal_dropdown",
        "title": "Цель обращения",
        "type": "template_offset",
        "template_key": "goal_dropdown",
        "offset_key": "goal_dropdown_offset",
        "description": "Клик по выпадающему списку цели обращения.",
    },
    {
        "key": "history_menu",
        "title": "История болезни",
        "type": "template_offset",
        "template_key": "history_menu",
        "offset_key": "history_menu_offset",
        "description": "Клик по меню История болезни.",
    },
    {
        "key": "history_fluoro_item",
        "title": "Флюорографическое исследование",
        "type": "template_offset",
        "template_key": "history_fluoro_item",
        "offset_key": "history_fluoro_item_offset",
        "description": "Клик по пункту флюорографического исследования.",
    },
    {
        "key": "history_xray_item",
        "title": "Рентгенографическое исследование",
        "type": "template_offset",
        "template_key": "history_xray_item",
        "offset_key": "history_xray_item_offset",
        "description": "Клик по пункту рентгенографического исследования.",
    },
    {
        "key": "templates_anchor",
        "title": "Кнопка «Шаблоны»",
        "type": "template_offset",
        "template_key": "templates_anchor",
        "offset_key": "templates_anchor_offset",
        "description": "Клик по кнопке Шаблоны.",
    },
    {
        "key": "template_use",
        "title": "Выбор шаблона",
        "type": "template_offset",
        "template_key": "template_use",
        "offset_key": "template_use_offset",
        "description": "Клик по пункту Выбрать.",
    },
    {
        "key": "service_price_zero",
        "title": "Строка услуги",
        "type": "template_offset",
        "template_key": "service_price_zero",
        "offset_key": "service_price_zero_offset",
        "description": "Клик по строке услуги 0,00.",
    },
    {
        "key": "work_plus",
        "title": "Добавление услуги",
        "type": "template_offset",
        "template_key": "work_plus",
        "offset_key": "work_plus_offset",
        "description": "Клик по плюсу добавления услуги.",
    },
    {
        "key": "diagnosis_drop",
        "title": "Меню диагноза",
        "type": "template_offset",
        "template_key": "diagnosis_drop",
        "offset_key": "diagnosis_drop_offset",
        "description": "Клик по выпадающему списку диагноза.",
    },
    {
        "key": "diagnosis_code",
        "title": "Выбор диагноза",
        "type": "template_offset",
        "template_key": "diagnosis_code",
        "offset_key": "diagnosis_code_offset",
        "description": "Клик по найденному диагнозу.",
    },
    {
        "key": "diagnosis_cancel_item",
        "title": "Отмена диагноза",
        "type": "template_offset",
        "template_key": "diagnosis_cancel_item",
        "offset_key": "diagnosis_cancel_item_offset",
        "description": "Клик по пункту Отменить.",
    },
    {
        "key": "dob_click_point",
        "title": "Выбор пациента по дате рождения",
        "type": "absolute_point",
        "point_key": "dob_click_point",
        "description": "Абсолютная точка клика по найденной строке пациента.",
    },
    {
        "key": "work_plus_fallback_point",
        "title": "Запасная точка добавления услуги",
        "type": "absolute_point",
        "point_key": "work_plus_fallback_point",
        "description": "Запасная точка клика по work_plus.",
    },
]

class ClickMapWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Коррекция рабочего места")
        self.geometry("1040x680")
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self.data = self._load_coords()
        self.current = None

        self._build_ui()
        self._fill_list()
        self._select_first()

    def _load_coords(self):
        with open(COORDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_coords(self):
        with open(COORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        intro = ttk.Label(
            root,
            text=(
                "Здесь можно проверить и исправить отдельные действия программы. "
                "Если рабочее место настраивается впервые, используйте "
                "«Первоначальную настройку рабочего места»."
            ),
            wraplength=980,
            justify="left",
        )
        intro.pack(fill="x", pady=(0, 10))

        toolbar = ttk.Frame(root)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(
            toolbar,
            text="Проверить всё",
            command=self.verify_all,
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Обновить список",
            command=self.reload_data,
        ).pack(side="left", padx=6)

        ttk.Button(
            toolbar,
            text="Закрыть",
            command=self.destroy,
        ).pack(side="right")

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y")

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        ttk.Label(
            left,
            text="Действия программы",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.listbox = tk.Listbox(
            left,
            width=38,
            height=30,
            exportselection=False,
        )
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.title_label = ttk.Label(
            right,
            text="Действие",
            font=("Segoe UI", 12, "bold"),
        )
        self.title_label.pack(anchor="w")

        self.desc_label = ttk.Label(
            right,
            text="",
            wraplength=660,
            justify="left",
        )
        self.desc_label.pack(anchor="w", pady=(6, 10))

        self.value_label = ttk.Label(
            right,
            text="",
            justify="left",
            foreground="#444444",
        )
        self.value_label.pack(anchor="w", pady=(0, 12))

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=(0, 10))

        ttk.Button(
            btns,
            text="Проверить",
            command=self.show_point,
        ).pack(side="left")

        ttk.Button(
            btns,
            text="Пробный клик",
            command=self.test_click,
        ).pack(side="left", padx=6)

        ttk.Button(
            btns,
            text="Изменить",
            command=self.calibrate,
        ).pack(side="left")

        self.log_text = tk.Text(right, height=20, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _fill_list(self):
        self.listbox.delete(0, "end")
        for item in CLICK_TARGETS:
            self.listbox.insert("end", item["title"])

    def _select_first(self):
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)
            self.listbox.event_generate("<<ListboxSelect>>")

    def _on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        title = self.listbox.get(sel[0])
        for item in CLICK_TARGETS:
            if item["title"] == title:
                self.current = item
                break
        self._render_current()

    def _render_current(self):
        if not self.current:
            return

        self.title_label.config(text=self.current["title"])
        self.desc_label.config(text=self.current.get("description", ""))

        if self.current["type"] == "template_offset":
            value = self.data.get("mis", {}).get(self.current["offset_key"], [0, 0])
            state = "настроено" if value is not None else "не настроено"
            self.value_label.config(
                text=f"Состояние: {state}\nСохранённая поправка: {value}"
            )
        else:
            value = self.data.get("mis", {}).get(self.current["point_key"])
            state = "настроено" if value and len(value) == 2 else "не настроено"
            self.value_label.config(
                text=f"Состояние: {state}\nСохранённая точка: {value if value else 'нет'}"
            )

    def reload_data(self):
        self.data = self._load_coords()
        self._render_current()
        self._log("Настройки перечитаны с диска")

    def _get_template_final_point(self):
        template_key = self.current["template_key"]
        offset_key = self.current["offset_key"]
        offset = tuple(self.data.get("mis", {}).get(offset_key, [0, 0]))

        loc = locate_image_on_screen(template_key, timeout=6)
        if not loc:
            raise RuntimeError(f"Не найден шаблон: {template_key}")

        final_x = loc.x + offset[0]
        final_y = loc.y + offset[1]
        return loc.x, loc.y, final_x, final_y

    def _get_absolute_final_point(self):
        win = find_mis_window()
        point_key = self.current["point_key"]
        point = self.data.get("mis", {}).get(point_key)

        if not point or len(point) != 2:
            raise RuntimeError(f"Не найдена точка в config: {point_key}")

        final_x = win.left + point[0]
        final_y = win.top + point[1]
        return win.left, win.top, final_x, final_y

    def show_point(self):
        if not self.current:
            return

        try:
            if self.current["type"] == "template_offset":
                base_x, base_y, final_x, final_y = self._get_template_final_point()
                self._log(f"{self.current['title']}: base=({base_x},{base_y}) final=({final_x},{final_y})")
            else:
                win_left, win_top, final_x, final_y = self._get_absolute_final_point()
                self._log(f"{self.current['title']}: win=({win_left},{win_top}) final=({final_x},{final_y})")

            debug_click_point(final_x, final_y)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def test_click(self):
        if not self.current:
            return

        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Выполнить пробный клик: {self.current['title']} ?",
            parent=self,
        )
        if not confirm:
            return

        try:
            if self.current["type"] == "template_offset":
                base_x, base_y, final_x, final_y = self._get_template_final_point()
                self._log(f"TEST {self.current['title']}: base=({base_x},{base_y}) final=({final_x},{final_y})")
            else:
                win_left, win_top, final_x, final_y = self._get_absolute_final_point()
                self._log(f"TEST {self.current['title']}: win=({win_left},{win_top}) final=({final_x},{final_y})")

            debug_click_point(final_x, final_y)
            time.sleep(0.2)
            pyautogui.click(final_x, final_y)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def verify_all(self):
        self._log("")
        self._log("=== Проверка рабочего места ===")

        ok_count = 0
        fail_count = 0

        for item in CLICK_TARGETS:
            title = item["title"]

            try:
                if item["type"] == "template_offset":
                    loc = locate_image_on_screen(item["template_key"], timeout=1.5)
                    ok = bool(loc)
                else:
                    point = self.data.get("mis", {}).get(item["point_key"])
                    ok = bool(point and len(point) == 2)

                if ok:
                    self._log(f"[OK] {title}")
                    ok_count += 1
                else:
                    self._log(f"[ТРЕБУЕТ ПРОВЕРКИ] {title}")
                    fail_count += 1

            except Exception as e:
                self._log(f"[ОШИБКА] {title}: {e}")
                fail_count += 1

        messagebox.showinfo(
            "Проверка рабочего места",
            f"Работают/настроены: {ok_count}\n"
            f"Требуют внимания: {fail_count}\n\n"
            "Подробности показаны в журнале.",
            parent=self,
        )

    def calibrate(self):
        if not self.current:
            return

        try:
            if self.current["type"] == "template_offset":
                self._calibrate_template_offset()
            else:
                self._calibrate_absolute_point()
        except Exception as e:
            messagebox.showerror("Ошибка настройки", str(e), parent=self)

    def _calibrate_template_offset(self):
        template_key = self.current["template_key"]
        offset_key = self.current["offset_key"]

        loc = locate_image_on_screen(template_key, timeout=6)
        if not loc:
            raise RuntimeError(f"Не найден шаблон: {template_key}")

        self.withdraw()
        self.update()
        try:
            picked = pick_point_in_mis(self.master, f"Кликни правильную точку для {self.current['title']}")
        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

        if not picked:
            self._log("Изменение отменено")
            return

        picked_x, picked_y = picked
        dx = int(picked_x - loc.x)
        dy = int(picked_y - loc.y)

        self.data.setdefault("mis", {})
        self.data["mis"][offset_key] = [dx, dy]
        self._save_coords()
        self._render_current()

        self._log(
            f"SAVED {offset_key}: base=({loc.x},{loc.y}) picked=({picked_x},{picked_y}) offset=({dx},{dy})"
        )

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo("Сохранено", f"{offset_key} = [{dx}, {dy}]", parent=self)

    def _calibrate_absolute_point(self):
        point_key = self.current["point_key"]
        win = find_mis_window()

        self.withdraw()
        self.update()
        try:
            picked = pick_point_in_mis(self.master, f"Кликни правильную точку для {self.current['title']}")
        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

        if not picked:
            self._log("Изменение отменено")
            return

        picked_x, picked_y = picked
        rel_x = int(picked_x - win.left)
        rel_y = int(picked_y - win.top)

        self.data.setdefault("mis", {})
        self.data["mis"][point_key] = [rel_x, rel_y]
        self._save_coords()
        self._render_current()

        self._log(
            f"SAVED {point_key}: win=({win.left},{win.top}) picked=({picked_x},{picked_y}) rel=({rel_x},{rel_y})"
        )

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo("Сохранено", f"{point_key} = [{rel_x}, {rel_y}]", parent=self)
