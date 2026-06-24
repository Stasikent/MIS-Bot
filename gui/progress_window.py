import tkinter as tk
from tkinter import ttk


class ProgressWindow:
    def __init__(self, master, controller, total_count: int):
        self.controller = controller
        self.total_count = max(1, total_count)

        self.win = tk.Toplevel(master)
        self.win.title("Выполнение")
        self.win.geometry("430x210")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.status_var = tk.StringVar(value="Подготовка...")
        self.patient_var = tk.StringVar(value="Пациент: —")
        self.birth_var = tk.StringVar(value="Дата рождения: —")
        self.counter_var = tk.StringVar(value=f"0 / {self.total_count}")

        ttk.Label(self.win, text="Прогресс запуска", font=("Segoe UI", 11, "bold")).pack(pady=(10, 6))
        ttk.Label(self.win, textvariable=self.counter_var).pack()
        ttk.Label(self.win, textvariable=self.patient_var, wraplength=390).pack(pady=(8, 2))
        ttk.Label(self.win, textvariable=self.birth_var).pack(pady=(0, 8))
        ttk.Label(self.win, textvariable=self.status_var, foreground="blue").pack(pady=(0, 8))

        self.pb = ttk.Progressbar(self.win, mode="determinate", maximum=self.total_count, length=360)
        self.pb.pack(pady=(0, 12))

        btns = ttk.Frame(self.win)
        btns.pack()

        self.pause_btn = ttk.Button(btns, text="Пауза", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=6)

        self.cancel_btn = ttk.Button(btns, text="Отмена", command=self._on_cancel)
        self.cancel_btn.pack(side="left", padx=6)

        self.win.bind("<Caps_Lock>", lambda e: self.toggle_pause())
        self.win.bind("<Escape>", lambda e: self._on_cancel())

        self._tick()

    def _on_cancel(self):
        self.controller.cancel()

    def toggle_pause(self):
        self.controller.toggle_pause()
        self._refresh_pause_button()

    def _refresh_pause_button(self):
        if self.controller.is_paused:
            self.pause_btn.config(text="Продолжить")
        else:
            self.pause_btn.config(text="Пауза")

    def set_current(self, index: int, fio: str, birth_date: str, status_text: str = "Выполняется"):
        self.pb["value"] = index
        self.counter_var.set(f"{index} / {self.total_count}")
        self.patient_var.set(f"Пациент: {fio}")
        self.birth_var.set(f"Дата рождения: {birth_date}")
        self.status_var.set(status_text)
        self._refresh_pause_button()
        self.win.update_idletasks()

    def set_status(self, text: str):
        self.status_var.set(text)
        self._refresh_pause_button()
        self.win.update_idletasks()

    def finish(self, text: str = "Готово"):
        self.status_var.set(text)
        self._refresh_pause_button()
        self.win.update_idletasks()

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass

    def _tick(self):
        if not self.win.winfo_exists():
            return

        if self.controller.cancel_requested:
            self.status_var.set("Отмена запрошена")
        elif self.controller.is_paused:
            self.status_var.set("Пауза")
        self._refresh_pause_button()

        self.win.after(250, self._tick)