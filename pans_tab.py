import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from PIL import Image, ImageTk
import database
from config import PANS_PHOTO_DIR

class PansTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
        self.refresh_table()

    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self.add_pan).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_pan).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_pan).pack(side='left', padx=2)

        # Таблица кастрюль
        columns = ('id', 'name', 'weight', 'photo')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Название')
        self.tree.heading('weight', text='Вес (г)')
        self.tree.heading('photo', text='Фото')

        self.tree.column('id', width=40)
        self.tree.column('name', width=150)
        self.tree.column('weight', width=80)
        self.tree.column('photo', width=200)

        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<Double-1>', lambda e: self.edit_pan())
        self.tree.pack(side='left', fill='both', expand=True, padx=(5,0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0,5), pady=5)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        pans = database.get_all_pans()
        for p in pans:
            # Показываем только имя файла, если путь есть
            photo_display = os.path.basename(p['photo_path']) if p['photo_path'] else ''
            self.tree.insert('', 'end', values=(p['id'], p['name'], p['weight'], photo_display))

    def add_pan(self):
        self._edit_dialog()

    def edit_pan(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите кастрюлю для редактирования")
            return
        item = self.tree.item(selected[0])
        pan_id = item['values'][0]
        self._edit_dialog(pan_id)

    def delete_pan(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите кастрюлю для удаления")
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранную кастрюлю?\nФото не будет удалено с диска."):
            item = self.tree.item(selected[0])
            pan_id = item['values'][0]
            database.delete_pan(pan_id)
            self.refresh_table()

    def _edit_dialog(self, pan_id=None):
        dialog = tk.Toplevel(self)
        dialog.title("Добавление кастрюли" if pan_id is None else "Редактирование кастрюли")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Поля
        ttk.Label(dialog, text="Название:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(dialog, text="Вес (г):").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        weight_entry = ttk.Entry(dialog, width=30)
        weight_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(dialog, text="Фото:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        photo_path_var = tk.StringVar()
        photo_entry = ttk.Entry(dialog, textvariable=photo_path_var, width=30, state='readonly')
        photo_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        def choose_photo():
            filename = filedialog.askopenfilename(
                title="Выберите изображение",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
            )
            if filename:
                # Копируем файл в папку pans_photos
                base = os.path.basename(filename)
                dest = os.path.join(PANS_PHOTO_DIR, base)
                # Если файл с таким именем уже есть, добавляем суффикс
                counter = 1
                name, ext = os.path.splitext(base)
                while os.path.exists(dest):
                    dest = os.path.join(PANS_PHOTO_DIR, f"{name}_{counter}{ext}")
                    counter += 1
                shutil.copy2(filename, dest)
                # Сохраняем относительный путь
                rel_path = os.path.relpath(dest, start=os.path.dirname(database.DB_PATH))
                photo_path_var.set(rel_path)

        ttk.Button(dialog, text="Обзор...", command=choose_photo).grid(row=2, column=2, padx=5, pady=5)

        # Если редактирование, загружаем данные
        if pan_id is not None:
            pan = database.get_pan(pan_id)
            if pan:
                name_entry.insert(0, pan['name'])
                weight_entry.insert(0, str(pan['weight']))
                if pan['photo_path']:
                    photo_path_var.set(pan['photo_path'])

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Название обязательно")
                return
            try:
                weight = float(weight_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Вес должен быть числом")
                return
            photo_path = photo_path_var.get().strip() or None

            if pan_id is None:
                database.add_pan(name, weight, photo_path)
            else:
                database.update_pan(pan_id, name, weight, photo_path)
            dialog.destroy()
            self.refresh_table()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Сохранить", command=save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side='left', padx=5)
