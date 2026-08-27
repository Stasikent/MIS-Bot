from project.bot_mode1_current import (
    find_mis_window,
    ensure_open_patient_card,
    set_active_controller,
    checkpoint,
    log,
    search_patient,
    find_patient_by_birth_date_and_click,
    open_visit,
    handle_post_visit_plus_flow,
    handle_visit_opening_flow,
    handle_inpatient_popup_if_present,
    fill_reason_code,
    fill_goal_complex,
    open_work_service,
    choose_first_service,
    open_history_xray,
    open_templates_selector,
    choose_only_my_templates,
    clear_template_diagnosis_if_exists,
    choose_xray_template,
    fill_xray_protocol,
    save_and_sign_xray_protocol,
    close_xray_diagnosis_314_304,
)


def _validate_xray_task(task):
    required = {
        "ФИО": getattr(task, "fio", ""),
        "Дата рождения": getattr(task, "birth_date", ""),
        "Дата исследования": getattr(task, "study_date", ""),
        "Исследование": getattr(task, "study_name", ""),
        "Описание": getattr(task, "description", ""),
        "Заключение": getattr(task, "conclusion", ""),
        "Шаблон": (
            getattr(task, "template_key", "")
            or getattr(task, "template_name", "")
        ),
    }

    missing = [
        name
        for name, value in required.items()
        if not str(value or "").strip()
    ]

    if missing:
        raise RuntimeError(
            "Для запуска рентгена не заполнены поля: " + ", ".join(missing)
        )


def _require_step(result, step_name: str):
    # Старые функции могут при успехе вернуть None.
    # Ошибкой считаем только явный False.
    if result is False:
        raise RuntimeError(f"[XRAY] Ошибка на этапе: {step_name}")



def _run_xray_after_open_card(task, win):
    """
    Общая часть рентген-сценария после того, как карточка/приём уже открыт.
    """
    log("[XRAY] Открытая карточка: повод обращения")
    _require_step(fill_reason_code(win), "заполнение повода обращения")
    checkpoint()

    log("[XRAY] Открытая карточка: цель обращения")
    _require_step(fill_goal_complex(win), "заполнение цели обращения")
    checkpoint()

    log("[XRAY] Открытая карточка: открытие списка услуг")
    _require_step(open_work_service(win), "открытие списка услуг")
    checkpoint()

    log("[XRAY] Открытая карточка: выбор услуги из открытого списка")
    _require_step(choose_first_service(win), "выбор услуги")
    checkpoint()

    log("[XRAY] Открытая карточка: История болезни -> Рентгенографическое исследование")
    _require_step(open_history_xray(win), "открытие рентгенографического протокола")
    checkpoint()

    log("[XRAY] Открытая карточка: Шаблоны -> Выбрать")
    _require_step(open_templates_selector(win), "Шаблоны -> Выбрать")
    checkpoint()

    log("[XRAY] Открытая карточка: Владелец -> Только свои")
    _require_step(choose_only_my_templates(win), "фильтр Только свои")
    checkpoint()

    log("[XRAY] Открытая карточка: удаление диагноза из шаблона")
    _require_step(clear_template_diagnosis_if_exists(win), "удаление диагноза из шаблона")
    checkpoint()

    log("[XRAY] Открытая карточка: выбор рентген-шаблона")
    _require_step(choose_xray_template(win, task), "выбор рентген-шаблона")
    checkpoint()

    log("[XRAY] Открытая карточка: заполнение протокола")
    _require_step(fill_xray_protocol(win, task), "заполнение описания и заключения")
    checkpoint()

    log("[XRAY] Открытая карточка: сохранение и подпись без поля даты")
    _require_step(
        save_and_sign_xray_protocol(win),
        "сохранение и подписание протокола",
    )
    checkpoint()

    log("[XRAY] Открытая карточка: закрытие диагноза 314 / 304")
    _require_step(close_xray_diagnosis_314_304(win), "закрытие диагноза 314/304")
    checkpoint()

    return True


def run_xray_from_open_patient_card(task, controller=None):
    """
    Запуск рентгена из уже открытой карточки пациента.

    Отличия от флюорографии остаются только рентген-специфичными:
    - выбор услуги выполняется общей логикой списка услуг;\n    - протокол «Рентгенографическое исследование» выбирается в Истории болезни;
    - рентген-шаблон;
    - заполнение описания и заключения.
    """
    try:
        set_active_controller(controller)
        _validate_xray_task(task)

        log("=" * 60)
        log("[XRAY] СТАРТ ИЗ ОТКРЫТОЙ КАРТОЧКИ")
        log(f"[XRAY] Пациент: {task.fio}")
        log(f"[XRAY] Исследование: {task.study_name}")
        log("=" * 60)

        win = find_mis_window()
        checkpoint()

        ok = ensure_open_patient_card(win)
        checkpoint()
        _require_step(ok, "проверка открытой карточки")

        result = _run_xray_after_open_card(task, win)

        log("[XRAY] Сценарий из открытой карточки завершён успешно")
        return result

    except Exception as exc:
        log(f"[XRAY] ОТКРЫТАЯ КАРТОЧКА — ОСТАНОВКА: {exc}")
        raise

    finally:
        set_active_controller(None)


def run_xray_task(task, controller=None):
    try:
        set_active_controller(controller)
        _validate_xray_task(task)

        log("=" * 60)
        log("[XRAY] СТАРТ")
        log(f"[XRAY] Пациент: {task.fio}")
        log(f"[XRAY] ДР: {task.birth_date}")
        log(f"[XRAY] Дата исследования: {task.study_date}")
        log(f"[XRAY] Исследование: {task.study_name}")
        log(
            f"[XRAY] Шаблон: "
            f"{getattr(task, 'template_name', '')} / "
            f"{getattr(task, 'template_key', '')}"
        )
        log(f"[XRAY] Описание: {len(getattr(task, 'description', '') or '')} символов")
        log(f"[XRAY] Заключение: {len(getattr(task, 'conclusion', '') or '')} символов")
        log("=" * 60)

        log("[XRAY] Этап 0: поиск окна МИС")
        win = find_mis_window()
        checkpoint()

        log("[XRAY] Этап 1: поиск пациента по ФИО")
        result = search_patient(win, task.fio)
        checkpoint()
        _require_step(result, "поиск поля ФИО и ввод пациента")

        log("[XRAY] Этап 2: выбор пациента по дате рождения")
        result = find_patient_by_birth_date_and_click(win, task.birth_date)
        checkpoint()
        _require_step(result, "выбор пациента по дате рождения")

        log("[XRAY] Этап 3: открытие нового приёма")
        result = open_visit(win, study_date=task.study_date)
        checkpoint()
        _require_step(result, "открытие нового приёма")

        log("[XRAY] Этап 4: подтверждение даты и определение ветки открытия приёма")
        visit_flow = handle_visit_opening_flow(win)
        checkpoint()
        _require_step(visit_flow, "открытие приёма")

        is_inpatient_flow = (visit_flow == "inpatient")
        if is_inpatient_flow:
            log("[XRAY] Стационарный пациент: ветка стационара обработана после Enter")
        else:
            log("[XRAY] Обычный пациент: окно приёма готово")

        log("[XRAY] Этап 5: повод обращения")
        result = fill_reason_code(win)
        checkpoint()
        _require_step(result, "заполнение повода обращения")

        log("[XRAY] Этап 6: цель обращения")
        result = fill_goal_complex(win)
        checkpoint()
        _require_step(result, "заполнение цели обращения")

        log("[XRAY] Этап 7: открытие списка услуг")
        result = open_work_service(win)
        checkpoint()
        _require_step(result, "открытие списка услуг")

        log("[XRAY] Этап 8: выбор услуги из открытого списка")
        result = choose_first_service(win)
        checkpoint()
        _require_step(result, "выбор услуги")

        log("[XRAY] Этап 9: открытие истории болезни / шаблонов")
        result = open_history_xray(win)
        checkpoint()
        _require_step(result, "открытие истории болезни и шаблонов")

        log("[XRAY] Этап 10: Шаблоны -> Выбрать")
        result = open_templates_selector(win)
        checkpoint()
        _require_step(result, "Шаблоны -> Выбрать")

        log("[XRAY] Этап 11: Владелец -> Только свои")
        result = choose_only_my_templates(win)
        checkpoint()
        _require_step(result, "фильтр Только свои")

        log("[XRAY] Этап 12: удаление диагноза из шаблона")
        result = clear_template_diagnosis_if_exists(win)
        checkpoint()
        _require_step(result, "удаление диагноза из шаблона")

        log("[XRAY] Этап 13: выбор рентген-шаблона")
        result = choose_xray_template(win, task)
        checkpoint()
        _require_step(result, "выбор рентген-шаблона")

        log("[XRAY] Этап 14: заполнение протокола")
        result = fill_xray_protocol(win, task)
        checkpoint()
        _require_step(result, "заполнение описания и заключения")

        log("[XRAY] Этап 15: сохранение и подпись без поиска даты исследования")
        result = save_and_sign_xray_protocol(win)
        checkpoint()
        _require_step(result, "сохранение и подписание протокола")

        if is_inpatient_flow:
            log("[XRAY] Стационарный пациент: закрытие диагноза 314/304 пропущено")
        else:
            log("[XRAY] Этап 16: закрытие диагноза 314 / 304")
            result = close_xray_diagnosis_314_304(win)
            checkpoint()
            _require_step(result, "закрытие диагноза 314/304")

        log("[XRAY] Рентген-сценарий завершён успешно")
        return True

    except Exception as exc:
        log(f"[XRAY] ОСТАНОВКА: {exc}")
        raise

    finally:
        set_active_controller(None)
