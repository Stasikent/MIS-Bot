import tkinter as tk
import time
import json
import pyautogui

from config.loader import CONFIG_DIR, load_json, save_json


class ClickCalibrationWindow:
    def __init__(self, root, template_key, base_point, offset_key):
        self.root = tk.Toplevel(root)
        self.root.title(f"Настройка: {template_key}")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.2)
        self.root.configure(bg="black")

        self.template_key = template_key
        self.base_x, self.base_y = base_point
        self.offset_key = offset_key

        self.label = tk.Label(
            self.root,
            text=f"Кликни в нужную точку для {template_key}",
            font=("Arial", 18),
            bg="black",
            fg="white"
        )
        self.label.pack(pady=40)

        self.root.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        new_x = event.x_root
        new_y = event.y_root

        dx = new_x - self.base_x
        dy = new_y - self.base_y

        self.save_offset(dx, dy)

        self.root.destroy()

    def save_offset(self, dx, dy):
        path = CONFIG_DIR / "coordinates.json"
        data = load_json("coordinates.json")

        if "mis" not in data:
            data["mis"] = {}

        data["mis"][self.offset_key] = [dx, dy]

        save_json("coordinates.json", data)

        print(f"[CALIBRATION] {self.offset_key} = [{dx}, {dy}]")