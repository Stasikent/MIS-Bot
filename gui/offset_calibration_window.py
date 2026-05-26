import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from gui.screen_pick_overlay import pick_screen_point
from project.bot_mode1_current import find_mis_window, locate_image_on_screen


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "coordinates.json"


OFFSET_TARGETS = {
    "diagnosis_code_offset": {
        "template_key": "diagnosis_code",
        "title": "Калибровка diagnosis_code_offset",
        "description": "Будет найден шаблон diagnosis_code, затем кликни по правильной точке для нажатия.",
    },
    "diagnosis_cancel_item_offset": {
        "template_key": "diagnosis_cancel_item",
        "title": "Калибровка diagnosis_cancel_item_offset",
        "description": "Будет найден шаблон diagnosis_cancel_item, затем кликни по правильной точке для нажатия.",
    },
}


class OffsetCalibrationWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Калибровка offset")
        self.geometry("760x420")
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self.data = self._load_data()

        self.target_var = tk.StringVar(value="diagnosis_code_offset")
        self.last_base = None
        self.last_final = None

        self._build_ui()
        self._refresh_info()

    def _load_data(self) -> dict:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Калибровка offset от найденного шаблона", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        top = ttk.Frame(root)
        top.pack(fill="x", pady=(12, 10))

        ttk.Label(top, text="Параметр:").pack(side="left")

        combo = ttk.Combobox(
            top,
            textvariable=self.target_var,
            values=list(OFFSET_TARGETS.keys()),
            state="readonly",
            width=32,
        )
        combo.pack(side="left", padx=(8, 0))
        combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_info())

        self.desc_label = ttk.Label(root, text="", wraplength=700, justify="left")
        self.desc_label.pack(anchor="w", pady=(4, 10))

        self.current_label = ttk.Label(root, text="", justify="left", foreground="#444444")
        self.current_label.pack(anchor="w", pady=(0, 10))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(4, 10))

        ttk.Button(btns, text="Найти шаблон и откалибровать", command=self.calibrate).pack(side="left")
        ttk.Button(btns, text="Обновить", command=self._reload).pack(side="left", padx=8)
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right")

        self.log_text = tk.Text(root, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def _log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _refresh_info(self):
        key = self.target_var.get()
        item = OFFSET_TARGETS[key]
        self.desc_label.config(text=item["description"])

        current = self.data.get("mis", {}).get(key, [0, 0])
        self.current_label.config(text=f"Текущее значение mis.{key} = {current}")

    def _reload(self):
        self.data = self._load_data()
        self._refresh_info()
        self._log("coordinates.json перечитан с диска")

    def calibrate(self):
        key = self.target_var.get()
        item = OFFSET_TARGETS[key]
        template_key = item["template_key"]

        confirm = messagebox.askyesno(
            item["title"],
            f"Убедись, что нужное окно открыто.\n\n"
            f"Сейчас бот попробует найти шаблон '{template_key}', "
            f"после этого ты кликнешь правильную точку.",
            parent=self,
        )
        if not confirm:
            return

        self.withdraw()
        self.update()

        try:
            win = find_mis_window()
            loc = locate_image_on_screen(template_key, timeout=6)

            if not loc:
                raise RuntimeError(f"Шаблон '{template_key}' не найден на экране.")

            base_x, base_y = loc.x, loc.y
            self.last_base = (base_x, base_y)

            self.deiconify()
            self.lift()
            self.focus_force()

            messagebox.showinfo(
                item["title"],
                f"Базовая точка найдена: ({base_x}, {base_y}).\n\n"
                f"Сейчас кликни по ПРАВИЛЬНОЙ точке на экране.",
                parent=self,
            )

            self.withdraw()
            self.update()

            picked = pick_screen_point(self.master)
            if picked is None:
                raise RuntimeError("Калибровка отменена.")

            final_x, final_y = picked
            self.last_final = (final_x, final_y)

            dx = int(final_x - base_x)
            dy = int(final_y - base_y)

            self.data.setdefault("mis", {})
            self.data["mis"][key] = [dx, dy]
            self._save_data()

        except Exception as e:
            self.deiconify()
            self.lift()
            self.focus_force()
            messagebox.showerror("Ошибка калибровки", str(e), parent=self)
            return

        self.deiconify()
        self.lift()
        self.focus_force()
        self._refresh_info()

        self._log(f"{key}: base={self.last_base} final={self.last_final} offset=({dx}, {dy})")

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo(
            "Готово",
            f"mis.{key} сохранён как [{dx}, {dy}]",
            parent=self,
        )