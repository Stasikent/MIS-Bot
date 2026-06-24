import tkinter as tk


class ScreenPickOverlay(tk.Toplevel):
    def __init__(self, parent, mode="point"):
        super().__init__(parent)
        self.mode = mode  # "point" | "rect"
        self.result = None

        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.22)

        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None
        self.rect_id = None
        self.crosshair_ids = []

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.hint_id = self.canvas.create_text(
            20,
            20,
            anchor="nw",
            text=self._hint_text(),
            fill="white",
            font=("Segoe UI", 14, "bold"),
        )

        self.canvas.bind("<Button-1>", self._on_left_down)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_up)
        self.canvas.bind("<Motion>", self._on_motion)

        self.bind("<Escape>", self._on_escape)
        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _hint_text(self):
        if self.mode == "point":
            return "Кликни по нужной точке. Esc — отмена"
        return "Зажми левую кнопку и выдели область. Esc — отмена"

    def _clear_crosshair(self):
        for item_id in self.crosshair_ids:
            self.canvas.delete(item_id)
        self.crosshair_ids.clear()

    def _draw_crosshair(self, x, y):
        self._clear_crosshair()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()

        self.crosshair_ids.append(
            self.canvas.create_line(0, y, w, y, fill="red", width=1)
        )
        self.crosshair_ids.append(
            self.canvas.create_line(x, 0, x, h, fill="red", width=1)
        )
        self.crosshair_ids.append(
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, outline="yellow", width=2)
        )

    def _on_motion(self, event):
        self._draw_crosshair(event.x_root, event.y_root)

    def _on_left_down(self, event):
        x = event.x_root
        y = event.y_root

        if self.mode == "point":
            self.result = (int(x), int(y))
            self._finish()
            return

        self.start_x = x
        self.start_y = y
        self.current_x = x
        self.current_y = y

        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)

        self.rect_id = self.canvas.create_rectangle(
            x, y, x, y,
            outline="red",
            width=2,
            dash=(6, 4),
        )

    def _on_drag(self, event):
        if self.mode != "rect" or self.rect_id is None:
            return

        self.current_x = event.x_root
        self.current_y = event.y_root

        self.canvas.coords(
            self.rect_id,
            self.start_x,
            self.start_y,
            self.current_x,
            self.current_y,
        )

    def _on_left_up(self, event):
        if self.mode != "rect" or self.start_x is None or self.start_y is None:
            return

        x2 = event.x_root
        y2 = event.y_root

        left = min(self.start_x, x2)
        top = min(self.start_y, y2)
        width = abs(x2 - self.start_x)
        height = abs(y2 - self.start_y)

        self.result = (int(left), int(top), int(width), int(height))
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


def pick_screen_point(parent):
    overlay = ScreenPickOverlay(parent, mode="point")
    parent.wait_window(overlay)
    return overlay.result


def pick_screen_rect(parent):
    overlay = ScreenPickOverlay(parent, mode="rect")
    parent.wait_window(overlay)
    return overlay.result