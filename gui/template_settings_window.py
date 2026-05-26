import json
import shutil
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from gui.screen_pick_overlay import pick_screen_rect
from PIL import ImageGrab


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "templates.json"
PROJECT_DIR = Path(__file__).resolve().parents[1] / "project"
TEMPLATES_DIR = PROJECT_DIR / "templates"


class TemplateSettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Настройки шаблонов")
        self.geometry("980x620")
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved
        self.data = self._load_data()
        self.current_section = "mis"
        self.current_key = None

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

        self.title_label = ttk.Label(center, text="Шаблон", font=("Segoe UI", 11, "bold"))
        self.title_label.pack(anchor="w")

        self.desc_label = ttk.Label(center, text="", wraplength=580, justify="left")
        self.desc_label.pack(anchor="w", pady=(6, 12))

        info = ttk.Frame(center)
        info.pack(fill="x", pady=(0, 12))

        ttk.Label(info, text="Файл:", width=12).grid(row=0, column=0, sticky="w")
        self.file_var = tk.StringVar()
        ttk.Entry(info, textvariable=self.file_var, width=48).grid(row=0, column=1, sticky="w", padx=(0, 8))

        ttk.Label(info, text="Confidence:", width=12).grid(row=1, column=0, sticky="w")
        self.conf_var = tk.StringVar()
        ttk.Entry(info, textvariable=self.conf_var, width=12).grid(row=1, column=1, sticky="w")

        self.path_label = ttk.Label(center, text="", wraplength=620, justify="left", foreground="#555555")
        self.path_label.pack(anchor="w", pady=(0, 10))

        btns = ttk.Frame(center)
        btns.pack(fill="x", pady=(8, 0))

        ttk.Button(btns, text="Заменить шаблон", command=self._replace_template).pack(side="left")
        ttk.Button(btns, text="Сохранить метаданные", command=self._save_metadata).pack(side="left", padx=6)
        ttk.Button(btns, text="Обновить из файла", command=self._reload_from_disk).pack(side="left")
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right")

        hint = (
            "Кнопка 'Заменить шаблон' открывает полноэкранный режим выделения.\n"
            "Старый PNG будет сохранён как backup с датой и временем."
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
        self.current_key = self.keys_list.get(sel[0])
        self._render_current()

    def _render_current(self):
        section = self.section_var.get()
        key = self.current_key
        item = self.data[section][key]

        self.title_label.config(text=f"{section}.{key}")
        self.desc_label.config(text=item.get("description", ""))
        self.file_var.set(item.get("file", ""))
        self.conf_var.set(str(item.get("confidence", 0.8)))

        path = TEMPLATES_DIR / item.get("file", "")
        self.path_label.config(text=f"Путь: {path}")

    def _reload_from_disk(self):
        self.data = self._load_data()
        self._render_current()
        if self.on_saved:
            self.on_saved()

    def _save_metadata(self):
        if not self.current_key:
            return

        section = self.section_var.get()
        key = self.current_key

        try:
            self.data[section][key]["file"] = self.file_var.get().strip()
            self.data[section][key]["confidence"] = float(self.conf_var.get().strip())
            self._save_data()
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e), parent=self)
            return

        self._render_current()

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo("Сохранено", f"Метаданные {section}.{key} сохранены.", parent=self)

    def _backup_existing(self, path: Path):
        if not path.exists():
            return None

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_name(f"{path.stem}_old_{ts}{path.suffix}")
        shutil.copy2(path, backup_path)
        return backup_path

    def _replace_template(self):
        if not self.current_key:
            return

        section = self.section_var.get()
        key = self.current_key
        file_name = self.file_var.get().strip()

        if not file_name:
            messagebox.showerror("Ошибка", "Не задано имя файла шаблона.", parent=self)
            return

        target_path = TEMPLATES_DIR / file_name

        self.withdraw()
        self.update()

        try:
            rect = pick_screen_rect(self.master)
            if rect is None:
                raise RuntimeError("Выделение отменено.")

            left, top, width, height = rect
            if width <= 1 or height <= 1:
                raise RuntimeError("Слишком маленькая область.")

            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))

            TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
            backup_path = self._backup_existing(target_path)
            screenshot.save(target_path)

        except Exception as e:
            self.deiconify()
            self.lift()
            self.focus_force()
            messagebox.showerror("Ошибка замены шаблона", str(e), parent=self)
            return

        self.deiconify()
        self.lift()
        self.focus_force()

        msg = f"Шаблон {section}.{key} обновлён:\n{target_path}"
        if backup_path:
            msg += f"\n\nBackup:\n{backup_path}"

        if self.on_saved:
            self.on_saved()

        messagebox.showinfo("Готово", msg, parent=self)