from pathlib import Path
import sys

from ocr.direction_ocr import parse_direction_image
from project.bot_mode1_current import full_run


def ask_user_confirmation(task):
    print("\n=== OCR RESULT ===")
    print("FIO       :", task.fio)
    print("BIRTH DATE:", task.birth_date)
    print("STUDY DATE:", task.study_date)
    print("MODE      :", task.mode)
    print()

    ans = input("Запустить сценарий по этим данным? (y/n): ").strip().lower()
    return ans in ("y", "yes", "д", "да")


def main():
    if len(sys.argv) < 2:
        print(r"Использование: python run_from_direction.py <path_to_image> [mode]")
        raise SystemExit(1)

    image_path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) >= 3 else "normal"

    if not image_path.exists():
        print(f"Ошибка: файл не найден: {image_path}")
        raise SystemExit(1)

    try:
        task = parse_direction_image(image_path, mode=mode)
    except Exception as e:
        print("❌ Ошибка OCR:", e)
        raise SystemExit(1)

    if not ask_user_confirmation(task):
        print("⛔ Запуск отменен пользователем")
        raise SystemExit(0)

    try:
        full_run(
            task.fio,
            task.birth_date,
            study_date=task.study_date,
            mode=task.mode,
            step_mode=False
        )
    except Exception as e:
        print("❌ Ошибка выполнения сценария:", e)


if __name__ == "__main__":
    main()