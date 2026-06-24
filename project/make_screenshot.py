import time
from pathlib import Path

import mss
import pygetwindow as gw
from PIL import Image

RDP_TITLE_PART = "Инфоклиника"   # замени на часть заголовка своего окна
OUT_DIR = Path("screenshots")
OUT_DIR.mkdir(exist_ok=True)

def get_rdp_window():
    wins = gw.getWindowsWithTitle(RDP_TITLE_PART)
    if not wins:
        raise RuntimeError(f"Окно RDP не найдено: {RDP_TITLE_PART}")
    win = wins[0]
    win.activate()
    time.sleep(0.8)
    return win

def screenshot_window(win):
    with mss.mss() as sct:
        shot = sct.grab({
            "left": win.left,
            "top": win.top,
            "width": win.width,
            "height": win.height,
        })
        return Image.frombytes("RGB", shot.size, shot.rgb)

def main():
    win = get_rdp_window()
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"rdp_{ts}.png"
    img = screenshot_window(win)
    img.save(out)
    print("Saved:", out.resolve())

if __name__ == "__main__":
    main()