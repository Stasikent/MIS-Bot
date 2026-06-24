import tkinter as tk
from tkinter import ttk, messagebox

from gui.ui_helper import make_dialog_buttons


class XrayReviewDialog(tk.Toplevel):
    def __init__(self, master, task):
        super().__init__(master)

        self.title("Проверка рентген-протокола")
        self.geometry("980x760")
        self.minsize(900, 650)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self.task = task
        self.result = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self):
        # Главный контейнер:
        # content_area растягивается, footer с кнопками всегда остается снизу
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        content_area = ttk.Frame(root)
        content_area.pack(side="top", fill="both", expand=True)

        footer = ttk.Frame(root)
        footer.pack(side="bottom", fill="x")

        # Canvas + scrollbar для прокрутки содержимого
        canvas = tk.Canvas(content_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_area, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfigure(scroll_window, width=event.width)

        scroll_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ===== Верхние поля =====
        form = ttk.Frame(scroll_frame)
        form.pack(fill="x", padx=10, pady=10)

        self.fio_var = tk.StringVar(value=self.task.fio)
        self.birth_var = tk.StringVar(value=self.task.birth_date)
        self.study_date_var = tk.StringVar(value=self.task.study_date)
        self.study_name_var = tk.StringVar(value=self.task.study_name)
        self.dose_var = tk.StringVar(value=self.task.dose)
        self.template_name_var = tk.StringVar(value=self.task.template_name)
        self.template_key_var = tk.StringVar(value=self.task.template_key)

        ttk.Label(form, text="ФИО").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.fio_var).grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="Дата рождения").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.birth_var, width=20).grid(row=1, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(form, text="Дата исследования").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.study_date_var, width=20).grid(row=2, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(form, text="Исследование").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.study_name_var).grid(row=3, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="Доза").grid(row=4, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.dose_var, width=20).grid(row=4, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(form, text="Шаблон").grid(row=5, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.template_name_var).grid(row=5, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(form, text="Template key").grid(row=6, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.template_key_var).grid(row=6, column=1, sticky="we", padx=6, pady=4)

        form.columnconfigure(1, weight=1)

        # ===== Описание / Заключение =====
        body = ttk.Frame(scroll_frame)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        ttk.Label(body, text="Описание").pack(anchor="w")
        self.description_text = tk.Text(body, wrap="word", height=14)
        self.description_text.pack(fill="both", expand=True, pady=(2, 10))
        self.description_text.insert("1.0", self.task.description or "")

        ttk.Label(body, text="Заключение").pack(anchor="w")
        self.conclusion_text = tk.Text(body, wrap="word", height=8)
        self.conclusion_text.pack(fill="both", expand=True, pady=(2, 10))
        self.conclusion_text.insert("1.0", self.task.conclusion or "")

        raw_frame = ttk.LabelFrame(scroll_frame, text="Исходный текст")
        raw_frame.pack(fill="both", expand=False, padx=10, pady=(0, 8))

        self.raw_text = tk.Text(raw_frame, wrap="word", height=7)
        self.raw_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.raw_text.insert("1.0", self.task.raw_text or "")
        self.raw_text.configure(state="disabled")

        # ===== Footer: кнопки всегда видны =====
        ttk.Separator(footer).pack(fill="x", pady=(0, 6))

        make_dialog_buttons(
            parent=footer,
            ok_text="Сохранить",
            ok_command=self._on_save,
            cancel_text="Отмена",
            cancel_command=self._on_cancel,
            padx=10,
            pady=(0, 10),
            button_width=16,
        )

    def _on_save(self):
        fio = self.fio_var.get().strip()
        birth_date = self.birth_var.get().strip()
        study_date = self.study_date_var.get().strip()
        study_name = self.study_name_var.get().strip()
        dose = self.dose_var.get().strip()
        template_name = self.template_name_var.get().strip()
        template_key = self.template_key_var.get().strip()
        description = self.description_text.get("1.0", "end").strip()
        conclusion = self.conclusion_text.get("1.0", "end").strip()

        if not fio:
            messagebox.showerror("Ошибка", "Укажите ФИО", parent=self)
            return

        if not birth_date:
            messagebox.showerror("Ошибка", "Укажите дату рождения", parent=self)
            return

        if not study_date:
            messagebox.showerror("Ошибка", "Укажите дату исследования", parent=self)
            return

        if not study_name:
            messagebox.showerror("Ошибка", "Укажите исследование", parent=self)
            return

        self.task.fio = fio
        self.task.birth_date = birth_date
        self.task.study_date = study_date
        self.task.study_name = study_name
        self.task.dose = dose
        self.task.description = description
        self.task.conclusion = conclusion
        self.task.template_name = template_name
        self.task.template_key = template_key
        self.task.task_type = "xray"
        self.task.mode = "xray"

        if template_name:
            self.task.note = f"Шаблон: {template_name}"

        if self.task.status == "pending_fix":
            self.task.status = "pending"
            self.task.note = ""

        self.result = self.task
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()