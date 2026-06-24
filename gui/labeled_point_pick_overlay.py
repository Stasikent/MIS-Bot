import tkinter as tk


class LabeledPointPickOverlay(tk.Toplevel):
    def __init__(self, parent, title_text="Кликни в нужную точку"):
        super().__init__(parent)
        self.result = None

        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.22)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.crosshair_ids = []

        self.canvas.create_text(
            20,
            20,
            anchor="nw",
            text=f"{title_text}   |   Esc — отмена",
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )

        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_click)
        self.bind("<Escape>", self._on_escape)

        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _clear_crosshair(self):
        for item_id in self.crosshair_ids:
            self.canvas.delete(item_id)
        self.crosshair_ids.clear()

    def _draw_crosshair(self, x, y):
        self._clear_crosshair()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()

        self.crosshair_ids.append(self.canvas.create_line(0, y, w, y, fill="yellow", width=1))
        self.crosshair_ids.append(self.canvas.create_line(x, 0, x, h, fill="yellow", width=1))
        self.crosshair_ids.append(
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, outline="white", width=2)
        )

    def _on_motion(self, event):
        self._draw_crosshair(event.x_root, event.y_root)

    def _on_click(self, event):
        self.result = (int(event.x_root), int(event.y_root))
        self._finish()

    def _on_escape(self, _event=None):
        self.result = None
        self._finish()

    def _finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def pick_labeled_point(parent, title_text="Кликни в нужную точку"):
    overlay = LabeledPointPickOverlay(parent, title_text=title_text)
    parent.wait_window(overlay)
    return overlay.result