import time
import threading
import traceback
import json
from pathlib import Path
import ctypes

# ВАЖНО: включаем DPI-awareness до создания первого Tk-окна.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from tkinter import simpledialog

from gui.add_task_dialog import AddTaskDialog
from gui.edit_task_dialog import EditTaskDialog
from gui.coordinates_settings_window import CoordinatesSettingsWindow
from gui.template_settings_window import TemplateSettingsWindow
from gui.defaults_settings_window import DefaultsSettingsWindow
from gui.offset_calibration_window import OffsetCalibrationWindow
from gui.preflight_window import PreflightWindow
from gui.run_until_stage_dialog import RunUntilStageDialog
from gui.click_map_window import ClickMapWindow
from gui.click_map_technical_window import TechnicalClickMapWindow
from gui.progress_window import ProgressWindow
from gui.bulk_import_review_dialog import BulkImportReviewDialog
from gui.xray_review_dialog import XrayReviewDialog
from gui.protocol_settings_window import ProtocolSettingsWindow
from gui.workplace_setup_wizard import WorkplaceSetupWizard

from models.patient_task import PatientTask
from services.xray_template_matcher import match_xray_template
from services.name_corrector import enforce_cyrillic_fio
from services.runtime_paths import CONFIG_DIR

from ocr.stationary_xray_text_parser import parse_stationary_xray_text
from ocr.direction_ocr import parse_direction_image
from ocr.screen_region_capture import capture_screen_region, capture_named_screen_region
from ocr.screen_list_ocr import parse_screen_region
from ocr.two_step_region_ocr import build_task_from_two_regions

from project.xray_flow import run_xray_task, run_xray_from_open_patient_card

from services.task_runner import run_task
from services.mode_mapper import get_internal_to_ui_mode
from services.session_store import save_session, load_session, clear_session
from services.protected_list_store import (
    load_profile, save_profile, verify_profile_password,
    save_protected_list, load_protected_list, peek_owner, ensure_unique_id,
)

from project.run_controller import RunController
from project.browser_ris_flow import run_ris_link
from project.bot_mode1_current import (
    full_run,
    continue_from_open_patient_card,
    set_interactive_click_calibration,
)


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MIS Bot")
        self.root.geometry("1320x740")

        self._ui_settings_path = CONFIG_DIR / "ui_settings.json"
        self.always_on_top_var = tk.BooleanVar(value=self._load_always_on_top_setting())
        self._apply_always_on_top()

        self.tasks = []
        self.task_index = {}

        # Сортировка таблицы.
        # Храним отдельно для каждого режима, чтобы переключение
        # Флюорография/Рентген не сбрасывало выбранный порядок.
        self._sort_state = {
            "fluoro": {"column": None, "reverse": False},
            "xray": {"column": None, "reverse": False},
        }

        # Массовое выделение и фильтры.
        self.checked_task_ids = set()
        self.filter_date_var = tk.StringVar(value="Все")
        self.filter_status_var = tk.StringVar(value="Все")

        self.current_workspace = tk.StringVar(value="fluoro")
        self.interactive_click_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._restore_session()
        self.set_workspace_mode("fluoro")

    def _build_ui(self):
        workspace_frame = ttk.Frame(self.root)
        workspace_frame.pack(fill="x", padx=8, pady=(8, 0))

        ttk.Label(
            workspace_frame,
            text="Режим работы:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            workspace_frame,
            text="Флюорография",
            width=22,
            command=lambda: self.set_workspace_mode("fluoro"),
        ).pack(side="left", padx=4)

        ttk.Button(
            workspace_frame,
            text="Рентген",
            width=22,
            command=lambda: self.set_workspace_mode("xray"),
        ).pack(side="left", padx=4)

        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=8)

        self.add_patient_menu_btn = self._make_menu_button(
            top,
            "Добавить пациента",
            [
                ("Вручную", self.add_task),
                ("Из фото", self.add_task_from_image),
                ("Из области", self.add_task_from_screen_region),
                ("Несколько из одной области", self.add_many_from_one_region),
                None,
                ("Добавить 1 (ФИО + дата)", self.add_one_two_step),
                ("Добавить несколько (ФИО + дата)", self.add_many_two_step),
            ],
        )
        self.add_patient_menu_btn.pack(side="left", padx=4)

        self.add_xray_text_btn = ttk.Button(
            top,
            text="Добавить рентген из текста",
            command=self.add_xray_from_text,
        )
        self.add_xray_text_btn.pack(side="left", padx=4)
        self.add_xray_text_btn.pack_forget()

        self._make_menu_button(
            top,
            "Редактировать запись",
            [
                ("Изменить", self.edit_selected_task),
                ("Удалить", self.delete_selected_task),
            ],
        ).pack(side="left", padx=4)

        self._make_menu_button(
            top,
            "Запуск",
            [
                ("Предполетная проверка", self.open_preflight_window),
                None,
                ("Запустить выбранную", self.run_selected_task),
                ("Запустить до этапа", self.run_selected_until_stage),
                ("Запустить все", self.run_all_tasks),
                ("Из открытой карточки", self.run_selected_open_card),
                ("Связать в РИС", self.run_selected_ris_link),
            ],
        ).pack(side="left", padx=4)

        self._make_menu_button(
            top,
            "Списки",
            [
                ("Сохранить текущий список", self.save_protected_task_list),
                ("Добавить сохранённый список", self.add_protected_task_list),
                None,
                ("Профиль списка", self.configure_list_profile),
            ],
        ).pack(side="left", padx=4)

        self._make_menu_button(
            top,
            "Настройки",
            [
                ("Выбрать окно МИС", self.pick_mis_window),
                None,
                ("Первоначальная настройка рабочего места", self.open_workplace_setup_wizard),
                ("Коррекция рабочего места", self.open_click_map),
                ("Карта кликов", self.open_technical_click_map),
                None,
                ("Шаблоны", self.open_template_settings),
                ("Протоколы", self.open_protocol_settings),
                ("Параметры по умолчанию", self.open_defaults_settings),
                None,
                ("Сохранить сессию", self.save_session_now),
                ("Очистить сессию", self.clear_saved_session),
            ],
        ).pack(side="left", padx=4)

        ttk.Checkbutton(
            top,
            text="Интерактивная настройка кликов",
            variable=self.interactive_click_var,
            command=self._on_interactive_click_toggle,
        ).pack(side="left", padx=(14, 4))

        ttk.Checkbutton(
            top,
            text="Поверх всех окон",
            variable=self.always_on_top_var,
            command=self._on_always_on_top_toggle,
        ).pack(side="left", padx=(14, 4))

        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(fill="x", padx=8, pady=(0, 4))

        ttk.Label(filter_frame, text="Дата исследования:").pack(side="left")

        self.filter_date_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_date_var,
            state="readonly",
            width=14,
        )
        self.filter_date_combo.pack(side="left", padx=(4, 10))
        self.filter_date_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        ttk.Label(filter_frame, text="Статус:").pack(side="left")

        self.filter_status_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_status_var,
            state="readonly",
            width=18,
        )
        self.filter_status_combo.pack(side="left", padx=(4, 10))
        self.filter_status_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        ttk.Button(
            filter_frame,
            text="✓ Выбрать показанных",
            command=self.check_all_visible,
        ).pack(side="left", padx=4)

        ttk.Button(
            filter_frame,
            text="Снять выбор",
            command=self.uncheck_all,
        ).pack(side="left", padx=4)

        ttk.Button(
            filter_frame,
            text="Запустить отмеченных",
            command=self.run_checked_tasks,
        ).pack(side="left", padx=(14, 4))

        ttk.Button(
            filter_frame,
            text="Удалить отмеченных",
            command=self.delete_checked_tasks,
        ).pack(side="left", padx=4)

        self.checked_count_label = ttk.Label(filter_frame, text="Выбрано: 0")
        self.checked_count_label.pack(side="right")

        self.tree = ttk.Treeview(self.root, columns=(), show="headings", height=18)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)


        self.tree.bind("<Button-1>", self._on_tree_click, add="+")
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        self.tree.tag_configure("needs_fix", background="#fff2a8")
        self.tree.tag_configure("error_row", background="#ffd6d6")

        self._build_context_menu()
        self._rebuild_tree_columns()

        log_frame = ttk.LabelFrame(self.root, text="Лог")
        log_frame.pack(fill="both", expand=False, padx=8, pady=8)

        self.log_text = tk.Text(log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def set_workspace_mode(self, mode: str):
        if mode not in ("fluoro", "xray"):
            return

        self.current_workspace.set(mode)

        if mode == "fluoro":
            self.log("Переключение интерфейса: Флюорография")
            self.add_patient_menu_btn.pack(side="left", padx=4)
            self.add_xray_text_btn.pack_forget()
        else:
            self.log("Переключение интерфейса: Рентген")
            self.add_patient_menu_btn.pack_forget()
            self.add_xray_text_btn.pack(side="left", padx=4)

        self.filter_date_var.set("Все")
        self.filter_status_var.set("Все")
        self._rebuild_tree_columns()
        self._reload_tree_rows()

    def _rebuild_tree_columns(self):
        mode = self.current_workspace.get()

        if mode == "xray":
            columns = (
                "checked",
                "fio",
                "birth_date",
                "study_date",
                "study_name",
                "dose",
                "template_name",
                "status",
                "description",
                "conclusion",
            )
            headers = {
                "checked": "✓",
                "fio": "ФИО",
                "birth_date": "Дата рождения",
                "study_date": "Дата исследования",
                "study_name": "Исследование",
                "dose": "Доза",
                "template_name": "Шаблон",
                "status": "Статус",
                "description": "Описание",
                "conclusion": "Заключение",
            }
            widths = {
                "checked": 60,
                "fio": 240,
                "birth_date": 110,
                "study_date": 125,
                "study_name": 190,
                "dose": 75,
                "template_name": 160,
                "status": 110,
                "description": 250,
                "conclusion": 250,
            }
        else:
            columns = (
                "checked",
                "fio",
                "birth_date",
                "study_date",
                "mode",
                "status",
                "note",
            )
            headers = {
                "checked": "✓",
                "fio": "ФИО",
                "birth_date": "Дата рождения",
                "study_date": "Дата исследования",
                "mode": "Протокол",
                "status": "Статус",
                "note": "Примечание",
            }
            widths = {
                "checked": 60,
                "fio": 280,
                "birth_date": 110,
                "study_date": 130,
                "mode": 150,
                "status": 130,
                "note": 260,
            }

        self.tree["columns"] = columns

        sortable_columns = {
            "fio",
            "birth_date",
            "study_date",
            "status",
        }

        current_sort = self._sort_state.get(mode, {})
        active_col = current_sort.get("column")
        active_reverse = bool(current_sort.get("reverse"))

        for col in columns:
            header_text = headers.get(col, col)

            # Небольшой визуальный индикатор активной сортировки.
            if col == active_col:
                header_text += " ▼" if active_reverse else " ▲"

            if col in sortable_columns:
                self.tree.heading(
                    col,
                    text=header_text,
                    command=lambda c=col: self._sort_tree_by_column(c),
                )
            else:
                self.tree.heading(col, text=header_text)

            self.tree.column(col, width=widths.get(col, 120), anchor="w")

        for col in ("checked", "birth_date", "study_date", "dose", "status", "mode", "template_name"):
            if col in columns:
                self.tree.column(col, anchor="center")

        if "checked" in columns:
            self.tree.column("checked", width=60, minwidth=60, stretch=False, anchor="center")

    def _reload_tree_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        current = self.current_workspace.get()

        visible_tasks = [
            task
            for task in self.tasks
            if getattr(task, "task_type", "fluoro") == current
            and self._task_matches_filters(task)
        ]

        visible_tasks = self._sorted_tasks_for_current_view(visible_tasks)

        for task in visible_tasks:
            self._insert_task_to_tree(task)

        self._refresh_filter_values()
        self._update_checked_count()

    def _all_current_workspace_tasks(self):
        current = self.current_workspace.get()
        return [
            task for task in self.tasks
            if getattr(task, "task_type", "fluoro") == current
        ]

    def _refresh_filter_values(self):
        current_tasks = self._all_current_workspace_tasks()

        dates = sorted(
            {
                str(getattr(task, "study_date", "") or "").strip()
                for task in current_tasks
                if str(getattr(task, "study_date", "") or "").strip()
            },
            key=lambda value: self._parse_sort_date(value),
        )

        statuses = sorted(
            {
                str(getattr(task, "status", "") or "").strip()
                for task in current_tasks
                if str(getattr(task, "status", "") or "").strip()
            },
            key=self._status_sort_key,
        )

        date_values = ["Все"] + dates
        status_values = ["Все"] + statuses

        self.filter_date_combo["values"] = date_values
        self.filter_status_combo["values"] = status_values

        if self.filter_date_var.get() not in date_values:
            self.filter_date_var.set("Все")

        if self.filter_status_var.get() not in status_values:
            self.filter_status_var.set("Все")

    def _task_matches_filters(self, task: PatientTask) -> bool:
        date_filter = self.filter_date_var.get()
        status_filter = self.filter_status_var.get()

        if date_filter != "Все":
            if str(getattr(task, "study_date", "") or "").strip() != date_filter:
                return False

        if status_filter != "Все":
            if str(getattr(task, "status", "") or "").strip() != status_filter:
                return False

        return True

    def _apply_filters(self):
        self._reload_tree_rows()

    def _visible_task_ids(self):
        return set(self.tree.get_children())

    def _update_checked_count(self):
        # Чистим IDs удалённых задач.
        valid_ids = set(self.task_index.keys())
        self.checked_task_ids.intersection_update(valid_ids)
        self.checked_count_label.config(text=f"Выбрано: {len(self.checked_task_ids)}")

    def check_all_visible(self):
        self.checked_task_ids.update(self._visible_task_ids())
        self._reload_tree_rows()

    def uncheck_all(self):
        self.checked_task_ids.clear()
        self._reload_tree_rows()

    def _toggle_task_checked(self, task_id: str):
        if task_id in self.checked_task_ids:
            self.checked_task_ids.remove(task_id)
        else:
            self.checked_task_ids.add(task_id)

        if self.tree.exists(task_id):
            task = self.task_index.get(task_id)
            if task:
                self._refresh_task_in_tree(task)

        self._update_checked_count()

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        if not row_id or not column_id:
            return

        try:
            column_index = int(column_id.replace("#", "")) - 1
            columns = list(self.tree["columns"])
            column_name = columns[column_index]
        except Exception:
            return

        if column_name == "checked":
            self._toggle_task_checked(row_id)
            return "break"

    def _checked_tasks_for_current_workspace(self):
        current = self.current_workspace.get()
        tasks = [
            task
            for task in self.tasks
            if task.id in self.checked_task_ids
            and getattr(task, "task_type", "fluoro") == current
        ]
        return tasks

    def delete_checked_tasks(self):
        tasks = self._checked_tasks_for_current_workspace()

        if not tasks:
            messagebox.showinfo("Информация", "Нет отмеченных пациентов")
            return

        if not messagebox.askyesno(
            "Удаление",
            f"Удалить отмеченные записи: {len(tasks)}?",
        ):
            return

        ids = {task.id for task in tasks}

        self.tasks = [task for task in self.tasks if task.id not in ids]

        for task_id in ids:
            self.task_index.pop(task_id, None)
            self.checked_task_ids.discard(task_id)

        self._autosave_session()
        self._reload_tree_rows()
        self.log(f"Удалено отмеченных записей: {len(ids)}")

    def run_checked_tasks(self):
        tasks = self._checked_tasks_for_current_workspace()

        runnable = [
            task
            for task in tasks
            if task.status in ("pending", "error", "cancelled")
            and task.birth_date != "ЗАМЕНИТЬ"
        ]

        if not runnable:
            messagebox.showinfo(
                "Информация",
                "Среди отмеченных нет записей, готовых к запуску",
            )
            return

        set_interactive_click_calibration(self.interactive_click_var.get())

        controller = RunController()
        controller.set_total(len(runnable))

        progress = ProgressWindow(
            self.root,
            controller,
            total_count=len(runnable),
        )
        self.root.update()

        self._hide_main_for_run_all()

        thread = threading.Thread(
            target=self._run_all_tasks_worker,
            args=(runnable, controller, progress),
            daemon=True,
        )
        thread.start()

    def _status_display_name(self, status: str) -> str:
        names = {
            "pending": "Ожидает",
            "pending_fix": "Требует проверки",
            "running": "Выполняется",
            "stage_running": "Выполняется до этапа",
            "open_card_running": "Открывается карта",
            "ris_running": "Отправляется в RIS",
            "error": "Ошибка",
            "stage_error": "Ошибка этапа",
            "open_card_error": "Ошибка открытия карты",
            "ris_error": "Ошибка RIS",
            "cancelled": "Отменено",
            "done": "Готово",
            "stage_done": "Этап выполнен",
            "open_card_done": "Карта открыта",
            "ris_done": "RIS выполнен",
        }
        value = str(status or "").strip()
        return names.get(value, value or "Ожидает")

    def _manual_status_choices(self):
        # Основные статусы, которые действительно имеет смысл выставлять вручную.
        # Технические промежуточные статусы worker-а намеренно не предлагаем.
        return [
            ("pending", "Ожидает"),
            ("pending_fix", "Требует проверки"),
            ("done", "Готово"),
            ("error", "Ошибка"),
            ("cancelled", "Отменено"),
        ]

    def _show_manual_status_menu(self, task: PatientTask, event):
        menu = tk.Menu(self.root, tearoff=0)

        current_status = str(getattr(task, "status", "pending") or "pending")

        for status_code, label in self._manual_status_choices():
            text = label
            if status_code == current_status:
                text = f"✓ {label}"

            menu.add_command(
                label=text,
                command=lambda code=status_code: self._set_manual_task_status(
                    task,
                    code,
                ),
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _set_manual_task_status(self, task: PatientTask, new_status: str):
        old_status = str(getattr(task, "status", "pending") or "pending")

        if old_status == new_status:
            return

        task.status = new_status

        # Если вручную возвращаем пациента в очередь, убираем старую ошибку,
        # чтобы запись выглядела как действительно готовая к повторному запуску.
        if new_status in {"pending", "pending_fix"}:
            task.last_error = None

        self._reload_tree_rows()

        self.log(
            "Статус изменён вручную: "
            f"{task.fio}: "
            f"{self._status_display_name(old_status)} -> "
            f"{self._status_display_name(new_status)}"
        )

    def _parse_sort_date(self, value):
        text = str(value or "").strip()

        if not text or text == "ЗАМЕНИТЬ":
            return (1, datetime.max)

        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
            try:
                return (0, datetime.strptime(text, fmt))
            except ValueError:
                continue

        # Нераспознанные значения уводим вниз, но сортировка не падает.
        return (1, datetime.max)

    def _status_sort_key(self, value):
        status = str(value or "").strip().lower()

        order = {
            "pending": 10,
            "pending_fix": 20,
            "running": 30,
            "stage_running": 31,
            "open_card_running": 32,
            "ris_running": 33,

            "error": 40,
            "stage_error": 41,
            "open_card_error": 42,
            "ris_error": 43,

            "cancelled": 50,

            "done": 60,
            "stage_done": 61,
            "open_card_done": 62,
            "ris_done": 63,
        }

        return (order.get(status, 999), status)

    def _task_sort_key(self, task: PatientTask, column: str):
        if column == "fio":
            return str(getattr(task, "fio", "") or "").casefold()

        if column == "birth_date":
            return self._parse_sort_date(getattr(task, "birth_date", ""))

        if column == "study_date":
            return self._parse_sort_date(getattr(task, "study_date", ""))

        if column == "status":
            return self._status_sort_key(getattr(task, "status", ""))

        return ""

    def _sorted_tasks_for_current_view(self, tasks):
        mode = self.current_workspace.get()
        state = self._sort_state.get(mode, {})
        column = state.get("column")
        reverse = bool(state.get("reverse"))

        if not column:
            return list(tasks)

        try:
            return sorted(
                tasks,
                key=lambda task: self._task_sort_key(task, column),
                reverse=reverse,
            )
        except Exception as e:
            self.log(f"Ошибка сортировки по {column}: {e}")
            return list(tasks)

    def _sort_tree_by_column(self, column: str):
        mode = self.current_workspace.get()
        state = self._sort_state.setdefault(
            mode,
            {"column": None, "reverse": False},
        )

        if state.get("column") == column:
            state["reverse"] = not bool(state.get("reverse"))
        else:
            state["column"] = column
            state["reverse"] = False

        self._rebuild_tree_columns()
        self._reload_tree_rows()

        direction = "по убыванию" if state["reverse"] else "по возрастанию"
        labels = {
            "fio": "ФИО",
            "birth_date": "дате рождения",
            "study_date": "дате исследования",
            "status": "статусу",
        }
        self.log(
            f"Сортировка по {labels.get(column, column)}: {direction}"
        )

    def _short_text(self, value: str, limit: int = 70):
        if not value:
            return ""
        value = str(value).replace("\n", " ").strip()
        return value[:limit] + "..." if len(value) > limit else value

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=False)
        self.context_menu.add_command(label="Изменить", command=self.edit_selected_task)
        self.context_menu.add_command(label="Удалить", command=self.delete_selected_task)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Запустить выбранную", command=self.run_selected_task)
        self.context_menu.add_command(label="Запустить до этапа", command=self.run_selected_until_stage)
        self.context_menu.add_command(label="Связать в РИС", command=self.run_selected_ris_link)
        self.context_menu.add_command(label="Из открытой карточки", command=self.run_selected_open_card)

    def _on_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def _make_menu_button(self, parent, text, items):
        btn = ttk.Menubutton(parent, text=text)
        menu = tk.Menu(btn, tearoff=False)

        for item in items:
            if item is None:
                menu.add_separator()
                continue

            label, command = item
            menu.add_command(label=label, command=command)

        btn["menu"] = menu
        return btn

    def _load_always_on_top_setting(self) -> bool:
        try:
            if not self._ui_settings_path.exists():
                return True
            data = json.loads(self._ui_settings_path.read_text(encoding="utf-8"))
            return bool(data.get("always_on_top", True))
        except Exception:
            return True

    def _save_always_on_top_setting(self):
        try:
            self._ui_settings_path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if self._ui_settings_path.exists():
                try:
                    data = json.loads(self._ui_settings_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            data["always_on_top"] = bool(self.always_on_top_var.get())
            self._ui_settings_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self.log(f"Не удалось сохранить настройку 'Поверх всех окон': {e}")

    def _apply_always_on_top(self):
        try:
            self.root.attributes("-topmost", bool(self.always_on_top_var.get()))
        except Exception:
            pass

    def _on_always_on_top_toggle(self):
        self._apply_always_on_top()
        self._save_always_on_top_setting()
        state = "ВКЛ" if self.always_on_top_var.get() else "ВЫКЛ"
        self.log(f"Поверх всех окон: {state}")

    def _hide_main_for_run_all(self):
        try:
            self.root.withdraw()
            self.root.update_idletasks()
        except Exception:
            pass

    def _restore_main_after_run_all(self):
        try:
            self.root.deiconify()
            self._apply_always_on_top()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def _on_interactive_click_toggle(self):
        set_interactive_click_calibration(self.interactive_click_var.get())
        state = "ВКЛ" if self.interactive_click_var.get() else "ВЫКЛ"
        self.log(f"Интерактивная настройка кликов: {state}")

    def pick_mis_window(self):
        import ctypes
        import time
        from ctypes import wintypes
        from config.loader import load_json, save_json

        user32 = ctypes.windll.user32

        VK_LBUTTON = 0x01
        VK_ESCAPE = 0x1B
        GA_ROOT = 2

        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int

        def pressed(vk):
            return bool(user32.GetAsyncKeyState(vk) & 0x8000)

        def window_title(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value.strip()

        self.log(
            "Выбор окна МИС: кликните мышью по нужному окну "
            "удалённого подключения. Esc — отмена."
        )

        started = time.time()
        while pressed(VK_LBUTTON) and time.time() - started < 2.0:
            self.root.update()
            time.sleep(0.01)

        try:
            while True:
                self.root.update()

                if pressed(VK_ESCAPE):
                    while pressed(VK_ESCAPE):
                        self.root.update()
                        time.sleep(0.01)
                    self.log("Выбор окна МИС отменён")
                    return

                if pressed(VK_LBUTTON):
                    point = wintypes.POINT()
                    if not user32.GetCursorPos(ctypes.byref(point)):
                        self.log("Не удалось получить позицию мыши")
                        return

                    hwnd = user32.WindowFromPoint(point)
                    if not hwnd:
                        self.log("Не удалось определить окно под курсором")
                        return

                    root_hwnd = user32.GetAncestor(hwnd, GA_ROOT) or hwnd
                    title = window_title(root_hwnd)

                    while pressed(VK_LBUTTON):
                        self.root.update()
                        time.sleep(0.01)

                    if not title:
                        self.log("У выбранного окна нет заголовка. Повторите выбор.")
                        continue

                    data = load_json("settings.json")
                    data.setdefault("mis", {})
                    data["mis"]["window_title"] = title

                    # Старые фиксированные параметры монитора больше не нужны.
                    # Монитор и его разрешение определяются автоматически каждый раз.
                    data["mis"].pop("selected_monitor_rect", None)
                    data["mis"].pop("selected_monitor_click", None)

                    save_json("settings.json", data)

                    self.log(f"Окно МИС сохранено: {title}")
                    self.log(
                        "Монитор МИС будет определяться автоматически "
                        "по текущему положению этого окна."
                    )
                    return

                time.sleep(0.01)

        except Exception as e:
            self.log(f"Ошибка выбора окна МИС: {e}")

    def log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def _autosave_session(self):
        try:
            path = save_session(self.tasks)
            return path
        except Exception as e:
            err_text = str(e)
            self.root.after(
                0,
                lambda err_text=err_text: self.log(
                    f"Ошибка автосохранения сессии: {err_text}"
                ),
            )
            return None

    def _restore_session(self):
        try:
            restored = load_session()
        except Exception as e:
            self.log(f"Ошибка загрузки сессии: {e}")
            return

        if not restored:
            self.log("Сохранённая сессия не найдена")
            return

        self.tasks = restored
        self.task_index = {}

        for task in self.tasks:
            self.task_index[task.id] = task

        self.log(f"Сессия восстановлена: {len(self.tasks)} записей")
        self._reload_tree_rows()

    def _add_task_object(self, task: PatientTask):
        if not getattr(task, "task_type", None):
            task.task_type = self.current_workspace.get()

        # Последняя защитная граница для ФИО:
        # в таблицу и дальше в МИС не пропускаем латиницу/спецсимволы.
        original_fio = str(getattr(task, "fio", "") or "")
        task.fio = enforce_cyrillic_fio(original_fio)

        if original_fio != task.fio:
            self.log(
                f"ФИО нормализовано: {original_fio!r} -> {task.fio!r}"
            )

        self.tasks.append(task)
        self.task_index[task.id] = task

        if task.task_type == self.current_workspace.get():
            self._insert_task_to_tree(task)

    def _get_task_tags(self, task: PatientTask):
        tags = []
        if task.status == "pending_fix" or task.birth_date == "ЗАМЕНИТЬ":
            tags.append("needs_fix")
        if "error" in str(task.status):
            tags.append("error_row")
        return tuple(tags)

    def _can_run_task(self, task: PatientTask) -> bool:
        if task.status == "pending_fix" or task.birth_date == "ЗАМЕНИТЬ":
            messagebox.showwarning(
                "Нужно исправление",
                "У записи не распознана дата рождения.\nСначала открой 'Изменить' и укажи правильную дату.",
            )
            self.log(f"Запуск заблокирован: {task.fio} требует исправления даты рождения")
            return False
        return True

    def _insert_task_to_tree(self, task: PatientTask):
        workspace = self.current_workspace.get()

        if workspace == "xray":
            values = (
                "☑" if task.id in self.checked_task_ids else "☐",
                task.fio,
                task.birth_date,
                task.study_date,
                task.study_name,
                task.dose,
                task.template_name or task.template_key or "",
                task.status,
                self._short_text(task.description),
                self._short_text(task.conclusion),
            )
        else:
            values = (
                "☑" if task.id in self.checked_task_ids else "☐",
                task.fio,
                task.birth_date,
                task.study_date,
                get_internal_to_ui_mode().get(task.mode, task.mode),
                task.status,
                task.note or "",
            )

        self.tree.insert(
            "",
            "end",
            iid=task.id,
            values=values,
            tags=self._get_task_tags(task),
        )

    def _refresh_task_in_tree(self, task: PatientTask):
        if not self.tree.exists(task.id):
            return

        workspace = self.current_workspace.get()

        if workspace == "xray":
            values = (
                "☑" if task.id in self.checked_task_ids else "☐",
                task.fio,
                task.birth_date,
                task.study_date,
                task.study_name,
                task.dose,
                task.template_name or task.template_key or "",
                task.status,
                self._short_text(task.description),
                self._short_text(task.conclusion),
            )
        else:
            values = (
                "☑" if task.id in self.checked_task_ids else "☐",
                task.fio,
                task.birth_date,
                task.study_date,
                get_internal_to_ui_mode().get(task.mode, task.mode),
                task.status,
                task.note or "",
            )

        self.tree.item(
            task.id,
            values=values,
            tags=self._get_task_tags(task),
        )

    def configure_list_profile(self):
        current = load_profile() or {}
        fio = simpledialog.askstring(
            "Профиль списка", "ФИО:", initialvalue=current.get("fio", ""), parent=self.root
        )
        if not fio:
            return
        password = simpledialog.askstring(
            "Профиль списка", "Пароль:", show="*", parent=self.root
        )
        if not password:
            return
        password2 = simpledialog.askstring(
            "Профиль списка", "Повторите пароль:", show="*", parent=self.root
        )
        if password != password2:
            messagebox.showerror("Ошибка", "Пароли не совпадают", parent=self.root)
            return
        try:
            save_profile(fio, password)
            self.log(f"Профиль защищённых списков сохранён: {fio}")
            messagebox.showinfo("Готово", "Профиль сохранён. Сам пароль на диске не хранится.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self.root)

    def save_protected_task_list(self):
        if not self.tasks:
            messagebox.showinfo("Список пуст", "Нет записей для сохранения", parent=self.root)
            return
        profile = load_profile()
        if not profile:
            messagebox.showinfo("Нужен профиль", "Сначала создайте профиль списка.", parent=self.root)
            self.configure_list_profile()
            profile = load_profile()
            if not profile:
                return
        password = simpledialog.askstring("Сохранение списка", f"Пароль профиля {profile['fio']}:", show="*", parent=self.root)
        if not password:
            return
        if not verify_profile_password(password):
            messagebox.showerror("Ошибка", "Неверный пароль профиля", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить список исследований", defaultextension=".mislist",
            filetypes=[("Защищённый список MIS Bot", "*.mislist")],
            initialfile=f"MIS_list_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.mislist",
        )
        if not path:
            return
        try:
            save_protected_list(path, self.tasks, profile["fio"], password)
            self.log(f"Сохранён защищённый список: {len(self.tasks)} записей")
            messagebox.showinfo("Сохранено", f"Сохранено записей: {len(self.tasks)}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e), parent=self.root)

    def add_protected_task_list(self):
        path = filedialog.askopenfilename(
            title="Добавить сохранённый список",
            filetypes=[("Защищённый список MIS Bot", "*.mislist"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            owner = peek_owner(path)
        except Exception as e:
            messagebox.showerror("Ошибка файла", str(e), parent=self.root)
            return
        fio = simpledialog.askstring("Открытие списка", "ФИО профиля:", initialvalue=owner, parent=self.root)
        if not fio:
            return
        password = simpledialog.askstring("Открытие списка", "Пароль:", show="*", parent=self.root)
        if not password:
            return
        try:
            imported = load_protected_list(path, fio, password)
            existing = set(self.task_index.keys())
            for task in imported:
                ensure_unique_id(task, existing)
                existing.add(task.id)
                self._add_task_object(task)
            self._autosave_session()
            self._reload_tree_rows()
            self.log(f"Добавлен сохранённый список: {len(imported)} записей | профиль: {owner}")
            messagebox.showinfo("Готово", f"Добавлено записей: {len(imported)}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Не удалось открыть список", str(e), parent=self.root)

    def save_session_now(self):
        path = self._autosave_session()
        if path:
            self.log(f"Сессия сохранена: {path}")
            messagebox.showinfo("Сохранено", "Сессия сохранена.")

    def clear_saved_session(self):
        confirm = messagebox.askyesno(
            "Подтверждение",
            "Очистить сохранённую сессию?\nЭто удалит файл восстановления и очистит список записей.",
        )
        if not confirm:
            return

        try:
            clear_session()

            self.tasks.clear()
            self.task_index.clear()

            for item in self.tree.get_children():
                self.tree.delete(item)

            self.log_text.delete("1.0", "end")
            self.log("Сохранённая сессия очищена. Список исследований очищен.")

            messagebox.showinfo("Готово", "Сохранённая сессия и список исследований очищены.")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def open_coordinates_settings(self):
        CoordinatesSettingsWindow(self.root, on_saved=lambda: self.log("coordinates.json обновлён"))

    def open_template_settings(self):
        TemplateSettingsWindow(self.root, on_saved=lambda: self.log("templates.json / PNG обновлены"))

    def open_protocol_settings(self):
        def on_saved():
            self.log("protocols.json / связанные шаблоны обновлены")
            self._reload_tree_rows()

        ProtocolSettingsWindow(self.root, on_saved=on_saved)

    def open_workplace_setup_wizard(self):
        WorkplaceSetupWizard(
            self.root,
            on_saved=lambda: self.log(
                "Мастер рабочего места: templates.json / coordinates.json обновлены"
            ),
        )

    def open_defaults_settings(self):
        DefaultsSettingsWindow(self.root, on_saved=lambda: self.log("Default-настройки обновлены"))

    def open_offset_calibration(self):
        OffsetCalibrationWindow(self.root, on_saved=lambda: self.log("Offset сохранён в coordinates.json"))

    def open_preflight_window(self):
        PreflightWindow(self.root)

    def open_click_map(self):
        ClickMapWindow(self.root, on_saved=lambda: self.log("Коррекция рабочего места: настройки обновлены"))

    def open_technical_click_map(self):
        try:
            TechnicalClickMapWindow(
                self.root,
                on_saved=lambda: self.log("Карта кликов: настройки обновлены"),
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть техническую карту кликов:\n{e}",
            )

    def add_xray_from_text(self):
        win = tk.Toplevel(self.root)
        win.title("Добавить рентген из текста")
        win.geometry("900x650")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(
            win,
            text="Вставьте текст протокола:",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 4))

        text_box = tk.Text(win, wrap="word", height=24, undo=True)
        text_box.pack(fill="both", expand=True, padx=10, pady=8)
        text_box.focus_set()

        paste_menu = tk.Menu(text_box, tearoff=False)

        def paste_from_clipboard(event=None):
            try:
                text = win.clipboard_get()
                text_box.insert("insert", text)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось вставить из буфера:\n{e}", parent=win)
            return "break"

        def copy_selection(event=None):
            try:
                value = text_box.get("sel.first", "sel.last")
            except tk.TclError:
                return "break"
            win.clipboard_clear()
            win.clipboard_append(value)
            return "break"

        def cut_selection(event=None):
            copy_selection()
            try:
                text_box.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            return "break"

        def select_all(event=None):
            text_box.tag_add("sel", "1.0", "end-1c")
            return "break"

        def show_context_menu(event):
            text_box.focus_set()
            paste_menu.delete(0, "end")
            paste_menu.add_command(label="Вырезать", command=cut_selection)
            paste_menu.add_command(label="Копировать", command=copy_selection)
            paste_menu.add_command(label="Вставить", command=paste_from_clipboard)
            paste_menu.add_separator()
            paste_menu.add_command(label="Выделить всё", command=select_all)
            try:
                paste_menu.tk_popup(event.x_root, event.y_root)
            finally:
                paste_menu.grab_release()
            return "break"

        for seq in ("<Control-c>", "<Control-C>"):
            text_box.bind(seq, copy_selection)
        for seq in ("<Control-x>", "<Control-X>"):
            text_box.bind(seq, cut_selection)
        for seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
            text_box.bind(seq, paste_from_clipboard)
        for seq in ("<Control-a>", "<Control-A>"):
            text_box.bind(seq, select_all)
        text_box.bind("<Button-3>", show_context_menu)

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        def parse_and_review():
            raw_text = text_box.get("1.0", "end").strip()

            if not raw_text:
                messagebox.showwarning("Пусто", "Вставьте текст протокола", parent=win)
                return

            try:
                task = parse_stationary_xray_text(raw_text)
                matched = match_xray_template(task.study_name)

                task.template_key = matched.get("template_key", "") or ""
                task.template_name = matched.get("template_name", "") or ""

                if task.template_name:
                    task.note = f"Шаблон: {task.template_name}"

            except Exception as e:
                messagebox.showerror("Ошибка парсинга", str(e), parent=win)
                return

            review = XrayReviewDialog(self.root, task)
            self.root.wait_window(review)

            if review.result is None:
                return

            self._add_task_object(review.result)
            self._autosave_session()

            self.log(
                f"Рентген: добавлен протокол: "
                f"{review.result.fio} | {review.result.birth_date} | "
                f"{review.result.study_name} | шаблон: {review.result.template_name or review.result.template_key or '-'}"
            )

            win.destroy()

        ttk.Button(
            btns,
            text="Вставить из буфера",
            width=18,
            command=paste_from_clipboard,
        ).pack(side="left", padx=4)

        ttk.Button(
            btns,
            text="Отмена",
            width=18,
            command=win.destroy,
        ).pack(side="right", padx=4)

        ttk.Button(
            btns,
            text="Распознать",
            width=18,
            command=parse_and_review,
        ).pack(side="right", padx=4)

    def add_task(self):
        dialog = AddTaskDialog(self.root)
        self.root.wait_window(dialog)

        if dialog.result is None:
            return

        task = dialog.result
        task.task_type = "fluoro"

        self._add_task_object(task)
        self._autosave_session()
        self.log(f"Добавлена запись: {task.fio}")

    def add_task_from_image(self):
        path = filedialog.askopenfilename(
            title="Выбери изображение направления",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.bmp"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return

        try:
            task = parse_direction_image(path, mode="normal")
            task.source = "image"
            task.status = "pending"
            task.task_type = "fluoro"

            self._add_task_object(task)
            self._autosave_session()

            self.log(f"OCR: добавлена запись из фото: {task.fio}")
        except Exception as e:
            messagebox.showerror("OCR ошибка", str(e))
            self.log(f"OCR ошибка: {e}")

    def add_task_from_screen_region(self):
        self.root.iconify()
        self.root.update()

        try:
            path = capture_screen_region(self.root)
        finally:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        if not path:
            self.log("Выделение области отменено")
            return

        try:
            result = parse_screen_region(path, mode="normal")

            if isinstance(result, list):
                for task in result:
                    task.source = "screen"
                    task.status = "pending"
                    task.task_type = "fluoro"
                    self._add_task_object(task)

                self._autosave_session()
                self.log(f"OCR экрана: добавлено записей: {len(result)}")
            else:
                task = result
                task.source = "screen"
                task.status = "pending"
                task.task_type = "fluoro"
                self._add_task_object(task)

                self._autosave_session()
                self.log(f"OCR экрана: добавлена запись: {task.fio}")

        except Exception as e:
            messagebox.showerror("OCR ошибка", str(e))
            self.log(f"OCR ошибка области экрана: {e}")

    def add_many_from_one_region(self):
        default_study_date = datetime.now().strftime("%d.%m.%Y")

        study_date = simpledialog.askstring(
            "Дата исследования",
            "Введите дату исследования для всех распознанных пациентов (дд.мм.гггг):",
            initialvalue=default_study_date,
            parent=self.root,
        )
        if not study_date:
            self.log("Массовое OCR из одной области отменено: дата не указана")
            return

        self.root.iconify()
        self.root.update()

        try:
            path = capture_screen_region(self.root)
        finally:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        if not path:
            self.log("Выделение области отменено")
            return

        try:
            result = parse_screen_region(path, mode="normal")

            if not isinstance(result, list):
                result = [result]

            for task in result:
                task.study_date = study_date
                task.mode = getattr(task, "mode", None) or "normal"
                task.source = "screen"
                task.status = "pending"
                task.task_type = "fluoro"

            review = BulkImportReviewDialog(self.root, result)
            self.root.wait_window(review)

            if review.result is None:
                self.log("Массовый импорт из одной области отменён на этапе проверки")
                return

            added = 0
            for task in review.result:
                task.task_type = "fluoro"
                self._add_task_object(task)
                added += 1

            self._autosave_session()
            self.log(f"Массовый OCR из одной области: добавлено записей {added}")

        except Exception as e:
            messagebox.showerror("OCR ошибка", str(e))
            self.log(f"Массовый OCR из одной области: ошибка {e}")

    def add_one_two_step(self):
        default_study_date = datetime.now().strftime("%d.%m.%Y")

        self.root.iconify()
        self.root.update()

        try:
            fio_path = capture_named_screen_region(self.root, "Выделите ФИО", rect_color="blue")
            if not fio_path:
                return

            birth_path = capture_named_screen_region(self.root, "Выделите дату рождения", rect_color="green")
            if not birth_path:
                return
        finally:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

        try:
            task = build_task_from_two_regions(fio_path, birth_path, mode="normal")
            task.study_date = default_study_date
            task.task_type = "fluoro"

            self._add_task_object(task)
            self._autosave_session()
            self.log(
                f"Двухмоментный OCR: добавлена запись: "
                f"{task.fio} | {task.birth_date} | дата исследования: {task.study_date}"
            )
        except Exception as e:
            messagebox.showerror("OCR ошибка", str(e))
            self.log(f"Двухмоментный OCR ошибка: {e}")

    def add_many_two_step(self):
        default_study_date = datetime.now().strftime("%d.%m.%Y")

        study_date = simpledialog.askstring(
            "Дата исследования",
            "Введите дату исследования для всех добавляемых пациентов (дд.мм.гггг):",
            initialvalue=default_study_date,
            parent=self.root,
        )

        if not study_date:
            self.log("Массовое добавление отменено: дата исследования не указана")
            return

        added = 0

        while True:
            self.root.iconify()
            self.root.update()

            try:
                fio_path = capture_named_screen_region(self.root, "Выделите ФИО", rect_color="blue")
                if not fio_path:
                    break

                birth_path = capture_named_screen_region(self.root, "Выделите дату рождения", rect_color="green")
                if not birth_path:
                    break
            finally:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()

            try:
                task = build_task_from_two_regions(fio_path, birth_path, mode="normal")
                task.study_date = study_date
                task.task_type = "fluoro"

                self._add_task_object(task)
                added += 1
                self._autosave_session()
                self.log(
                    f"Двухмоментный OCR: добавлена запись: "
                    f"{task.fio} | {task.birth_date} | дата исследования: {task.study_date}"
                )
            except Exception as e:
                messagebox.showerror("OCR ошибка", str(e))
                self.log(f"Двухмоментный OCR ошибка: {e}")
                break

            cont = messagebox.askyesno("Продолжить", "Добавить следующего пациента?")
            if not cont:
                study_date = default_study_date
                self.log(f"Массовое добавление завершено. Дата исследования сброшена на дефолтную: {study_date}")
                break

        if added:
            self.log(f"Двухмоментный OCR: всего добавлено {added} записей")

    def edit_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.get(iid)
        if not task:
            return

        if getattr(task, "task_type", "fluoro") == "xray":
            dialog = XrayReviewDialog(self.root, task)
            self.root.wait_window(dialog)

            if dialog.result is None:
                return

            self._refresh_task_in_tree(task)
            self._autosave_session()
            self.log(f"Изменена рентген-запись: {task.fio}")
            return

        dialog = EditTaskDialog(self.root, task)
        self.root.wait_window(dialog)

        if dialog.result is None:
            return

        task.fio = dialog.result["fio"]
        task.birth_date = dialog.result["birth_date"]
        task.study_date = dialog.result["study_date"]
        task.mode = dialog.result["mode"]
        task.note = dialog.result["note"]

        if task.birth_date and task.birth_date != "ЗАМЕНИТЬ" and task.status == "pending_fix":
            task.status = "pending"
            if task.note == "Дата рождения не распознана":
                task.note = ""

        self._refresh_task_in_tree(task)
        self._autosave_session()
        self.log(f"Изменена запись: {task.fio}")

    def _on_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        if not row_id:
            return

        # Делаем строку активной независимо от того,
        # была ли она выделена до двойного клика.
        self.tree.selection_set(row_id)
        self.tree.focus(row_id)

        try:
            column_index = int(column_id.replace("#", "")) - 1
            columns = list(self.tree["columns"])
            column_name = columns[column_index]
        except Exception:
            column_name = None

        # Двойной клик непосредственно по столбцу "Статус"
        # открывает ручную смену статуса.
        if column_name == "status":
            task = self.task_index.get(row_id)
            if task is not None:
                self._show_manual_status_menu(task, event)
            return

        # Двойной клик по любой другой ячейке сохраняет старое
        # поведение — открыть редактирование пациента.
        self.edit_selected_task()

    def delete_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.pop(iid, None)
        if task:
            self.tasks = [t for t in self.tasks if t.id != iid]

        self.tree.delete(iid)
        self._autosave_session()
        self.log("Запись удалена")

    def run_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.get(iid)
        if not task:
            return

        if not self._can_run_task(task):
            return

        set_interactive_click_calibration(self.interactive_click_var.get())

        thread = threading.Thread(
            target=self._run_single_task_worker,
            args=(task,),
            daemon=True,
        )
        thread.start()

    def run_selected_until_stage(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.get(iid)
        if not task:
            return

        if getattr(task, "task_type", "fluoro") == "xray":
            messagebox.showinfo("Информация", "Запуск рентгена до этапа пока не реализован")
            return

        if not self._can_run_task(task):
            return

        dialog = RunUntilStageDialog(self.root)
        self.root.wait_window(dialog)

        if not dialog.result:
            return

        set_interactive_click_calibration(self.interactive_click_var.get())

        thread = threading.Thread(
            target=self._run_until_stage_worker,
            args=(task, dialog.result),
            daemon=True,
        )
        thread.start()

    def run_selected_ris_link(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.get(iid)
        if not task:
            return

        if getattr(task, "task_type", "fluoro") == "xray":
            messagebox.showinfo("Информация", "Связка с РИС для рентгена пока не реализована")
            return

        if not self._can_run_task(task):
            return

        thread = threading.Thread(
            target=self._run_ris_link_worker,
            args=(task,),
            daemon=True,
        )
        thread.start()

    def run_selected_open_card(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выбери запись")
            return

        iid = selected[0]
        task = self.task_index.get(iid)
        if not task:
            return

        if not self._can_run_task(task):
            return

        set_interactive_click_calibration(self.interactive_click_var.get())

        thread = threading.Thread(
            target=self._run_open_card_worker,
            args=(task,),
            daemon=True,
        )
        thread.start()

    def run_all_tasks(self):
        current = self.current_workspace.get()

        runnable = [
            task
            for task in self.tasks
            if getattr(task, "task_type", "fluoro") == current
            and task.status in ("pending", "error", "cancelled")
            and task.birth_date != "ЗАМЕНИТЬ"
        ]

        if not runnable:
            messagebox.showinfo("Информация", "Нет записей, готовых к запуску")
            return

        selected = self.tree.selection()
        ordered_tasks = runnable

        if selected:
            selected_id = selected[0]
            start_index = next(
                (i for i, task in enumerate(runnable) if task.id == selected_id),
                None,
            )
            if start_index is not None:
                ordered_tasks = runnable[start_index:]

        set_interactive_click_calibration(self.interactive_click_var.get())

        controller = RunController()
        controller.set_total(len(ordered_tasks))

        progress = ProgressWindow(
            self.root,
            controller,
            total_count=len(ordered_tasks),
        )
        self.root.update()

        self._hide_main_for_run_all()

        thread = threading.Thread(
            target=self._run_all_tasks_worker,
            args=(ordered_tasks, controller, progress),
            daemon=True,
        )
        thread.start()

    def _run_single_task_worker(self, task: PatientTask):
        try:
            task.status = "running"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task: self.log(
                    f"Запуск: {task.fio} "
                    f"[task_type={getattr(task, 'task_type', 'fluoro')}; mode={task.mode}]"
                ),
            )
            self._autosave_session()

            task_type = getattr(task, "task_type", "fluoro")

            if task_type == "xray":
                self.root.after(0, lambda: self.log("[XRAY] Передаю задачу в run_xray_task()"))
                ok = run_xray_task(task)
                self.root.after(
                    0,
                    lambda ok=ok: self.log(f"[XRAY] run_xray_task() вернул: {ok!r}"),
                )
            else:
                ok = run_task(task)

            if ok is False:
                raise RuntimeError("Сценарий явно завершился с ошибкой (False)")

            task.status = "done"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"Успешно: {task.fio}"))
            self._autosave_session()

        except Exception as e:
            task.status = "error"
            err_text = str(e)
            tb_text = traceback.format_exc()

            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task, err_text=err_text: self.log(
                    f"Ошибка: {task.fio} -> {err_text}"
                ),
            )
            self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
            self._autosave_session()

    def _run_all_tasks_worker(self, tasks_to_run, controller, progress):
        try:
            for idx, task in enumerate(tasks_to_run, start=1):
                if controller.cancel_requested:
                    self.root.after(0, lambda: progress.set_status("Отменено пользователем"))
                    break

                controller.set_current(idx, task.fio, task.birth_date)

                self.root.after(
                    0,
                    lambda idx=idx, task=task: progress.set_current(
                        idx,
                        task.fio,
                        task.birth_date,
                        "Выполняется",
                    ),
                )

                if task.status == "pending_fix" or task.birth_date == "ЗАМЕНИТЬ":
                    self.root.after(
                        0,
                        lambda task=task: self.log(
                            f"Пропуск: {task.fio} требует исправления даты рождения"
                        ),
                    )
                    continue

                try:
                    task.status = "running"
                    self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
                    self.root.after(
                        0,
                        lambda task=task: self.log(
                            f"Запуск: {task.fio} "
                            f"[task_type={getattr(task, 'task_type', 'fluoro')}; mode={task.mode}]"
                        ),
                    )
                    self._autosave_session()

                    task_type = getattr(task, "task_type", "fluoro")

                    if task_type == "xray":
                        self.root.after(0, lambda: self.log("[XRAY] Передаю задачу в run_xray_task()"))
                        ok = run_xray_task(task, controller=controller)
                        self.root.after(
                            0,
                            lambda ok=ok: self.log(
                                f"[XRAY] run_xray_task() вернул: {ok!r}"
                            ),
                        )
                    else:
                        ok = full_run(
                            fio=task.fio,
                            birth_date=task.birth_date,
                            study_date=task.study_date,
                            mode=task.mode,
                            step_mode=False,
                            controller=controller,
                        )

                    if ok is False:
                        raise RuntimeError("Сценарий явно завершился с ошибкой (False)")

                    if controller.cancel_requested:
                        task.status = "cancelled"
                        self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
                        self.root.after(0, lambda task=task: self.log(f"Отменено: {task.fio}"))
                        self._autosave_session()
                        break

                    task.status = "done"
                    self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
                    self.root.after(0, lambda task=task: self.log(f"Успешно: {task.fio}"))
                    self._autosave_session()

                except Exception as e:
                    task.status = "error"
                    err_text = str(e)
                    tb_text = traceback.format_exc()

                    self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
                    self.root.after(
                        0,
                        lambda task=task, err_text=err_text: self.log(
                            f"Ошибка: {task.fio} -> {err_text}"
                        ),
                    )
                    self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
                    self._autosave_session()

                time.sleep(0.4)

            if controller.cancel_requested:
                self.root.after(0, lambda: progress.finish("Отменено"))
            else:
                self.root.after(0, lambda: progress.finish("Все задачи завершены"))

        finally:
            def finish_run_all_ui():
                try:
                    progress.close()
                finally:
                    self._restore_main_after_run_all()

            self.root.after(1200, finish_run_all_ui)

    def _run_until_stage_worker(self, task: PatientTask, run_cfg: dict):
        scenario = run_cfg["scenario"]
        stop_stage = run_cfg["stop_stage"]
        stop_label = run_cfg["stop_label"]

        try:
            task.status = "stage_running"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task, stop_label=stop_label: self.log(
                    f"Запуск до этапа: {task.fio} -> {stop_label}"
                ),
            )
            self._autosave_session()

            if scenario == "full":
                full_run(
                    fio=task.fio,
                    birth_date=task.birth_date,
                    study_date=task.study_date,
                    mode=task.mode,
                    step_mode=False,
                    stop_stage=stop_stage,
                )
            else:
                if getattr(task, "task_type", "fluoro") == "xray":
                    # Для рентгена пока выполняем полноценный сценарий
                    # из открытой карточки. Отдельные stop_stage для XRAY
                    # можно добавить позже.
                    run_xray_from_open_patient_card(task)
                else:
                    continue_from_open_patient_card(
                        task=task,
                        step_mode=False,
                        stop_stage=stop_stage,
                    )

            task.status = "stage_done"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task, stop_label=stop_label: self.log(
                    f"Остановка на этапе выполнена: {task.fio} -> {stop_label}"
                ),
            )
            self._autosave_session()

        except Exception as e:
            task.status = "stage_error"
            err_text = str(e)
            tb_text = traceback.format_exc()

            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task, err_text=err_text: self.log(
                    f"Запуск до этапа: ошибка для {task.fio} -> {err_text}"
                ),
            )
            self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
            self._autosave_session()

    def _run_ris_link_worker(self, task: PatientTask):
        try:
            task.status = "ris_running"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"РИС: запуск для {task.fio}"))
            self._autosave_session()

            run_ris_link(task)

            task.status = "ris_done"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"РИС: успешно для {task.fio}"))
            self._autosave_session()

        except Exception as e:
            task.status = "ris_error"
            err_text = str(e)
            tb_text = traceback.format_exc()

            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task, err_text=err_text: self.log(f"РИС: ошибка для {task.fio} -> {err_text}"))
            self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
            self._autosave_session()

    def _run_open_card_worker(self, task: PatientTask):
        try:
            task.status = "open_card_running"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"Открытая карточка: запуск для {task.fio}"))
            self._autosave_session()

            if getattr(task, "task_type", "fluoro") == "xray":
                self.root.after(
                    0,
                    lambda task=task: self.log(
                        f"[XRAY] Запуск из открытой карточки: {task.fio}"
                    ),
                )
                run_xray_from_open_patient_card(task)
            else:
                continue_from_open_patient_card(task, step_mode=False)

            task.status = "open_card_done"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"Открытая карточка: успешно для {task.fio}"))
            self._autosave_session()

        except Exception as e:
            task.status = "open_card_error"
            err_text = str(e)
            tb_text = traceback.format_exc()

            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(
                0,
                lambda task=task, err_text=err_text: self.log(
                    f"Открытая карточка: ошибка для {task.fio} -> {err_text}"
                ),
            )
            self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
            self._autosave_session()