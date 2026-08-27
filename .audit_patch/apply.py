from pathlib import Path


def replace_once(path: str, old: str, new: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected 1 match, got {count} for {old[:80]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Initial workplace setup must include runtime-critical anchors that were
# previously available only through the technical Click Map.
replace_once(
    "gui/workplace_setup_wizard.py",
    '''    {
        "key": "goal_dropdown",
        "title": "Поле «Цель обращения»",
        "kind": "template_offset",
        "offset_key": "goal_dropdown_offset",
        "description": (
            "Откройте окно приёма. Выделите область выпадающего списка цели обращения, "
            "затем кликните по фактической точке."
        ),
    },
''',
    '''    {
        "key": "goal_dropdown",
        "title": "Поле «Цель обращения»",
        "kind": "template_offset",
        "offset_key": "goal_dropdown_offset",
        "description": (
            "Откройте окно приёма. Выделите область выпадающего списка цели обращения, "
            "затем кликните по фактической точке."
        ),
    },
    {
        "key": "goal_active_visit_item",
        "title": "Цель обращения → «Активное посещение»",
        "kind": "template_offset",
        "offset_key": "goal_active_visit_item_offset",
        "description": (
            "Раскройте список «Цель обращения», выделите пункт «Активное посещение» "
            "и затем укажите точку клика по нему."
        ),
    },
''',
)

replace_once(
    "gui/workplace_setup_wizard.py",
    '''    {
        "key": "reason_field",
        "title": "Поле «Повод обращения»",
        "kind": "template_offset",
        "offset_key": "reason_field_offset",
        "description": (
            "Откройте окно приёма. Выделите устойчивую часть поля «Повод обращения», "
            "затем укажите точку, куда бот должен кликать."
        ),
    },
''',
    '''    {
        "key": "inpatient_question",
        "title": "Вопрос «Пациент в стационаре?»",
        "kind": "template_only",
        "description": (
            "Если на этом рабочем месте появляется вопрос о стационаре, выделите устойчивую "
            "часть окна. Если окно не используется, шаг можно пропустить."
        ),
    },
    {
        "key": "inpatient_yes_button",
        "title": "Стационар → кнопка «Да»",
        "kind": "template_offset",
        "offset_key": "inpatient_yes_button_offset",
        "description": (
            "При открытом вопросе о стационаре выделите кнопку/якорь «Да» и укажите "
            "фактическую точку клика. Если ветка не используется, шаг можно пропустить."
        ),
    },
    {
        "key": "add_diagnosis_question",
        "title": "Вопрос «Добавить диагноз?»",
        "kind": "template_only",
        "description": (
            "Если после стационарного окна появляется вопрос «Добавить диагноз?», "
            "выделите устойчивую область этого окна."
        ),
    },
    {
        "key": "add_diagnosis_no_button",
        "title": "Добавить диагноз → «Нет»",
        "kind": "template_offset",
        "offset_key": "add_diagnosis_no_button_offset",
        "description": (
            "В окне «Добавить диагноз?» выделите кнопку «Нет» и укажите точку клика."
        ),
    },
    {
        "key": "reason_field",
        "title": "Поле «Повод обращения»",
        "kind": "template_offset",
        "offset_key": "reason_field_offset",
        "description": (
            "Откройте окно приёма. Выделите устойчивую часть поля «Повод обращения», "
            "затем укажите точку, куда бот должен кликать."
        ),
    },
''',
)

replace_once(
    "gui/workplace_setup_wizard.py",
    '''    {
        "key": "study_date_label",
        "title": "Метка даты исследования",
        "kind": "template_offset",
        "offset_key": "study_date_label_offset",
        "description": "Выделите подпись/якорь рядом с датой исследования и затем кликните в само поле даты.",
    },
''',
    '''    {
        "key": "study_date_label",
        "title": "Метка даты исследования (флюорография)",
        "kind": "template_offset",
        "offset_key": "study_date_label_offset",
        "description": "Для флюорографии выделите подпись/якорь рядом с датой исследования и затем кликните в само поле даты.",
    },
    {
        "key": "xray_field_description",
        "title": "Рентген → поле «Описание»",
        "kind": "template_offset",
        "offset_key": "xray_field_description_offset",
        "description": (
            "Откройте рентген-протокол, выделите устойчивый якорь поля «Описание» "
            "и укажите точку ввода текста."
        ),
    },
    {
        "key": "xray_field_conclusion",
        "title": "Рентген → поле «Заключение»",
        "kind": "template_offset",
        "offset_key": "xray_field_conclusion_offset",
        "description": (
            "В том же рентген-протоколе выделите устойчивый якорь поля «Заключение» "
            "и укажите точку ввода текста."
        ),
    },
''',
)

# 2) Correct labels in the technical map and make test clicks use the same
# Win32 physical-coordinate mechanism as the real bot.
replace_once(
    "gui/click_map_technical_window.py",
    '''    debug_click_point,
)''',
    '''    debug_click_point,
    _win32_click,
)''',
)
replace_once(
    "gui/click_map_technical_window.py",
    '''    "case_result_label": "Исход случая",
    "case_outcome_label": "Результат случая",
''',
    '''    "case_result_label": "Результат случая",
    "case_outcome_label": "Исход заболевания",
''',
)
replace_once(
    "gui/click_map_technical_window.py",
    '''            debug_click_point(x, y)
            time.sleep(0.25)
            pyautogui.click(x, y)
''',
    '''            if not debug_click_point(x, y):
                raise RuntimeError(f"Точка ({x}, {y}) вне виртуального рабочего стола")
            time.sleep(0.25)
            if not _win32_click(x, y):
                raise RuntimeError(f"Win32-клик не выполнен в ({x}, {y})")
''',
)

print("final audit source fixes applied")
