import time
import threading
import traceback
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
from gui.progress_window import ProgressWindow
from gui.bulk_import_review_dialog import BulkImportReviewDialog
from gui.xray_review_dialog import XrayReviewDialog

from models.patient_task import PatientTask
from services.xray_template_matcher import match_xray_template

from ocr.stationary_xray_text_parser import parse_stationary_xray_text
from ocr.direction_ocr import parse_direction_image
from ocr.screen_region_capture import capture_screen_region, capture_named_screen_region
from ocr.screen_list_ocr import parse_screen_region
from ocr.two_step_region_ocr import build_task_from_two_regions
from ocr.stationary_xray_text_parser import parse_stationary_xray_text

from project.xray_flow import run_xray_task

from services.task_runner import run_task
from services.mode_mapper import INTERNAL_TO_UI_MODE
from services.session_store import save_session, load_session, clear_session

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

        self.tasks = []
        self.task_index = {}

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
            "Настройки",
            [
                ("Выбрать окно МИС", self.pick_mis_window),
                ("Координаты", self.open_coordinates_settings),
                ("Шаблоны", self.open_template_settings),
                ("Карта кликов", self.open_click_map),
                ("Калибровать offset", self.open_offset_calibration),
                ("Default", self.open_defaults_settings),
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

        self.tree = ttk.Treeview(self.root, columns=(), show="headings", height=18)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

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

        self._rebuild_tree_columns()
        self._reload_tree_rows()

    def _rebuild_tree_columns(self):
        mode = self.current_workspace.get()

        if mode == "xray":
            columns = (
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
                "fio",
                "birth_date",
                "study_date",
                "mode",
                "status",
                "note",
            )
            headers = {
                "fio": "ФИО",
                "birth_date": "Дата рождения",
                "study_date": "Дата исследования",
                "mode": "Протокол",
                "status": "Статус",
                "note": "Примечание",
            }
            widths = {
                "fio": 280,
                "birth_date": 110,
                "study_date": 130,
                "mode": 150,
                "status": 130,
                "note": 260,
            }

        self.tree["columns"] = columns

        for col in columns:
            self.tree.heading(col, text=headers.get(col, col))
            self.tree.column(col, width=widths.get(col, 120), anchor="w")

        for col in ("birth_date", "study_date", "dose", "status", "mode", "template_name"):
            if col in columns:
                self.tree.column(col, anchor="center")

    def _reload_tree_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        current = self.current_workspace.get()

        for task in self.tasks:
            task_type = getattr(task, "task_type", "fluoro")
            if task_type != current:
                continue
            self._insert_task_to_tree(task)

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

    def _on_interactive_click_toggle(self):
        set_interactive_click_calibration(self.interactive_click_var.get())
        state = "ВКЛ" if self.interactive_click_var.get() else "ВЫКЛ"
        self.log(f"Интерактивная настройка кликов: {state}")

    def pick_mis_window(self):
        import time
        import pygetwindow as gw
        from config.loader import save_setting

        self.log("Через 3 секунды кликните по окну МИС...")
        time.sleep(3)

        win = gw.getActiveWindow()

        if not win:
            self.log("Не удалось определить окно")
            return

        title = win.title.strip()

        if not title:
            self.log("Пустой title окна")
            return

        save_setting("mis", "window_title", title)
        self.log(f"Окно МИС сохранено: {title}")

    def log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def _autosave_session(self):
        try:
            path = save_session(self.tasks)
            return path
        except Exception as e:
            self.log(f"Ошибка автосохранения сессии: {e}")
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
                task.fio,
                task.birth_date,
                task.study_date,
                INTERNAL_TO_UI_MODE.get(task.mode, task.mode),
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
                task.fio,
                task.birth_date,
                task.study_date,
                INTERNAL_TO_UI_MODE.get(task.mode, task.mode),
                task.status,
                task.note or "",
            )

        self.tree.item(
            task.id,
            values=values,
            tags=self._get_task_tags(task),
        )

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

    def open_defaults_settings(self):
        DefaultsSettingsWindow(self.root, on_saved=lambda: self.log("Default-настройки обновлены"))

    def open_offset_calibration(self):
        OffsetCalibrationWindow(self.root, on_saved=lambda: self.log("Offset сохранён в coordinates.json"))

    def open_preflight_window(self):
        PreflightWindow(self.root)

    def open_click_map(self):
        ClickMapWindow(self.root, on_saved=lambda: self.log("Карта кликов: coordinates.json обновлён"))

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

        def show_context_menu(event):
            paste_menu.delete(0, "end")
            paste_menu.add_command(label="Вставить", command=paste_from_clipboard)
            paste_menu.tk_popup(event.x_root, event.y_root)
            return "break"

        text_box.bind("<Control-v>", paste_from_clipboard)
        text_box.bind("<Control-V>", paste_from_clipboard)
        text_box.bind("<Shift-Insert>", paste_from_clipboard)
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
        selected = self.tree.selection()
        if selected:
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

        if getattr(task, "task_type", "fluoro") == "xray":
            messagebox.showinfo("Информация", "Рентген из открытой карточки пока не реализован")
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
            task for task in self.tasks
            if getattr(task, "task_type", "fluoro") == current
            and not (task.status == "pending_fix" or task.birth_date == "ЗАМЕНИТЬ")
        ]

        if not runnable:
            messagebox.showinfo("Информация", "Нет записей, готовых к запуску")
            return

        selected = self.tree.selection()
        ordered_tasks = runnable

        if selected:
            selected_id = selected[0]
            start_index = next((i for i, t in enumerate(runnable) if t.id == selected_id), None)
            if start_index is not None:
                ordered_tasks = runnable[start_index:] + runnable[:start_index]

        set_interactive_click_calibration(self.interactive_click_var.get())

        controller = RunController()
        controller.set_total(len(ordered_tasks))

        progress = ProgressWindow(self.root, controller, total_count=len(ordered_tasks))
        self.root.update()

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
            self.root.after(0, lambda task=task: self.log(f"Запуск: {task.fio} [{task.mode}]"))
            self._autosave_session()

            if getattr(task, "task_type", "fluoro") == "xray":
                run_xray_task(task)
            else:
                run_task(task)

            task.status = "done"
            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task: self.log(f"Успешно: {task.fio}"))
            self._autosave_session()

        except Exception as e:
            task.status = "error"
            err_text = str(e)
            tb_text = traceback.format_exc()

            self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
            self.root.after(0, lambda task=task, err_text=err_text: self.log(f"Ошибка: {task.fio} -> {err_text}"))
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
                        lambda task=task: self.log(f"Пропуск: {task.fio} требует исправления даты рождения"),
                    )
                    continue

                try:
                    task.status = "running"
                    self.root.after(0, lambda task=task: self._refresh_task_in_tree(task))
                    self.root.after(0, lambda task=task: self.log(f"Запуск: {task.fio} [{task.mode}]"))
                    self._autosave_session()

                    if getattr(task, "task_type", "fluoro") == "xray":
                        run_xray_task(task, controller=controller)
                    else:
                            full_run(
                            fio=task.fio,
                            birth_date=task.birth_date,
                            study_date=task.study_date,
                            mode=task.mode,
                            step_mode=False,
                            controller=controller,
                    )

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
                    self.root.after(0, lambda task=task, err_text=err_text: self.log(f"Ошибка: {task.fio} -> {err_text}"))
                    self.root.after(0, lambda tb_text=tb_text: self.log(tb_text))
                    self._autosave_session()

                time.sleep(0.4)

            if controller.cancel_requested:
                self.root.after(0, lambda: progress.finish("Отменено"))
            else:
                self.root.after(0, lambda: progress.finish("Все задачи завершены"))

        finally:
            self.root.after(1200, progress.close)

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