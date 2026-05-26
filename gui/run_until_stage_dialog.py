import tkinter as tk
from tkinter import ttk


FULL_STAGES = [
    ("after_search", "После поиска пациента"),
    ("after_open_visit", "После открытия приема"),
    ("after_fill_basic", "После заполнения повода и цели"),
    ("after_service", "После выбора услуги"),
    ("after_protocol", "После открытия протокола"),
    ("after_template_date", "После шаблона и ввода даты"),
    ("after_cancel_diagnosis", "После отмены диагноза"),
]

OPEN_CARD_STAGES = [
    ("after_fill_basic", "После заполнения повода и цели"),
    ("after_service", "После выбора услуги"),
    ("after_protocol", "После открытия протокола"),
    ("after_template_date", "После шаблона и ввода даты"),
    ("after_cancel_diagnosis", "После отмены диагноза"),
]


class RunUntilStageDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Запуск до этапа")
        self.geometry("520x220")
        self.transient(parent)
        self.grab_set()

        self.result = None

        self.scenario_var = tk.StringVar(value="full")
        self.stage_var = tk.StringVar()

        self._build_ui()
        self._refresh_stage_values()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Сценарий:").pack(anchor="w")
        scenario_box = ttk.Combobox(
            root,
            textvariable=self.scenario_var,
            state="readonly",
            values=[
                "full",
                "open_card",
            ],
            width=30,
        )
        scenario_box.pack(anchor="w", pady=(4, 12))
        scenario_box.bind("<<ComboboxSelected>>", lambda e: self._refresh_stage_values())

        ttk.Label(root, text="Остановиться на этапе:").pack(anchor="w")
        self.stage_box = ttk.Combobox(
            root,
            textvariable=self.stage_var,
            state="readonly",
            width=50,
        )
        self.stage_box.pack(anchor="w", pady=(4, 12))

        hint = (
            "full — полный сценарий\n"
            "open_card — сценарий из уже открытой карточки"
        )
        ttk.Label(root, text=hint, foreground="#555555", justify="left").pack(anchor="w", pady=(0, 12))

        btns = ttk.Frame(root)
        btns.pack(fill="x")

        ttk.Button(btns, text="Запустить", command=self._on_ok).pack(side="left")
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right")

    def _refresh_stage_values(self):
        scenario = self.scenario_var.get()
        items = FULL_STAGES if scenario == "full" else OPEN_CARD_STAGES

        labels = [label for _, label in items]
        self.stage_box["values"] = labels

        if labels:
            self.stage_box.current(0)

    def _on_ok(self):
        scenario = self.scenario_var.get()
        items = FULL_STAGES if scenario == "full" else OPEN_CARD_STAGES

        selected_label = self.stage_var.get()
        selected_key = None

        for key, label in items:
            if label == selected_label:
                selected_key = key
                break

        if not selected_key:
            return

        self.result = {
            "scenario": scenario,
            "stop_stage": selected_key,
            "stop_label": selected_label,
        }
        self.destroy()