import cv2
from datetime import datetime
from pathlib import Path


CAMERA_INDEX = 1  # поменяй, если USB-камера на другом индексе


def ensure_capture_dir() -> Path:
    out_dir = Path("captures")
    out_dir.mkdir(exist_ok=True)
    return out_dir


def enhance_frame_for_document(frame):
    """
    Мягкая обработка под OCR:
    - увеличиваем
    - grayscale
    - легкое повышение контраста
    - небольшое шумоподавление
    - без жесткой бинаризации
    """
    frame = cv2.resize(frame, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    return gray


def capture_from_webcam() -> Path | None:
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Не удалось открыть камеру")
        return None

    # Просим максимальное разумное разрешение
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    print(f"Используется камера индекс: {CAMERA_INDEX}")
    print("SPACE — сделать снимок | ESC — отмена")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        preview = frame.copy()
        h, w = preview.shape[:2]

        # Более широкая рамка, чтобы ФИО и дата точно попадали
        x1, y1 = int(w * 0.08), int(h * 0.08)
        x2, y2 = int(w * 0.92), int(h * 0.92)
        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow("Camera", preview)
        key = cv2.waitKey(1)

        if key == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            return None

        elif key == 32:  # SPACE
            crop = frame[y1:y2, x1:x2]
            enhanced = enhance_frame_for_document(crop)

            out_dir = ensure_capture_dir()
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            out_path = out_dir / filename

            cv2.imwrite(str(out_path), enhanced)

            cap.release()
            cv2.destroyAllWindows()
            return out_path