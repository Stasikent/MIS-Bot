import tkinter as tk
from tkinter import ttk

from services.preflight_checks import (
    run_mis_preflight,
    run_ris_preflight,
    run_open_card_preflight,
    PreflightResult,
)


class PreflightWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Предполетная проверка")
        self.geometry("860x520")
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(
            root,
            text="Проверка готовности режимов",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(12, 10))

        ttk.Button(btns, text="Проверить МИС", command=self._check_mis).pack(side="left")
        ttk.Button(btns, text="Проверить РИС", command=self._check_ris).pack(side="left", padx=8)
        ttk.Button(btns, text="Проверить открытую карточку", command=self._check_open_card).pack(side="left")
        ttk.Button(btns, text="Закрыть", command=self.destroy).pack(side="right")

        self.result_label = ttk.Label(root, text="", font=("Segoe UI", 10, "bold"))
        self.result_label.pack(anchor="w", pady=(0, 10))

        self.text = tk.Text(root, wrap="word")
        self.text.pack(fill="both", expand=True)

    def _render_result(self, result: PreflightResult):
        self.text.delete("1.0", "end")

        status = "ГОТОВО" if result.ok else "НЕ ГОТОВО"
        self.result_label.config(text=f"{result.title}: {status}")

        self.text.insert("end", f"{result.title}\n")
        self.text.insert("end", f"Итог: {status}\n\n")

        for item in result.items:
            mark = "OK" if item.ok else "FAIL"
            self.text.insert("end", f"[{mark}] {item.name}\n")
            if item.details:
                self.text.insert("end", f"    {item.details}\n")
            self.text.insert("end", "\n")

        self.text.see("1.0")

    def _check_mis(self):
        self._render_result(run_mis_preflight())

    def _check_ris(self):
        self._render_result(run_ris_preflight())

    def _check_open_card(self):
        self._render_result(run_open_card_preflight())