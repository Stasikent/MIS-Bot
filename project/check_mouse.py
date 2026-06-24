import time
import pyautogui
import pygetwindow as gw

RDP_TITLE_PART = "Инфоклиника"

def choose_window():
    windows = []
    for w in gw.getAllWindows():
        title = (w.title or "").strip()
        if title:
            windows.append(w)

    if not windows:
        raise RuntimeError("Вообще не найдено ни одного окна с заголовком")

    if not RDP_TITLE_PART:
        print("Найдены окна:")
        for i, w in enumerate(windows, 1):
            print(f"{i:2d}. {w.title}")
        raise RuntimeError("Заполни RDP_TITLE_PART частью заголовка нужного окна")

    matched = [w for w in windows if RDP_TITLE_PART.lower() in w.title.lower()]
    if not matched:
        print("Доступные окна:")
        for i, w in enumerate(windows, 1):
            print(f"{i:2d}. {w.title}")
        raise RuntimeError(f"Окно не найдено по шаблону: {RDP_TITLE_PART}")

    win = matched[0]
    win.activate()
    time.sleep(0.8)
    return win

def main():
    win = choose_window()
    print("Окно найдено:")
    print(f"title={win.title}")
    print(f"left={win.left}, top={win.top}, width={win.width}, height={win.height}")
    print()
    print("Наводи мышь на нужные точки. Ctrl+C для выхода.")
    print()

    while True:
        x, y = pyautogui.position()
        rel_x = x - win.left
        rel_y = y - win.top
        print(f"ABS=({x:4d}, {y:4d}) | REL=({rel_x:4d}, {rel_y:4d})     ", end="\r")
        time.sleep(0.05)

if __name__ == "__main__":
    main()