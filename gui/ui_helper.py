import tkinter as tk


def _show_window(title, message, buttons):
    result = {"value": None}

    root = tk.Tk()
    root.title(title)
    root.geometry("520x220")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    lbl = tk.Label(
        root,
        text=message,
        justify="center",
        wraplength=480
    )
    lbl.pack(padx=20, pady=20, fill="both", expand=True)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    def make_handler(val):
        def handler():
            result["value"] = val
            root.destroy()
        return handler

    for text, val in buttons:
        tk.Button(btn_frame, text=text, width=18, command=make_handler(val))\
            .pack(side="left", padx=8)

    root.mainloop()
    return result["value"]


def ui_error(message: str) -> str:
    return _show_window(
        "Ошибка",
        message,
        [
            ("Отмена", "cancel"),
            ("Продолжить", "continue"),
        ]
    )


def ui_checkpoint(message: str) -> bool:
    return _show_window(
        "Пауза",
        message,
        [
            ("Остановить", False),
            ("Продолжить", True),
        ]
    )


def ui_manual_continue(message: str) -> bool:
    return _show_window(
        "Ручная правка",
        message,
        [
            ("Отмена", False),
            ("Продолжить", True),
        ]
    )


def ui_adapt_action(message: str) -> str:
    return _show_window(
        "Адаптация",
        message,
        [
            ("Повторить", "retry"),
            ("Новая точка", "recalibrate"),
            ("Пропустить", "skip"),
            ("Отмена", "cancel"),
        ]
    )

def make_dialog_buttons(
    parent,
    ok_text="Сохранить",
    ok_command=None,
    cancel_text="Отмена",
    cancel_command=None,
    padx=10,
    pady=10,
    button_width=16,
):
    import tkinter as tk
    from tkinter import ttk

    btns = ttk.Frame(parent)
    btns.pack(fill="x", padx=padx, pady=pady)

    cancel_btn = ttk.Button(
        btns,
        text=cancel_text,
        width=button_width,
        command=cancel_command,
    )
    cancel_btn.pack(side="right", padx=4)

    ok_btn = ttk.Button(
        btns,
        text=ok_text,
        width=button_width,
        command=ok_command,
    )
    ok_btn.pack(side="right", padx=4)

    return btns, ok_btn, cancel_btn