from project.bot_mode1_current import full_run


def run_task(task):
    full_run(
        task.fio,
        task.birth_date,
        study_date=task.study_date,
        mode=task.mode,
        step_mode=False
    )