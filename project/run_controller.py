import time
import threading


class RunController:
    def __init__(self):
        self.is_paused = False
        self.cancel_requested = False

        self.current_index = 0
        self.total = 0

        self.current_fio = ""
        self.current_birth_date = ""

        self._lock = threading.Lock()

    # --- управление ---
    def pause(self):
        with self._lock:
            self.is_paused = True

    def resume(self):
        with self._lock:
            self.is_paused = False

    def toggle_pause(self):
        with self._lock:
            self.is_paused = not self.is_paused

    def cancel(self):
        with self._lock:
            self.cancel_requested = True

    # --- состояние ---
    def set_total(self, total):
        self.total = total

    def set_current(self, index, fio, birth_date):
        self.current_index = index
        self.current_fio = fio
        self.current_birth_date = birth_date

    # --- контроль выполнения ---
    def wait_if_paused(self):
        while True:
            with self._lock:
                if not self.is_paused:
                    return
            time.sleep(0.2)

    def raise_if_cancelled(self):
        if self.cancel_requested:
            raise RuntimeError("Запуск отменён пользователем")