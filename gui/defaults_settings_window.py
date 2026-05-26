import shutil
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
PROJECT_DIR = ROOT_DIR / "project"
TEMPLATES_DIR = PROJECT_DIR / "templates"

DEFAULTS_DIR = CONFIG_DIR / "defaults"
DEFAULTS_CONFIG_DIR = DEFAULTS_DIR / "config"
DEFAULTS_TEMPLATES_DIR = DEFAULTS_DIR / "templates"


class DefaultsSettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Default-настройки")
        self.geometry("760x420")
        self.transient(parent)
        self.grab_set()

        self.on_saved = on_saved

        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="Управление default-настройками", font=("Segoe UI", 12, "bold"))
        title.pack(anchor="w")

        desc = (
            "Сохранить как default:\n"
            "- сохраняет текущие config/*.json\n"
            "- сохраняет текущие project/templates/*\n\n"
            "Восстановить default:\n"
            "- возвращает config/*.json из defaults\n"
            "- возвращает project/templates/* из defaults"
        )
        ttk.Label(root, text=desc, justify="left").pack(anchor="w", pady=(10, 14))

        self.status_label = ttk.Label(root, text="", justify="left", foreground="#444444")
        self.status_label.pack(anchor="w", pady=(0, 14))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(8, 0))

        ttk.Button(btns, text="Сохранить как default", command=self.save_as_default).pack(side="left")
        ttk.Button(btns, text="Восстановить default", command=self.restore_default).pack(side="left", padx=8)
        ttk.Button(btns, text="Обновить статус", command=self._refresh_status).pack(side="left")
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right")

        self.log_text = tk.Text(root, height=10, wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=(14, 0))

    def _log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def _copy_tree_clean(self, src: Path, dst: Path):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    def _copy_json_files(self, src_dir: Path, dst_dir: Path):
        dst_dir.mkdir(parents=True, exist_ok=True)
        for path in src_dir.glob("*.json"):
            shutil.copy2(path, dst_dir / path.name)

    def _refresh_status(self):
        config_ok = DEFAULTS_CONFIG_DIR.exists()
        templates_ok = DEFAULTS_TEMPLATES_DIR.exists()

        cfg_files = sorted(p.name for p in DEFAULTS_CONFIG_DIR.glob("*.json")) if config_ok else []
        tmpl_count = len(list(DEFAULTS_TEMPLATES_DIR.glob("*"))) if templates_ok else 0

        status = [
            f"Папка default config: {'есть' if config_ok else 'нет'}",
            f"Файлы default config: {', '.join(cfg_files) if cfg_files else '-'}",
            f"Папка default templates: {'есть' if templates_ok else 'нет'}",
            f"Файлов шаблонов в default: {tmpl_count}",
        ]
        self.status_label.config(text="\n".join(status))

    def save_as_default(self):
        confirm = messagebox.askyesno(
            "Подтверждение",
            "Сохранить текущие настройки и шаблоны как default?",
            parent=self,
        )
        if not confirm:
            return

        try:
            DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)

            self._copy_json_files(CONFIG_DIR, DEFAULTS_CONFIG_DIR)
            self._copy_tree_clean(TEMPLATES_DIR, DEFAULTS_TEMPLATES_DIR)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log(f"[{ts}] Default сохранён")
            self._log(f"Config -> {DEFAULTS_CONFIG_DIR}")
            self._log(f"Templates -> {DEFAULTS_TEMPLATES_DIR}")

            self._refresh_status()

            if self.on_saved:
                self.on_saved()

            messagebox.showinfo("Готово", "Текущие настройки сохранены как default.", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def restore_default(self):
        if not DEFAULTS_CONFIG_DIR.exists() or not DEFAULTS_TEMPLATES_DIR.exists():
            messagebox.showerror(
                "Ошибка",
                "Default-настройки ещё не сохранены.",
                parent=self,
            )
            return

        confirm = messagebox.askyesno(
            "Подтверждение",
            "Восстановить настройки и шаблоны из default?\nТекущие значения будут заменены.",
            parent=self,
        )
        if not confirm:
            return

        try:
            self._copy_json_files(DEFAULTS_CONFIG_DIR, CONFIG_DIR)
            self._copy_tree_clean(DEFAULTS_TEMPLATES_DIR, TEMPLATES_DIR)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log(f"[{ts}] Default восстановлен")
            self._log(f"Config <- {DEFAULTS_CONFIG_DIR}")
            self._log(f"Templates <- {DEFAULTS_TEMPLATES_DIR}")

            self._refresh_status()

            if self.on_saved:
                self.on_saved()

            messagebox.showinfo("Готово", "Default-настройки восстановлены.", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)