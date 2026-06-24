from project.bot_mode1_current import (
    find_mis_window,
    set_active_controller,
    checkpoint,
    log,
    search_patient,
    find_patient_by_birth_date_and_click,
    open_visit,
    handle_post_visit_plus_flow,
    handle_inpatient_popup_if_present,
    fill_reason_code,
    fill_goal_complex,
    open_work_service,
    choose_xray_service,
    open_history_fluoro,
    choose_only_my_templates,
    clear_template_diagnosis_if_exists,
    choose_xray_template,
    fill_xray_protocol,
    fill_template_date_and_sign,
    cancel_diagnosis,
)


def _validate_xray_task(task):
    required = {
        "ФИО": task.fio,
        "Дата рождения": task.birth_date,
        "Дата исследования": task.study_date,
        "Исследование": task.study_name,
        "Описание": task.description,
        "Заключение": task.conclusion,
        "Шаблон": task.template_key or task.template_name,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            "Для запуска рентгена не заполнены поля: " + ", ".join(missing)
        )


def run_xray_task(task, controller=None):
    try:
        set_active_controller(controller)
        _validate_xray_task(task)

        log("=" * 60)
        log("[XRAY] Запуск стационарного рентгена")
        log(f"[XRAY] Пациент: {task.fio}")
        log(f"[XRAY] ДР: {task.birth_date}")
        log(f"[XRAY] Дата исследования: {task.study_date}")
        log(f"[XRAY] Исследование: {task.study_name}")
        log(f"[XRAY] Шаблон: {task.template_name} / {task.template_key}")
        log("=" * 60)

        win = find_mis_window()
        checkpoint()

        ok = search_patient(win, task.fio)
        checkpoint()
        if not ok:
            return False

        ok = find_patient_by_birth_date_and_click(win, task.birth_date)
        checkpoint()
        if not ok:
            return False

        ok = open_visit(win, study_date=task.study_date)
        checkpoint()
        if not ok:
            return False

        is_inpatient_flow = handle_inpatient_popup_if_present(win)
        checkpoint()

        if is_inpatient_flow:
            log("[XRAY] Стационарный пациент: обработаны окна стационара")
            log("[XRAY] Обычный post_visit_flow пропущен")
        else:
            ok = handle_post_visit_plus_flow(win)
            checkpoint()
            if not ok:
                return False

        fill_reason_code(win)
        checkpoint()

        fill_goal_complex(win)
        checkpoint()

        ok = open_work_service(win)
        checkpoint()
        if not ok:
            return False

        ok = choose_xray_service(win)
        checkpoint()
        if not ok:
            return False

        ok = open_history_fluoro(win)
        checkpoint()
        if not ok:
            return False

        ok = choose_only_my_templates(win)
        checkpoint()
        if not ok:
            return False

        ok = clear_template_diagnosis_if_exists(win)
        checkpoint()
        if not ok:
            return False

        ok = choose_xray_template(win, task)
        checkpoint()
        if not ok:
            return False

        ok = fill_xray_protocol(win, task)
        checkpoint()
        if not ok:
            return False

        log("[XRAY] Протокол заполнен. Сохраняю/подписываю.")

        ok = fill_template_date_and_sign(win, study_date=task.study_date)
        checkpoint()
        if not ok:
            return False

        if is_inpatient_flow:
            log("[XRAY] Стационарный пациент: закрытие диагноза пропущено")
        else:
            log("[XRAY] Обычный пациент: закрываю диагноз")
            ok = cancel_diagnosis(win)
            checkpoint()
            if not ok:
                return False

        log("[XRAY] Рентген-сценарий завершён успешно")
        return True

    finally:
        set_active_controller(None)