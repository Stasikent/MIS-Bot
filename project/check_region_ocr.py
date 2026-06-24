import time
from pathlib import Path

import mss
import pygetwindow as gw
import pytesseract
from PIL import Image

RDP_TITLE_PART = "172.21.73.2"   # замени
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# сюда подставишь свою область даты рождения
DOB_REGION = (470, 250, 170, 35)

def get_rdp_window():
    wins = gw.getWindowsWithTitle(RDP_TITLE_PART)
    if not wins:
        raise RuntimeError(f"Окно RDP не найдено: {RDP_TITLE_PART}")
    win = wins[0]
    win.activate()
    time.sleep(0.8)
    return win

def screenshot_region(win, rel_region):
    x = win.left + rel_region[0]
    y = win.top + rel_region[1]
    w = rel_region[2]
    h = rel_region[3]

    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
        return Image.frombytes("RGB", shot.size, shot.rgb)

def main():
    win = get_rdp_window()
    img = screenshot_region(win, DOB_REGION)

    out = Path("dob_region_test.png")
    img.save(out)

    text = pytesseract.image_to_string(img, lang="rus+eng", config="--psm 7")
    print("OCR text:", repr(text))
    print("Saved image:", out.resolve())

if __name__ == "__main__":
    main()