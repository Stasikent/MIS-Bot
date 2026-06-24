import time
import pygetwindow as gw


def pick_window_by_click(timeout=5):
    """
    Дает пользователю время кликнуть по нужному окну.
    Возвращает title активного окна.
    """
    print("Выберите окно (кликните по нему)...")

    time.sleep(timeout)

    win = gw.getActiveWindow()
    if not win:
        return None

    return win.title