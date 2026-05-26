import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from gui.screen_pick_overlay import pick_screen_point, pick_screen_rect


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "coordinates.json"


FIELD_DESCRIPTIONS = {
    ("mis", "search_anchor_x_offset"): "Смещение влево от якоря поиска до поля ввода ФИО.",
    ("mis", "dob_region"): "Область даты рождения в списке пациентов МИС: x, y, width, height.",
    ("mis", "dob_click_point"): "Точка клика по найденной строке пациента: x, y.",
    ("mis", "row_height"): "Высота одной строки пациента в списке.",
    ("mis", "max_patient_rows"): "Максимум строк для проверки OCR.",
    ("mis", "work_plus_fallback_point"): "Запасная точка клика по плюсу услуг: x, y.",
    ("mis", "diagnosis_code_offset"): "Offset клика по diagnosis_code относительно найденного шаблона: dx, dy.",
    ("mis", "diagnosis_cancel_item_offset"): "Offset клика по пункту 'Отменить' относительно найденного шаблона: dx, dy.",

    ("ris", "search_button_to_field_offset"): "Offset от кнопки поиска до поля ввода в РИС: dx, dy.",
    ("ris", "patient_card_region_offset"): "Область OCR карточки пациента относительно якоря карточки: left, top, width, height.",
    ("ris", "birth_region_inside_card"): "Область даты рождения внутри OCR-карточки: left, top, width, height.",
    ("ris", "debug_card_region"): "Отладочная область карточки на полном скриншоте: left, top, width, height.",
}


class CoordinatesSettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Настройки координат")
        self.geometry("980x620")
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self.data = self._load_data()
        self.current_section = "mis"
        self.current_key = None
        self.entry_vars = []

        self._build_ui()
        self._fill_keys()
        self._select_first_key()

    def _load_data(self) -> dict:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        left = ttk.Frame(root)
        left.pack(side="left", fill="y")

        center = ttk.Frame(root)
        center.pack(side="left", fill="both", expand=True, padx=(12, 0))

        top_bar = ttk.Frame(left)
        top_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(top_bar, text="Секция:").pack(side="left")
        self.section_var = tk.StringVar(value="mis")
        section_box = ttk.Combobox(
            top_bar,
            textvariable=self.section_var,
            values=["mis", "ris"],
            state="readonly",
            width=10,
        )
        section_box.pack(side="left", padx=(6, 0))
        section_box.bind("<<ComboboxSelected>>", self._on_section_changed)

        self.keys_list = tk.Listbox(left, width=34, height=28, exportselection=False)
        self.keys_list.pack(fill="y", expand=True)
        self.keys_list.bind("<<ListboxSelect>>", self._on_key_selected)

        self.title_label = ttk.Label(center, text="Параметр", font=("Segoe UI", 11, "bold"))
        self.title_label.pack(anchor="w")

        self.desc_label = ttk.Label(center, text="", wraplength=580, justify="left")
        self.desc_label.pack(anchor="w", pady=(6, 12))

        self.form_frame = ttk.Frame(center)
        self.form_frame.pack(fill="x", pady=(0, 10))

        btns = ttk.Frame(center)
        btns.pack(fill="x", pady=(8, 0))

        ttk.Button(btns, text="Считать с экрана", command=self._capture_from_screen).pack(side="left")
        ttk.Button(btns, text="Сохранить", command=self._save_current).pack(side="left", padx=6)
        ttk.Button(btns, text="Обновить из файла", command=self._reload_from_disk).pack(side="left")
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right")

        hint = (
            "Для x,y или dx,dy берётся одна точка.\n"
            "Для region/offset-областей выделяется прямоугольник на экране.\n"
            "Если это offset, после захвата может понадобиться вручную скорректировать числа."
        )
        ttk.Label(center, text=hint, foreground="#555555", justify="left").pack(anchor="w", pady=(14, 0))

    def _fill_keys(self):
        self.keys_list.delete(0, "end")
        section = self.section_var.get()
        keys = list(self.data.get(section, {}).keys())
        for key in keys:
            self.keys_list.insert("end", key)

    def _select_first_key(self):
        if self.keys_list.size() > 0:
            self.keys_list.selection_clear(0, "end")
            self.keys_list.selection_set(0)
            self.keys_list.event_generate("<<ListboxSelect>>")

    def _on_section_changed(self, _event=None):
        self.current_section = self.section_var.get()
        self._fill_keys()
        self._select_first_key()

    def _on_key_selected(self, _event=None):
        sel = self.keys_list.curselection()
        if not sel:
            return
        key = self.keys_list.get(sel[0])
        self.current_key = key
        self._render_current_key()

    def _clear_form(self):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.entry_vars.clear()

    def _render_current_key(self):
        self._clear_form()

        section = self.section_var.get()
        key = self.current_key
        value = self.data[section][key]

        self.title_label.config(text=f"{section}.{key}")
        self.desc_label.config(text=FIELD_DESCRIPTIONS.get((section, key), "Описание не задано."))

        if isinstance(value, list):
            for i, item in enumerate(value):
                row = ttk.Frame(self.form_frame)
                row.pack(fill="x", pady=3)

                ttk.Label(row, text=f"[{i}]", width=10).pack(side="left")
                var = tk.StringVar(value=str(item))
                entry = ttk.Entry(row, textvariable=var, width=18)
                entry.pack(side="left")
                self.entry_vars.append(var)

        elif isinstance(value, dict):
            for sub_key, sub_val in value.items():
                row = ttk.Frame(self.form_frame)
                row.pack(fill="x", pady=3)

                ttk.Label(row, text=sub_key, width=14).pack(side="left")
                var = tk.StringVar(value=str(sub_val))
                entry = ttk.Entry(row, textvariable=var, width=18)
                entry.pack(side="left")
                self.entry_vars.append((sub_key, var))

        else:
            row = ttk.Frame(self.form_frame)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text="value", width=14).pack(side="left")
            var = tk.StringVar(value=str(value))
            entry = ttk.Entry(row, textvariable=var, width=18)
            entry.pack(side="left")
            self.entry_vars.append(var)

    def _parse_current_form_value(self):
        section = self.section_var.get()
        key = self.current_key
        old_value = self.data[section][key]

        try:
            if isinstance(old_value, list):
                return [int(v.get()) for v in self.entry_vars]

            if isinstance(old_value, dict):
                result = {}
                for sub_key, var in self.entry_vars:
                    result[sub_key] = int(var.get())
                return result

            return int(self.entry_vars[0].get())
        except ValueError:
            raise ValueError("Все значения должны быть целыми числами.")

    def _save_current(self):
        if not self.current_key:
            return

        try:
            new_value = self._parse_current_form_value()
            self.data[self.section_var.get()][self.current_key] = new_value
            self._save_data()
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e), parent=self)
            return

        messagebox.showinfo(
            "Сохранено",
            f"Параметр {self.section_var.get()}.{self.current_key} сохранён.",
            parent=self,
        )

        if self.on_saved:
            self.on_saved()

    def _reload_from_disk(self):
        self.data = self._load_data()
        self._render_current_key()
        if self.on_saved:
            self.on_saved()

    def _capture_from_screen(self):
        if not self.current_key:
            return

        section = self.section_var.get()
        key = self.current_key
        current_value = self.data[section][key]

        self.withdraw()
        self.update()

        try:
            if isinstance(current_value, list) and len(current_value) == 2:
                result = pick_screen_point(self.master)
                if result is None:
                    raise RuntimeError("Захват отменён.")
                x, y = result
                self.data[section][key] = [int(x), int(y)]

            elif isinstance(current_value, list) and len(current_value) == 4:
                result = pick_screen_rect(self.master)
                if result is None:
                    raise RuntimeError("Захват отменён.")
                left, top, width, height = result
                self.data[section][key] = [int(left), int(top), int(width), int(height)]

            elif isinstance(current_value, dict):
                result = pick_screen_rect(self.master)
                if result is None:
                    raise RuntimeError("Захват отменён.")

                left, top, width, height = result
                keys = list(current_value.keys())

                if keys == ["left", "top", "width", "height"]:
                    self.data[section][key] = {
                        "left": int(left),
                        "top": int(top),
                        "width": int(width),
                        "height": int(height),
                    }
                else:
                    self.data[section][key] = {
                        keys[0]: int(left),
                        keys[1]: int(top),
                        keys[2]: int(width),
                        keys[3]: int(height),
                    }
            else:
                raise ValueError("Автозахват для этого типа параметра не поддержан.")

            self._save_data()

        except Exception as e:
            self.deiconify()
            self.lift()
            self.focus_force()
            messagebox.showerror("Ошибка захвата", str(e), parent=self)
            return

        self.deiconify()
        self.lift()
        self.focus_force()
        self._render_current_key()

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo(
            "Готово",
            f"Параметр {section}.{key} считан с экрана и сохранён.",
            parent=self,
        )