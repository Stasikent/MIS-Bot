from __future__ import annotations

import ctypes
from ctypes import wintypes
import tkinter as tk

user32 = ctypes.windll.user32
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

try:
    _SetThreadDpiAwarenessContext = user32.SetThreadDpiAwarenessContext
    _SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    _SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
except Exception:
    _SetThreadDpiAwarenessContext = None


def _push_per_monitor_dpi():
    if _SetThreadDpiAwarenessContext is None:
        return None
    try:
        return _SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
    except Exception:
        return None


def _pop_dpi(previous):
    if previous is None or _SetThreadDpiAwarenessContext is None:
        return
    try:
        _SetThreadDpiAwarenessContext(previous)
    except Exception:
        pass


def virtual_desktop_bounds():
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Некорректный виртуальный рабочий стол: left={left}, top={top}, width={width}, height={height}")
    return left, top, width, height


def get_cursor_pos():
    pt = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError()
    return int(pt.x), int(pt.y)


def _place_exact(window, left, top, width, height):
    window.update_idletasks()
    window.geometry(f"{max(1, width)}x{max(1, height)}+0+0")
    window.update_idletasks()
    hwnd = wintypes.HWND(window.winfo_id())
    if not user32.SetWindowPos(hwnd, wintypes.HWND(-1), int(left), int(top), int(width), int(height), 0x0040):
        raise ctypes.WinError()


class FullVirtualDesktopOverlay(tk.Toplevel):
    """Dark selection overlay spanning the complete Windows virtual desktop."""

    def __init__(self, parent, mode: str, title_text: str, rect_color="yellow"):
        self._previous_dpi = _push_per_monitor_dpi()
        try:
            super().__init__(parent)
            if mode not in {"point", "rect"}:
                raise ValueError("mode must be point or rect")
            self.mode = mode
            self.result = None
            self.rect_color = rect_color
            self.virtual_left, self.virtual_top, self.virtual_width, self.virtual_height = virtual_desktop_bounds()
            self.start_global = None
            self.rect_id = None
            self.crosshair_ids = []
            self.withdraw()
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.27)
            self.configure(bg="black")
            self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
            self.canvas.pack(fill="both", expand=True)
            self.canvas.create_text(24, 24, anchor="nw", text=(f"{title_text}   |   Esc — отмена\nВсе экраны: {self.virtual_width}×{self.virtual_height}, origin=({self.virtual_left},{self.virtual_top})"), fill="white", font=("Segoe UI", 15, "bold"))
            self.canvas.bind("<Motion>", self._on_motion)
            self.canvas.bind("<ButtonPress-1>", self._on_down)
            self.canvas.bind("<B1-Motion>", self._on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_up)
            self.bind("<Escape>", self._cancel)
            self.deiconify()
            _place_exact(self, self.virtual_left, self.virtual_top, self.virtual_width, self.virtual_height)
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            _pop_dpi(self._previous_dpi)
            raise

    def _global_to_canvas(self, gx, gy):
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        return (int(round((gx - self.virtual_left) * cw / self.virtual_width)), int(round((gy - self.virtual_top) * ch / self.virtual_height)))

    def _clear_crosshair(self):
        for item in self.crosshair_ids:
            self.canvas.delete(item)
        self.crosshair_ids.clear()

    def _on_motion(self, _event):
        gx, gy = get_cursor_pos()
        x, y = self._global_to_canvas(gx, gy)
        self._clear_crosshair()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.crosshair_ids.append(self.canvas.create_line(0, y, cw, y, fill="yellow", width=1))
        self.crosshair_ids.append(self.canvas.create_line(x, 0, x, ch, fill="yellow", width=1))

    def _on_down(self, _event):
        gx, gy = get_cursor_pos()
        if self.mode == "point":
            self.result = (gx, gy)
            self._finish()
            return
        self.start_global = (gx, gy)
        x, y = self._global_to_canvas(gx, gy)
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(x, y, x, y, outline=self.rect_color, width=3, dash=(7, 4))

    def _on_drag(self, _event):
        if self.mode != "rect" or self.start_global is None or self.rect_id is None:
            return
        gx2, gy2 = get_cursor_pos()
        gx1, gy1 = self.start_global
        self.canvas.coords(self.rect_id, *self._global_to_canvas(gx1, gy1), *self._global_to_canvas(gx2, gy2))

    def _on_up(self, _event):
        if self.mode != "rect" or self.start_global is None:
            return
        gx2, gy2 = get_cursor_pos()
        gx1, gy1 = self.start_global
        left, top = min(gx1, gx2), min(gy1, gy2)
        width, height = abs(gx2 - gx1), abs(gy2 - gy1)
        if width < 3 or height < 3:
            if self.rect_id is not None:
                self.canvas.delete(self.rect_id)
            self.rect_id = None
            self.start_global = None
            return
        self.result = (left, top, width, height)
        self._finish()

    def _cancel(self, _event=None):
        self.result = None
        self._finish()

    def _finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        finally:
            _pop_dpi(self._previous_dpi)


def pick_point_in_mis(parent, title_text="Кликни в нужную точку"):
    overlay = FullVirtualDesktopOverlay(parent, mode="point", title_text=title_text)
    parent.wait_window(overlay)
    return overlay.result


def pick_rect_in_mis(parent, title_text="Выдели область", rect_color="yellow"):
    overlay = FullVirtualDesktopOverlay(parent, mode="rect", title_text=title_text, rect_color=rect_color)
    parent.wait_window(overlay)
    return overlay.result
