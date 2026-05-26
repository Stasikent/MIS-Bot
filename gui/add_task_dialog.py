import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from models.patient_task import PatientTask
from services.mode_mapper import UI_MODE_TO_INTERNAL


class AddTaskDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Добавить запись")
        self.resizable(False, False)
        self.result = None

        self.transient(master)
        self.grab_set()

        self.fio_var = tk.StringVar()
        self.birth_var = tk.StringVar()
        self.study_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))
        self.mode_var = tk.StringVar(value="Норма")
        self.note_var = tk.StringVar()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        ttk.Label(self, text="ФИО").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.fio_var, width=45).grid(row=0, column=1, **pad)

        ttk.Label(self, text="Дата рождения").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.birth_var, width=20).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Дата исследования").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.study_var, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="Протокол").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(
            self,
            textvariable=self.mode_var,
            values=list(UI_MODE_TO_INTERNAL.keys()),
            state="readonly",
            width=25
        ).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(self, text="Примечание").grid(row=4, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.note_var, width=45).grid(row=4, column=1, **pad)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=self._on_save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self._on_cancel).pack(side="left", padx=5)

    def _on_save(self):
        fio = self.fio_var.get().strip()
        birth = self.birth_var.get().strip()
        study = self.study_var.get().strip()
        ui_mode = self.mode_var.get().strip()
        note = self.note_var.get().strip() or None

        if not fio:
            messagebox.showerror("Ошибка", "Укажи ФИО")
            return

        if not birth:
            messagebox.showerror("Ошибка", "Укажи дату рождения")
            return

        if not study:
            messagebox.showerror("Ошибка", "Укажи дату исследования")
            return

        self.result = PatientTask(
            fio=fio,
            birth_date=birth,
            study_date=study,
            mode=UI_MODE_TO_INTERNAL[ui_mode],
            note=note,
            source="manual"
        )
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()