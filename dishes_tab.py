import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database

class DishesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.current_dish_id = None
        self.pans_list = []  # список кортежей (id, name)
        self.products_list = []  # список кортежей (id, name)
        self.create_widgets()
        self.load_pans()
        self.load_products()
        self.refresh_dishes_list()

    def create_widgets(self):
        # Левая панель со списком блюд
        left_frame = ttk.Frame(self, width=200, relief='sunken', padding=5)
        left_frame.pack(side='left', fill='y', padx=(5,0), pady=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Блюда", font=('Arial', 10, 'bold')).pack(anchor='w')

        self.dishes_listbox = tk.Listbox(left_frame)
        self.dishes_listbox.pack(fill='both', expand=True, pady=5)
        self.dishes_listbox.bind('<<ListboxSelect>>', self.on_dish_select)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Новое", command=self.new_dish).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_dish).pack(side='left', padx=2)

        # Правая панель (детали блюда)
        right_frame = ttk.Frame(self, padding=5)
        right_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Поле названия
        ttk.Label(right_frame, text="Название:").grid(row=0, column=0, sticky='e', pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(right_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky='w', pady=2)
        self.name_entry.bind('<FocusOut>', lambda e: self.save_dish_details())

        # Выбор кастрюли по умолчанию
        ttk.Label(right_frame, text="Кастрюля по умолчанию:").grid(row=1, column=0, sticky='e', pady=2)
        self.pan_var = tk.StringVar()  # хранит id кастрюли
        self.pan_combo = ttk.Combobox(right_frame, textvariable=self.pan_var, width=38, state='readonly')
        self.pan_combo.grid(row=1, column=1, sticky='w', pady=2)
        self.pan_combo.bind('<<ComboboxSelected>>', lambda e: self.save_dish_details())

        # Типичный вес готового блюда
        ttk.Label(right_frame, text="Типичный вес готового блюда (г):").grid(row=2, column=0, sticky='e', pady=2)
        self.weight_var = tk.StringVar()
        self.weight_entry = ttk.Entry(right_frame, textvariable=self.weight_var, width=40)
        self.weight_entry.grid(row=2, column=1, sticky='w', pady=2)
        self.weight_entry.bind('<FocusOut>', lambda e: self.save_dish_details())

        # Таблица состава блюда
        ttk.Label(right_frame, text="Состав блюда:", font=('Arial', 10, 'bold')).grid(row=3, column=0, columnspan=2, sticky='w', pady=(10,0))

        # Кнопки управления составом
        comp_btn_frame = ttk.Frame(right_frame)
        comp_btn_frame.grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        ttk.Button(comp_btn_frame, text="Добавить продукт", command=self.add_product_to_dish).pack(side='left', padx=2)
        ttk.Button(comp_btn_frame, text="Изменить вес", command=self.edit_product_weight).pack(side='left', padx=2)
        ttk.Button(comp_btn_frame, text="Удалить продукт", command=self.delete_product_from_dish).pack(side='left', padx=2)

        # Таблица состава
        columns = ('product', 'weight')
        self.comp_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=10)
        self.comp_tree.heading('product', text='Продукт')
        self.comp_tree.heading('weight', text='Вес (г)')
        self.comp_tree.column('product', width=200)
        self.comp_tree.column('weight', width=100)

        scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.comp_tree.yview)
        self.comp_tree.configure(yscrollcommand=scrollbar.set)

        self.comp_tree.grid(row=5, column=0, columnspan=2, sticky='nsew', pady=5)
        scrollbar.grid(row=5, column=2, sticky='ns')

        # Настройка весов для растяжения
        right_frame.columnconfigure(1, weight=1)
        right_frame.rowconfigure(5, weight=1)

    def load_pans(self):
        """Загружает список кастрюль для комбобокса."""
        self.pans_list = [(0, '— нет —')]  # нулевой ID для "нет"
        pans = database.get_all_pans()
        for p in pans:
            self.pans_list.append((p['id'], p['name']))
        self.pan_combo['values'] = [name for _, name in self.pans_list]

    def load_products(self):
        """Загружает список продуктов для диалогов."""
        prods = database.get_all_products()
        self.products_list = [(p['id'], p['name']) for p in prods]

    def refresh_dishes_list(self):
        """Обновляет список блюд в левой панели."""
        self.dishes_listbox.delete(0, tk.END)
        dishes = database.get_all_dishes()
        self.dish_items = []  # список кортежей (id, name)
        for d in dishes:
            self.dishes_listbox.insert(tk.END, d['name'])
            self.dish_items.append((d['id'], d['name']))

    def on_dish_select(self, event):
        """Обработчик выбора блюда из списка."""
        selection = self.dishes_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.current_dish_id = self.dish_items[index][0]
        self.load_dish_details()

    def load_dish_details(self):
        """Загружает данные выбранного блюда в правую панель."""
        if self.current_dish_id is None:
            self.clear_right_panel()
            return

        dish = database.get_dish(self.current_dish_id)
        if not dish:
            return

        # Название
        self.name_var.set(dish['name'])

        # Кастрюля по умолчанию
        pan_id = dish['default_pan_id']
        # Находим индекс в self.pans_list
        pan_index = 0
        for i, (pid, _) in enumerate(self.pans_list):
            if pid == pan_id:
                pan_index = i
                break
        self.pan_combo.current(pan_index)

        # Типичный вес
        if dish['default_cooked_weight'] is not None:
            self.weight_var.set(str(dish['default_cooked_weight']))
        else:
            self.weight_var.set('')

        # Загружаем состав
        self.refresh_composition_table()

    def clear_right_panel(self):
        """Очищает правую панель (когда блюдо не выбрано)."""
        self.name_var.set('')
        self.pan_combo.current(0)
        self.weight_var.set('')
        for row in self.comp_tree.get_children():
            self.comp_tree.delete(row)

    def save_dish_details(self):
        """Сохраняет изменения в полях названия, кастрюли и веса."""
        if self.current_dish_id is None:
            return
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Название блюда не может быть пустым")
            # Возвращаем старое значение
            dish = database.get_dish(self.current_dish_id)
            if dish:
                self.name_var.set(dish['name'])
            return

        # Получаем id кастрюли из выбранного элемента
        pan_index = self.pan_combo.current()
        if pan_index < 0:
            pan_id = None
        else:
            pan_id = self.pans_list[pan_index][0]
            if pan_id == 0:
                pan_id = None

        # Вес
        weight_str = self.weight_var.get().strip()
        if weight_str:
            try:
                weight = float(weight_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Вес должен быть числом")
                dish = database.get_dish(self.current_dish_id)
                if dish and dish['default_cooked_weight']:
                    self.weight_var.set(str(dish['default_cooked_weight']))
                else:
                    self.weight_var.set('')
                return
        else:
            weight = None

        # Сохраняем в БД
        database.update_dish(self.current_dish_id, name, pan_id, weight)

        # Обновляем название в списке слева
        self.refresh_dishes_list()
        # Находим и выделяем это же блюдо (по id)
        for i, (did, _) in enumerate(self.dish_items):
            if did == self.current_dish_id:
                self.dishes_listbox.selection_set(i)
                break

    def refresh_composition_table(self):
        """Обновляет таблицу состава для текущего блюда."""
        for row in self.comp_tree.get_children():
            self.comp_tree.delete(row)
        if self.current_dish_id is None:
            return
        comp = database.get_dish_composition(self.current_dish_id)
        for item in comp:
            self.comp_tree.insert('', 'end', values=(item['product_name'], item['weight']), tags=(item['product_id'],))

    def new_dish(self):
        """Создание нового блюда."""
        name = simpledialog.askstring("Новое блюдо", "Введите название блюда:", parent=self)
        if not name:
            return
        # Проверка уникальности (можно не делать, пусть БД выдаст ошибку, но лучше проверить)
        try:
            dish_id = database.add_dish(name, None, None)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать блюдо: {e}")
            return
        self.refresh_dishes_list()
        # Выделяем новое блюдо
        for i, (did, _) in enumerate(self.dish_items):
            if did == dish_id:
                self.dishes_listbox.selection_set(i)
                self.current_dish_id = dish_id
                self.load_dish_details()
                break

    def delete_dish(self):
        """Удаление выбранного блюда."""
        if self.current_dish_id is None:
            messagebox.showwarning("Предупреждение", "Выберите блюдо для удаления")
            return
        if messagebox.askyesno("Подтверждение", f"Удалить блюдо '{self.name_var.get()}'?"):
            database.delete_dish(self.current_dish_id)
            self.current_dish_id = None
            self.refresh_dishes_list()
            self.clear_right_panel()

    def add_product_to_dish(self):
        """Добавление продукта в состав блюда."""
        if self.current_dish_id is None:
            messagebox.showwarning("Предупреждение", "Сначала выберите блюдо")
            return

        # Диалог выбора продукта
        dialog = tk.Toplevel(self)
        dialog.title("Добавить продукт")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("400x300")

        ttk.Label(dialog, text="Выберите продукт:").pack(pady=5)

        # Список продуктов
        listbox = tk.Listbox(dialog)
        listbox.pack(fill='both', expand=True, padx=10, pady=5)
        scrollbar = ttk.Scrollbar(listbox, orient='vertical', command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        # Заполняем список
        products = database.get_all_products()
        product_map = {}
        for p in products:
            listbox.insert(tk.END, p['name'])
            product_map[p['name']] = p['id']

        # Поле ввода веса
        weight_frame = ttk.Frame(dialog)
        weight_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(weight_frame, text="Вес (г):").pack(side='left')
        weight_entry = ttk.Entry(weight_frame, width=10)
        weight_entry.pack(side='left', padx=5)
        weight_entry.insert(0, "100")

        def add():
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror("Ошибка", "Выберите продукт")
                return
            product_name = listbox.get(selection[0])
            product_id = product_map[product_name]
            try:
                weight = float(weight_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Вес должен быть числом")
                return

            # Проверяем, есть ли уже такой продукт в составе
            comp = database.get_dish_composition(self.current_dish_id)
            existing = [item for item in comp if item['product_id'] == product_id]
            if existing:
                # Спрашиваем, заменить ли?
                if messagebox.askyesno("Подтверждение", f"Продукт '{product_name}' уже есть в составе. Заменить вес?"):
                    database.update_dish_composition(self.current_dish_id, product_id, weight)
                else:
                    dialog.destroy()
                    return
            else:
                database.add_dish_composition(self.current_dish_id, product_id, weight)

            self.refresh_composition_table()
            dialog.destroy()

        ttk.Button(dialog, text="Добавить", command=add).pack(pady=5)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)

    def edit_product_weight(self):
        """Изменение веса выбранного продукта в составе."""
        if self.current_dish_id is None:
            return
        selected = self.comp_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите продукт в таблице состава")
            return
        item = self.comp_tree.item(selected[0])
        product_id = item['tags'][0]  # мы сохранили product_id в tags
        current_weight = item['values'][1]

        new_weight = simpledialog.askfloat("Изменить вес", "Новый вес (г):", initialvalue=current_weight, parent=self)
        if new_weight is not None and new_weight > 0:
            database.update_dish_composition(self.current_dish_id, product_id, new_weight)
            self.refresh_composition_table()

    def delete_product_from_dish(self):
        """Удаление продукта из состава."""
        if self.current_dish_id is None:
            return
        selected = self.comp_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите продукт в таблице состава")
            return
        item = self.comp_tree.item(selected[0])
        product_id = item['tags'][0]
        product_name = item['values'][0]
        if messagebox.askyesno("Подтверждение", f"Удалить '{product_name}' из состава?"):
            database.delete_dish_composition(self.current_dish_id, product_id)
            self.refresh_composition_table()