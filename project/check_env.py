from pathlib import Path
import sys
import struct

print("=== PYTHON ===")
print("Version:", sys.version)
print("Arch:", struct.calcsize("P") * 8, "bit")

print("\n=== IMPORTS ===")
mods = [
    "pyautogui",
    "pygetwindow",
    "PIL",
    "mss",
    "pytesseract",
    "cv2",
    "rapidfuzz",
    "numpy",
]
for m in mods:
    try:
        __import__(m)
        print(f"[OK] {m}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")

print("\n=== TESSERACT ===")
try:
    import pytesseract

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]

    exe = None
    for p in candidates:
        p = Path(p.replace("%USERNAME%", Path.home().name))
        if p.exists():
            exe = str(p)
            break

    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
        print("[OK] tesseract.exe:", exe)
        print("[OK] version:", pytesseract.get_tesseract_version())
    else:
        print("[FAIL] tesseract.exe not found in standard paths")

except Exception as e:
    print("[FAIL] Tesseract check:", e)

print("\n=== DONE ===")