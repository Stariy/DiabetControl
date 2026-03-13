import tkinter as tk
from tkinter import ttk, messagebox
import database


class ProductsTab(ttk.Frame):
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
            "Products.Treeview",
            rowheight=row_height,
            font=('Arial', 10),
            background='#f5f5f5',
            fieldbackground='#f5f5f5'
        )

        style.configure(
            "Products.Treeview.Heading",
            font=('Arial', 10, 'bold'),
            relief='raised'
        )

        # Настраиваем цвета для выделения
        style.map(
            "Products.Treeview",
            background=[('selected', '#0078d7')],
            foreground=[('selected', 'white')]
        )

        # Настраиваем чередование фона через теги
        # Теги будут применяться вручную при вставке строк

    def _get_optimal_rowheight(self):
        """Определяет оптимальную высоту строки на основе текущего шрифта."""
        temp_label = ttk.Label(self, text="Тест", font=('Arial', 10))
        temp_label.pack()
        height = temp_label.winfo_reqheight()
        temp_label.destroy()
        return height + 4  # добавляем небольшой отступ

    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self.add_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_product).pack(side='left', padx=2)

        # Таблица продуктов с настроенным стилем
        columns = ('id', 'name', 'calories', 'proteins', 'fats', 'carbs', 'gi')
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            selectmode='browse',
            style="Products.Treeview"
        )

        # Настройка заголовков
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Название')
        self.tree.heading('calories', text='Калории (ккал/100г)')
        self.tree.heading('proteins', text='Белки (г/100г)')
        self.tree.heading('fats', text='Жиры (г/100г)')
        self.tree.heading('carbs', text='Углеводы (г/100г)')
        self.tree.heading('gi', text='ГИ')

        # Настройка ширины колонок
        self.tree.column('id', width=40, anchor='center')
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('calories', width=100, anchor='center')
        self.tree.column('proteins', width=80, anchor='center')
        self.tree.column('fats', width=80, anchor='center')
        self.tree.column('carbs', width=100, anchor='center')
        self.tree.column('gi', width=50, anchor='center')

        # Привязываем обработчик двойного щелчка
        self.tree.bind('<Double-1>', lambda e: self.edit_product())

        # Настраиваем теги для чередования фона
        self.tree.tag_configure('oddrow', background='#ffffff')
        self.tree.tag_configure('evenrow', background='#f0f0f0')

        # Скроллбар
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Размещаем виджеты
        self.tree.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0, 5), pady=5)

    def refresh_table(self):
        """Обновляет данные в таблице из базы с чередованием фона."""
        # Очищаем таблицу
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Загружаем продукты
        products = database.get_all_products()

        # Вставляем с чередованием фона
        for i, p in enumerate(products):
            # Определяем тег для чередования (четные/нечетные строки)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'

            self.tree.insert('', 'end',
                             values=(
                                 p['id'],
                                 p['name'],
                                 f"{p['calories']:.1f}" if p['calories'] else "0",
                                 f"{p['proteins']:.1f}" if p['proteins'] else "0",
                                 f"{p['fats']:.1f}" if p['fats'] else "0",
                                 f"{p['carbs']:.1f}" if p['carbs'] else "0",
                                 p['glycemic_index'] if p['glycemic_index'] else ''
                             ),
                             tags=(tag,)
                             )

    def add_product(self):
        self._edit_dialog()

    def edit_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите продукт для редактирования")
            return
        item = self.tree.item(selected[0])
        product_id = item['values'][0]
        self._edit_dialog(product_id)

    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите продукт для удаления")
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранный продукт?"):
            item = self.tree.item(selected[0])
            product_id = item['values'][0]
            database.delete_product(product_id)
            self.refresh_table()

    def _edit_dialog(self, product_id=None):
        """Диалог добавления/редактирования продукта."""
        dialog = tk.Toplevel(self)
        dialog.title("Добавление продукта" if product_id is None else "Редактирование продукта")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        fields = [
            ('Название:', 'name'),
            ('Калории (ккал/100г):', 'calories'),
            ('Белки (г/100г):', 'proteins'),
            ('Жиры (г/100г):', 'fats'),
            ('Углеводы (г/100г):', 'carbs'),
            ('Гликемический индекс:', 'gi')
        ]
        entries = {}

        # Загрузка данных, если редактирование
        product_data = None
        if product_id is not None:
            product_data = database.get_product(product_id)

        for i, (label_text, key) in enumerate(fields):
            ttk.Label(dialog, text=label_text, font=('Arial', 10)).grid(
                row=i, column=0, padx=5, pady=5, sticky='e'
            )
            entry = ttk.Entry(dialog, width=30, font=('Arial', 10))
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='w')
            entries[key] = entry

            # Предзаполнение
            if product_data:
                if key == 'name':
                    entry.insert(0, product_data['name'])
                elif key == 'gi':
                    val = product_data['glycemic_index']
                    if val is not None:
                        entry.insert(0, str(val))
                else:
                    entry.insert(0, f"{product_data[key]:.1f}")

        def save():
            try:
                name = entries['name'].get().strip()
                if not name:
                    messagebox.showerror("Ошибка", "Название обязательно")
                    return

                calories = float(entries['calories'].get() or 0)
                proteins = float(entries['proteins'].get() or 0)
                fats = float(entries['fats'].get() or 0)
                carbs = float(entries['carbs'].get() or 0)
                gi_str = entries['gi'].get().strip()
                gi = int(gi_str) if gi_str else None

                if product_id is None:
                    database.add_product(name, calories, proteins, fats, carbs, gi)
                else:
                    database.update_product(product_id, name, calories, proteins, fats, carbs, gi)

                dialog.destroy()
                self.refresh_table()

            except ValueError as e:
                messagebox.showerror("Ошибка", f"Проверьте правильность ввода чисел: {e}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=save, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy, width=15).pack(side='left', padx=5)