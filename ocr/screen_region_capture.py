from pathlib import Path
from datetime import datetime

from PIL import ImageGrab

from gui.labeled_pick_overlay import pick_labeled_rect


LOG_DIR = Path(__file__).resolve().parents[1] / "project" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _now_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def capture_screen_region(parent):
    rect = pick_labeled_rect(parent, "Выделите область", rect_color="red")
    if not rect:
        return None

    left, top, width, height = rect
    img = ImageGrab.grab(bbox=(left, top, left + width, top + height))

    out_path = LOG_DIR / f"screen_region_{_now_str()}.png"
    img.save(out_path)
    return str(out_path)


def capture_named_screen_region(parent, title_text: str, rect_color="red"):
    rect = pick_labeled_rect(parent, title_text=title_text, rect_color=rect_color)
    if not rect:
        return None

    left, top, width, height = rect
    img = ImageGrab.grab(bbox=(left, top, left + width, top + height))

    out_path = LOG_DIR / f"screen_region_{_now_str()}.png"
    img.save(out_path)
    return str(out_path)