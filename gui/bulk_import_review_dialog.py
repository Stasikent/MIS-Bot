import tkinter as tk
from tkinter import ttk, messagebox

from services.mode_mapper import UI_MODE_TO_INTERNAL, INTERNAL_TO_UI_MODE


class BulkImportReviewDialog(tk.Toplevel):
    def __init__(self, master, tasks):
        super().__init__(master)
        self.title("Проверка распознанных пациентов")
        self.geometry("980x520")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self.tasks = tasks
        self.result = None

        self.bulk_mode_var = tk.StringVar(value="Норма")

        self._build_ui()
        self._fill_table()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(top, text="Шаблон для всех:").pack(side="left")
        self.bulk_mode_combo = ttk.Combobox(
            top,
            textvariable=self.bulk_mode_var,
            values=list(UI_MODE_TO_INTERNAL.keys()),
            state="readonly",
            width=18,
        )
        self.bulk_mode_combo.pack(side="left", padx=6)

        ttk.Button(top, text="Применить ко всем", command=self._apply_mode_to_all).pack(side="left", padx=6)
        ttk.Button(top, text="Удалить выбранную строку", command=self._delete_selected_row).pack(side="left", padx=12)

        cols = ("fio", "birth_date", "study_date", "mode", "note")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree.heading("fio", text="ФИО")
        self.tree.heading("birth_date", text="Дата рождения")
        self.tree.heading("study_date", text="Дата исследования")
        self.tree.heading("mode", text="Шаблон")
        self.tree.heading("note", text="Примечание")

        self.tree.column("fio", width=320)
        self.tree.column("birth_date", width=120, anchor="center")
        self.tree.column("study_date", width=120, anchor="center")
        self.tree.column("mode", width=130, anchor="center")
        self.tree.column("note", width=220)

        self.tree.bind("<Double-1>", self._edit_selected_row)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=(0, 8))

        ttk.Button(bottom, text="Изменить выбранную", command=self._edit_selected_row).pack(side="left")
        ttk.Button(bottom, text="Отмена", command=self._on_cancel).pack(side="right", padx=6)
        ttk.Button(bottom, text="Добавить в список", command=self._on_save).pack(side="right")

    def _fill_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, task in enumerate(self.tasks):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    task.fio,
                    task.birth_date,
                    getattr(task, "study_date", "") or "",
                    INTERNAL_TO_UI_MODE.get(task.mode, task.mode),
                    task.note or "",
                ),
            )

    def _get_selected_index(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _apply_mode_to_all(self):
        ui_mode = self.bulk_mode_var.get().strip()
        if not ui_mode:
            return

        internal_mode = UI_MODE_TO_INTERNAL[ui_mode]
        for task in self.tasks:
            task.mode = internal_mode

        self._fill_table()

    def _delete_selected_row(self):
        idx = self._get_selected_index()
        if idx is None:
            messagebox.showinfo("Информация", "Выбери строку")
            return

        del self.tasks[idx]
        self._fill_table()

    def _edit_selected_row(self, event=None):
        idx = self._get_selected_index()
        if idx is None:
            messagebox.showinfo("Информация", "Выбери строку")
            return

        task = self.tasks[idx]

        edit_win = tk.Toplevel(self)
        edit_win.title("Редактировать запись")
        edit_win.geometry("520x240")
        edit_win.transient(self)
        edit_win.grab_set()
        edit_win.attributes("-topmost", True)

        fio_var = tk.StringVar(value=task.fio)
        birth_var = tk.StringVar(value=task.birth_date)
        study_var = tk.StringVar(value=getattr(task, "study_date", "") or "")
        mode_var = tk.StringVar(value=INTERNAL_TO_UI_MODE.get(task.mode, task.mode))
        note_var = tk.StringVar(value=task.note or "")

        pad = {"padx": 8, "pady": 6}

        ttk.Label(edit_win, text="ФИО").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(edit_win, textvariable=fio_var, width=42).grid(row=0, column=1, **pad)

        ttk.Label(edit_win, text="Дата рождения").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(edit_win, textvariable=birth_var, width=20).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(edit_win, text="Дата исследования").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(edit_win, textvariable=study_var, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(edit_win, text="Шаблон").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(
            edit_win,
            textvariable=mode_var,
            values=list(UI_MODE_TO_INTERNAL.keys()),
            state="readonly",
            width=18
        ).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(edit_win, text="Примечание").grid(row=4, column=0, sticky="w", **pad)
        ttk.Entry(edit_win, textvariable=note_var, width=42).grid(row=4, column=1, **pad)

        def save_changes():
            fio = fio_var.get().strip()
            birth = birth_var.get().strip()
            study = study_var.get().strip()
            ui_mode = mode_var.get().strip()

            if not fio:
                messagebox.showerror("Ошибка", "Укажи ФИО", parent=edit_win)
                return
            if not birth:
                messagebox.showerror("Ошибка", "Укажи дату рождения", parent=edit_win)
                return
            if not study:
                messagebox.showerror("Ошибка", "Укажи дату исследования", parent=edit_win)
                return

            task.fio = fio
            task.birth_date = birth
            task.study_date = study
            task.mode = UI_MODE_TO_INTERNAL[ui_mode]
            task.note = note_var.get().strip() or None

            edit_win.destroy()
            self._fill_table()

        btns = ttk.Frame(edit_win)
        btns.grid(row=5, column=0, columnspan=2, pady=12)

        ttk.Button(btns, text="Сохранить", command=save_changes).pack(side="left", padx=6)
        ttk.Button(btns, text="Отмена", command=edit_win.destroy).pack(side="left", padx=6)

    def _on_save(self):
        if not self.tasks:
            messagebox.showwarning("Пусто", "Нет записей для добавления")
            return

        self.result = self.tasks
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()