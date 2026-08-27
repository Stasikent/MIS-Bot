import json
import re
from pathlib import Path
from services.runtime_paths import CONFIG_DIR, TEMPLATES_DIR
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageGrab

from gui.screen_pick_overlay import pick_screen_rect

PROTOCOLS_PATH = CONFIG_DIR / "protocols.json"
TEMPLATES_PATH = CONFIG_DIR / "templates.json"

def _slug(text):
    value = str(text or "").strip().lower()
    table = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "abvgdeejzijklmnoprstufhzcss_y_eua"
    )
    value = value.translate(table)
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "protocol"

class ProtocolSettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("Протоколы и связанные шаблоны")
        self.geometry("900x590")
        self.transient(parent)
        self.grab_set()
        self.on_saved = on_saved
        self.section_var = tk.StringVar(value="fluoro")
        self.name_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.template_var = tk.StringVar()
        self.aliases_var = tk.StringVar()
        self.data = self._load()
        self._build()
        self._refresh()

    def _load(self):
        if PROTOCOLS_PATH.exists():
            return json.loads(PROTOCOLS_PATH.read_text(encoding="utf-8"))
        return {"version": 1, "fluoro": [], "xray": []}

    def _save(self):
        PROTOCOLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROTOCOLS_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.on_saved:
            self.on_saved()

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        left = ttk.Frame(root)
        left.pack(side="left", fill="y")
        right = ttk.Frame(root)
        right.pack(side="left", fill="both", expand=True, padx=(14,0))

        top = ttk.Frame(left); top.pack(fill="x", pady=(0,8))
        ttk.Label(top, text="Режим:").pack(side="left")
        box = ttk.Combobox(top, textvariable=self.section_var, values=["fluoro","xray"], state="readonly", width=10)
        box.pack(side="left", padx=5); box.bind("<<ComboboxSelected>>", lambda e:self._refresh())

        self.listbox = tk.Listbox(left, width=32, height=25, exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e:self._load_selected())

        b = ttk.Frame(left); b.pack(fill="x", pady=8)
        ttk.Button(b, text="Добавить", command=self._add).pack(side="left")
        ttk.Button(b, text="Удалить", command=self._delete).pack(side="left", padx=5)

        labels = [
            ("Название:", self.name_var),
            ("Внутренний ключ:", self.key_var),
            ("Ключ шаблона:", self.template_var),
            ("Синонимы через ;", self.aliases_var),
        ]
        for row,(label,var) in enumerate(labels):
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(right, textvariable=var, width=55).grid(row=row, column=1, sticky="ew", pady=5)
        right.columnconfigure(1, weight=1)

        actions = ttk.Frame(right)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16,0))
        ttk.Button(actions, text="Сохранить протокол", command=self._save_selected).pack(side="left")
        ttk.Button(actions, text="Создать / заменить шаблон", command=self._capture_template).pack(side="left", padx=8)
        ttk.Button(actions, text="Закрыть", command=self.destroy).pack(side="right")

        hint = ("Шаблон создаётся выделением области на экране. PNG сохраняется в project/templates, "
                "а запись автоматически добавляется в templates.json.")
        ttk.Label(right, text=hint, wraplength=560, justify="left").grid(row=6,column=0,columnspan=2,sticky="w",pady=16)

    def _items(self):
        return self.data.setdefault(self.section_var.get(), [])

    def _refresh(self, select_index=None):
        self.listbox.delete(0,"end")
        for item in self._items():
            self.listbox.insert("end", item.get("name", item.get("key","")))
        if self.listbox.size():
            idx = 0 if select_index is None else min(select_index, self.listbox.size()-1)
            self.listbox.selection_set(idx)
            self._load_selected()
        else:
            self._clear()

    def _index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _clear(self):
        for v in (self.name_var,self.key_var,self.template_var,self.aliases_var): v.set("")

    def _load_selected(self):
        idx=self._index()
        if idx is None: return
        item=self._items()[idx]
        self.name_var.set(item.get("name",""))
        self.key_var.set(item.get("key",""))
        self.template_var.set(item.get("template_key",""))
        self.aliases_var.set("; ".join(item.get("aliases",[])))

    def _add(self):
        base="Новый протокол"
        existing={x.get("key") for x in self._items()}
        n=1
        while True:
            key=f"custom_{n}"
            if key not in existing: break
            n+=1
        self._items().append({"key":key,"name":base,"template_key":f"template_row_{key}","aliases":[]})
        self._save()
        self._refresh(len(self._items())-1)

    def _delete(self):
        idx=self._index()
        if idx is None: return
        item=self._items()[idx]
        if not messagebox.askyesno("Удаление", f"Удалить протокол «{item.get('name')}»?\nPNG-шаблон автоматически не удаляется.", parent=self):
            return
        del self._items()[idx]
        self._save()
        self._refresh(max(0,idx-1))

    def _save_selected(self):
        idx=self._index()
        if idx is None: return
        name=self.name_var.get().strip()
        key=self.key_var.get().strip() or _slug(name)
        template_key=self.template_var.get().strip() or f"template_row_{key}"
        if not name:
            messagebox.showerror("Ошибка","Название не может быть пустым.",parent=self); return
        for i,item in enumerate(self._items()):
            if i != idx and item.get("key")==key:
                messagebox.showerror("Ошибка","Такой внутренний ключ уже существует.",parent=self); return
        self._items()[idx] = {
            "key":key, "name":name, "template_key":template_key,
            "aliases":[x.strip() for x in self.aliases_var.get().split(";") if x.strip()]
        }
        self._save()
        self._refresh(idx)
        messagebox.showinfo("Готово","Протокол сохранён.",parent=self)

    def _capture_template(self):
        idx=self._index()
        if idx is None: return
        self._save_selected()
        item=self._items()[idx]
        template_key=item["template_key"]
        filename=f"{template_key}.png"

        self.withdraw(); self.update()
        try:
            rect=pick_screen_rect(self.master)
            if rect is None: return
            left,top,width,height=rect
            if width <= 1 or height <= 1: raise RuntimeError("Слишком маленькая область.")
            image=ImageGrab.grab(bbox=(left,top,left+width,top+height))
            TEMPLATES_DIR.mkdir(parents=True,exist_ok=True)
            image.save(TEMPLATES_DIR/filename)

            data=json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
            section="mis"
            data.setdefault(section,{})[template_key] = {
                "file":filename,
                "confidence":0.82,
                "description":f"Пользовательский шаблон протокола: {item['name']}"
            }
            TEMPLATES_PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
            self._save()
        except Exception as e:
            messagebox.showerror("Ошибка",str(e),parent=self)
        finally:
            self.deiconify(); self.lift(); self.focus_force()

        messagebox.showinfo("Готово",f"Шаблон {template_key} сохранён.",parent=self)
