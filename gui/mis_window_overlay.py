from __future__ import annotations

import ctypes
from ctypes import wintypes
import tkinter as tk

user32 = ctypes.windll.user32

# Full Windows virtual desktop metrics
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# DPI contexts
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

# Win32
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

# SetThreadDpiAwarenessContext may not exist on old Windows
try:
    _SetThreadDpiAwarenessContext = user32.SetThreadDpiAwarenessContext
    _SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    _SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
except Exception:
    _SetThreadDpiAwarenessContext = None


def _push_per_monitor_dpi():
    """
    Make ONLY the current GUI thread Per-Monitor-V2 while creating/using
    the calibration overlay. This works even if the main Tk application
    was created earlier with another DPI mode.
    """
    if _SetThreadDpiAwarenessContext is None:
        return None

    try:
        return _SetThreadDpiAwarenessContext(
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        )
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
    """
    Physical bounding rectangle of ALL currently connected monitors.
    May have negative left/top coordinates.
    """
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"Некорректный виртуальный рабочий стол: "
            f"left={left}, top={top}, width={width}, height={height}"
        )

    return left, top, width, height


def get_cursor_pos():
    pt = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError()
    return int(pt.x), int(pt.y)


def _place_exact(window, left, top, width, height):
    window.update_idletasks()

    # Ensure a native HWND exists.
    window.geometry(f"{max(1, width)}x{max(1, height)}+0+0")
    window.update_idletasks()

    hwnd = wintypes.HWND(window.winfo_id())

    HWND_TOPMOST = wintypes.HWND(-1)
    SWP_SHOWWINDOW = 0x0040

    ok = user32.SetWindowPos(
        hwnd,
        HWND_TOPMOST,
        int(left),
        int(top),
        int(width),
        int(height),
        SWP_SHOWWINDOW,
    )
    if not ok:
        raise ctypes.WinError()


class FullVirtualDesktopOverlay(tk.Toplevel):
    """
    Classic darkened selection overlay over the ENTIRE Windows virtual desktop.

    Important differences from previous attempts:
    - no monitor is selected or fixed;
    - no screenshots are used;
    - no restriction to the MIS/RDP rectangle;
    - the overlay spans the complete bounding rectangle of all monitors;
    - the overlay thread is temporarily switched to Per-Monitor-V2 DPI mode;
    - actual coordinates are read from Win32 GetCursorPos, not Tk event coords.
    """

    def __init__(self, parent, mode: str, title_text: str, rect_color="yellow"):
        self._previous_dpi = _push_per_monitor_dpi()

        try:
            super().__init__(parent)

            if mode not in {"point", "rect"}:
                raise ValueError("mode must be point or rect")

            self.mode = mode
            self.result = None
            self.rect_color = rect_color

            (
                self.virtual_left,
                self.virtual_top,
                self.virtual_width,
                self.virtual_height,
            ) = virtual_desktop_bounds()

            self.start_global = None
            self.rect_id = None
            self.crosshair_ids = []

            self.withdraw()
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.attributes("-alpha", 0.27)
            self.configure(bg="black")

            self.canvas = tk.Canvas(
                self,
                bg="black",
                highlightthickness=0,
                cursor="crosshair",
            )
            self.canvas.pack(fill="both", expand=True)

            self.message_id = self.canvas.create_text(
                24,
                24,
                anchor="nw",
                text=(
                    f"{title_text}   |   Esc — отмена\n"
                    f"Все экраны: {self.virtual_width}×{self.virtual_height}, "
                    f"origin=({self.virtual_left},{self.virtual_top})"
                ),
                fill="white",
                font=("Segoe UI", 15, "bold"),
            )

            self.canvas.bind("<Motion>", self._on_motion)
            self.canvas.bind("<ButtonPress-1>", self._on_down)
            self.canvas.bind("<B1-Motion>", self._on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_up)
            self.bind("<Escape>", self._cancel)

            self.deiconify()
            _place_exact(
                self,
                self.virtual_left,
                self.virtual_top,
                self.virtual_width,
                self.virtual_height,
            )

            self.lift()
            self.focus_force()
            self.grab_set()

        except Exception:
            _pop_dpi(self._previous_dpi)
            raise

    def _global_to_canvas(self, gx, gy):
        """
        Use actual canvas/native size instead of assuming Tk's event coordinate
        scale equals Windows physical coordinates.
        """
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())

        x_ratio = cw / self.virtual_width
        y_ratio = ch / self.virtual_height

        lx = int(round((gx - self.virtual_left) * x_ratio))
        ly = int(round((gy - self.virtual_top) * y_ratio))
        return lx, ly

    def _current_global(self):
        return get_cursor_pos()

    def _clear_crosshair(self):
        for item in self.crosshair_ids:
            self.canvas.delete(item)
        self.crosshair_ids.clear()

    def _on_motion(self, _event):
        gx, gy = self._current_global()
        x, y = self._global_to_canvas(gx, gy)

        self._clear_crosshair()

        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())

        self.crosshair_ids.append(
            self.canvas.create_line(0, y, cw, y, fill="yellow", width=1)
        )
        self.crosshair_ids.append(
            self.canvas.create_line(x, 0, x, ch, fill="yellow", width=1)
        )

    def _on_down(self, _event):
        gx, gy = self._current_global()

        if self.mode == "point":
            self.result = (gx, gy)
            self._finish()
            return

        self.start_global = (gx, gy)
        x, y = self._global_to_canvas(gx, gy)

        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)

        self.rect_id = self.canvas.create_rectangle(
            x, y, x, y,
            outline=self.rect_color,
            width=3,
            dash=(7, 4),
        )

    def _on_drag(self, _event):
        if self.mode != "rect" or self.start_global is None or self.rect_id is None:
            return

        gx2, gy2 = self._current_global()
        gx1, gy1 = self.start_global

        x1, y1 = self._global_to_canvas(gx1, gy1)
        x2, y2 = self._global_to_canvas(gx2, gy2)

        self.canvas.coords(self.rect_id, x1, y1, x2, y2)

    def _on_up(self, _event):
        if self.mode != "rect" or self.start_global is None:
            return

        gx2, gy2 = self._current_global()
        gx1, gy1 = self.start_global

        left = min(gx1, gx2)
        top = min(gy1, gy2)
        width = abs(gx2 - gx1)
        height = abs(gy2 - gy1)

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
    overlay = FullVirtualDesktopOverlay(
        parent,
        mode="point",
        title_text=title_text,
    )
    parent.wait_window(overlay)
    return overlay.result


def pick_rect_in_mis(parent, title_text="Выдели область", rect_color="yellow"):
    overlay = FullVirtualDesktopOverlay(
        parent,
        mode="rect",
        title_text=title_text,
        rect_color=rect_color,
    )
    parent.wait_window(overlay)
    return overlay.result
