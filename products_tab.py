import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database

class ProductsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()
        self.refresh_table()

    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить", command=self.add_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_product).pack(side='left', padx=2)

        # Таблица продуктов
        columns = ('id', 'name', 'calories', 'proteins', 'fats', 'carbs', 'gi')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Название')
        self.tree.heading('calories', text='Калории (ккал/100г)')
        self.tree.heading('proteins', text='Белки (г/100г)')
        self.tree.heading('fats', text='Жиры (г/100г)')
        self.tree.heading('carbs', text='Углеводы (г/100г)')
        self.tree.heading('gi', text='ГИ')

        self.tree.column('id', width=40)
        self.tree.column('name', width=150)
        self.tree.column('calories', width=80)
        self.tree.column('proteins', width=80)
        self.tree.column('fats', width=80)
        self.tree.column('carbs', width=80)
        self.tree.column('gi', width=50)
        self.tree.bind('<Double-1>', lambda e: self.edit_product())


        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True, padx=(5,0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0,5), pady=5)

    def refresh_table(self):
        """Обновляет данные в таблице из базы."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        products = database.get_all_products()
        for p in products:
            self.tree.insert('', 'end', values=(
                p['id'], p['name'], p['calories'], p['proteins'],
                p['fats'], p['carbs'], p['glycemic_index'] if p['glycemic_index'] else ''
            ))

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
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, padx=5, pady=5, sticky='e')
            entry = ttk.Entry(dialog, width=30)
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
                    entry.insert(0, str(product_data[key]))

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
            except ValueError:
                messagebox.showerror("Ошибка", "Проверьте правильность ввода чисел")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Сохранить", command=save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side='left', padx=5)