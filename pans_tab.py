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

        # Настройка стиля для Treeview
        self._configure_treeview_style()

        self.create_widgets()
        self.refresh_table()

    def _configure_treeview_style(self):
        """Настраивает стиль Treeview для правильной высоты строк и чередования фона."""
        style = ttk.Style()

        # Определяем оптимальную высоту строки
        temp_label = ttk.Label(self, text="Тест", font=('Arial', 10))
        temp_label.pack()
        row_height = temp_label.winfo_reqheight() + 4  # добавляем небольшой отступ
        temp_label.destroy()

        # Настраиваем стиль для Treeview
        style.configure(
            "Pans.Treeview",
            rowheight=row_height,
            font=('Arial', 10),
            background='#f5f5f5',
            fieldbackground='#f5f5f5'
        )

        style.configure(
            "Pans.Treeview.Heading",
            font=('Arial', 10, 'bold'),
            relief='raised'
        )

        # Настраиваем цвета для выделения
        style.map(
            "Pans.Treeview",
            background=[('selected', '#0078d7')],
            foreground=[('selected', 'white')]
        )

    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self.add_pan).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_pan).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_pan).pack(side='left', padx=2)

        # Таблица кастрюль с настроенным стилем
        columns = ('id', 'name', 'weight', 'photo')
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            selectmode='browse',
            style="Pans.Treeview"
        )

        # Настройка заголовков
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Название')
        self.tree.heading('weight', text='Вес (г)')
        self.tree.heading('photo', text='Фото')

        # Настройка ширины колонок
        self.tree.column('id', width=40, anchor='center')
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('weight', width=100, anchor='center')
        self.tree.column('photo', width=250, anchor='w')

        # Настраиваем теги для чередования фона
        self.tree.tag_configure('oddrow', background='#ffffff')
        self.tree.tag_configure('evenrow', background='#f0f0f0')

        # Скроллбар
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Привязываем обработчик двойного щелчка
        self.tree.bind('<Double-1>', lambda e: self.edit_pan())

        # Размещаем виджеты
        self.tree.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0, 5), pady=5)

    def refresh_table(self):
        """Обновляет данные в таблице из базы с чередованием фона."""
        # Очищаем таблицу
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Загружаем кастрюли
        pans = database.get_all_pans()

        # Вставляем с чередованием фона
        for i, p in enumerate(pans):
            # Определяем тег для чередования (четные/нечетные строки)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'

            # Показываем только имя файла, если путь есть
            photo_display = os.path.basename(p['photo_path']) if p['photo_path'] else ''

            # Форматируем вес
            weight_display = f"{p['weight']:.0f}" if p['weight'] else "0"

            self.tree.insert('', 'end',
                             values=(
                                 p['id'],
                                 p['name'],
                                 weight_display,
                                 photo_display
                             ),
                             tags=(tag,)
                             )

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
        ttk.Label(dialog, text="Название:", font=('Arial', 10)).grid(
            row=0, column=0, padx=5, pady=5, sticky='e'
        )
        name_entry = ttk.Entry(dialog, width=30, font=('Arial', 10))
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(dialog, text="Вес (г):", font=('Arial', 10)).grid(
            row=1, column=0, padx=5, pady=5, sticky='e'
        )
        weight_entry = ttk.Entry(dialog, width=30, font=('Arial', 10))
        weight_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(dialog, text="Фото:", font=('Arial', 10)).grid(
            row=2, column=0, padx=5, pady=5, sticky='e'
        )

        # Фрейм для поля ввода и кнопки выбора фото
        photo_frame = ttk.Frame(dialog)
        photo_frame.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky='w')

        photo_path_var = tk.StringVar()
        photo_entry = ttk.Entry(photo_frame, textvariable=photo_path_var, width=30,
                                state='readonly', font=('Arial', 10))
        photo_entry.pack(side='left', padx=(0, 5))

        ttk.Button(photo_frame, text="Обзор...", command=lambda: self._choose_photo(photo_path_var),
                   width=10).pack(side='left')

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
                if weight <= 0:
                    messagebox.showerror("Ошибка", "Вес должен быть положительным числом")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Вес должен быть числом")
                return
            photo_path = photo_path_var.get().strip() or None

            try:
                if pan_id is None:
                    database.add_pan(name, weight, photo_path)
                else:
                    database.update_pan(pan_id, name, weight, photo_path)
                dialog.destroy()
                self.refresh_table()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить кастрюлю: {e}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=save, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy, width=15).pack(side='left', padx=5)

    def _choose_photo(self, photo_path_var):
        """Выбор и копирование фото."""
        filename = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if filename:
            try:
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

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось скопировать фото: {e}")