from pathlib import Path

path = Path('project/bot_mode1_current.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
        '        "backspace": 0x08,\n    }',
        '        "backspace": 0x08,\n        "f2": 0x71,           # VK_F2\n        "esc": 0x1B,          # VK_ESCAPE\n    }',
    ),
    (
        '''def click_template_target(\n    win,\n    template_key,\n    offset=(0, 0),\n    offset_key=None,\n    confidence=None,\n    timeout=8,\n    label=None,\n    clicks=1\n):\n    if offset_key:\n''',
        '''def click_template_target(\n    win,\n    template_key,\n    offset=(0, 0),\n    offset_key=None,\n    confidence=None,\n    timeout=8,\n    label=None,\n    clicks=1\n):\n    current_offset = offset\n    if offset_key:\n''',
    ),
    (
        '''    checkpoint()\n    pyautogui.click(x, y, clicks=clicks, interval=0.15)\n    checkpoint()\n    time.sleep(0.3)\n    checkpoint()\n    return x, y\n\n\ndef ask_user_checkpoint''',
        '''    checkpoint()\n    if not _win32_click(x, y, clicks=clicks, interval=0.15):\n        return manual_recover_step(\n            win,\n            f"Не удалось физически нажать точку: {label}",\n            "Выполните этот клик вручную.",\n        )\n    checkpoint()\n    time.sleep(0.3)\n    checkpoint()\n    return x, y\n\n\ndef ask_user_checkpoint''',
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one match, found {count}: {old[:80]!r}')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('runtime patch applied successfully')
