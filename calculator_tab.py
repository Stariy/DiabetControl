import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database
from utils import calculate_product_nutrition, calculate_gn, calculate_xe
from config import DEFAULT_CARBS_PER_XE

class CalculatorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.components = []  # список компонентов текущего приёма
        self.current_component_index = None
        self.pans_list = []   # список кортежей (id, name, weight)
        self.products_list = []  # список продуктов для диалогов
        self.dishes_list = []    # список блюд
        self.carbs_per_xe = DEFAULT_CARBS_PER_XE  # позже будет браться из настроек

        self.create_widgets()
        self.load_lists()

    def create_widgets(self):
        # Основной контейнер разделён на три части
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)

        # Левая панель (список компонентов)
        left_frame = ttk.Frame(main_paned, width=250, relief='sunken', padding=5)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Состав приёма", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.components_listbox = tk.Listbox(left_frame)
        self.components_listbox.pack(fill='both', expand=True, pady=5)
        self.components_listbox.bind('<<ListboxSelect>>', self.on_component_select)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="+ Блюдо", command=self.add_dish).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="+ Продукт", command=self.add_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_component).pack(side='left', padx=2)

        # Правая панель (детали выбранного компонента)
        right_frame = ttk.Frame(main_paned, padding=5)
        main_paned.add(right_frame, weight=3)

        # Место для деталей (будет заполняться динамически)
        self.details_frame = ttk.Frame(right_frame)
        self.details_frame.pack(fill='both', expand=True)

        # Нижняя панель (итоги)
        bottom_frame = ttk.Frame(self, relief='raised', padding=5)
        bottom_frame.pack(side='bottom', fill='x')

        self.total_vars = {
            'calories': tk.StringVar(value='0.0'),
            'proteins': tk.StringVar(value='0.0'),
            'fats': tk.StringVar(value='0.0'),
            'carbs': tk.StringVar(value='0.0'),
            'gn': tk.StringVar(value='0.0'),
            'xe': tk.StringVar(value='0.0')
        }

        ttk.Label(bottom_frame, text="Итого:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5)
        ttk.Label(bottom_frame, text="Ккал:").grid(row=0, column=1, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['calories']).grid(row=0, column=2, padx=5, sticky='w')
        ttk.Label(bottom_frame, text="Белки:").grid(row=0, column=3, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['proteins']).grid(row=0, column=4, padx=5, sticky='w')
        ttk.Label(bottom_frame, text="Жиры:").grid(row=0, column=5, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['fats']).grid(row=0, column=6, padx=5, sticky='w')
        ttk.Label(bottom_frame, text="Углеводы:").grid(row=0, column=7, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['carbs']).grid(row=0, column=8, padx=5, sticky='w')
        ttk.Label(bottom_frame, text="ГН:").grid(row=1, column=1, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['gn']).grid(row=1, column=2, padx=5, sticky='w')
        ttk.Label(bottom_frame, text="ХЕ:").grid(row=1, column=3, padx=5, sticky='e')
        ttk.Label(bottom_frame, textvariable=self.total_vars['xe']).grid(row=1, column=4, padx=5, sticky='w')

        ttk.Button(bottom_frame, text="Записать приём", command=self.save_meal).grid(row=0, column=9, rowspan=2, padx=20)

    def load_lists(self):
        """Загружает списки продуктов, блюд, кастрюль."""
        prods = database.get_all_products()
        self.products_list = [(p['id'], p['name']) for p in prods]

        dishes = database.get_all_dishes()
        self.dishes_list = [(d['id'], d['name']) for d in dishes]

        pans = database.get_all_pans()
        self.pans_list = [(0, '— нет —', 0)] + [(p['id'], p['name'], p['weight']) for p in pans]

    def add_dish(self):
        """Добавление блюда в приём."""
        if not self.dishes_list:
            messagebox.showwarning("Предупреждение", "Сначала создайте хотя бы одно блюдо")
            return
        # Диалог выбора блюда
        dialog = tk.Toplevel(self)
        dialog.title("Выберите блюдо")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("300x400")

        listbox = tk.Listbox(dialog)
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        for _, name in self.dishes_list:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if not sel:
                return
            dish_id, dish_name = self.dishes_list[sel[0]]
            # Создаём компонент блюда
            dish_data = database.get_dish(dish_id)
            composition = database.get_dish_composition(dish_id)
            # Преобразуем состав в список словарей с продуктами
            comp_list = []
            for item in composition:
                prod = database.get_product(item['product_id'])
                comp_list.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'original_weight': item['weight'],
                    'current_weight': item['weight'],
                    'product_data': prod
                })
            component = {
                'type': 'dish',
                'id': dish_id,
                'name': dish_name,
                'composition': comp_list,
                'pan_id': dish_data['default_pan_id'] if dish_data else None,
                'pan_name': self._get_pan_name(dish_data['default_pan_id']) if dish_data else None,
                'pan_weight': self._get_pan_weight(dish_data['default_pan_id']) if dish_data else 0,
                'cooked_weight': dish_data['default_cooked_weight'] if dish_data else None,
                'serving_weight': None,  # будет вычислено позже
            }
            self.components.append(component)
            self.update_components_list()
            dialog.destroy()

        ttk.Button(dialog, text="Выбрать", command=select).pack(pady=5)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)

    def add_product(self):
        """Добавление отдельного продукта."""
        if not self.products_list:
            messagebox.showwarning("Предупреждение", "Сначала создайте хотя бы один продукт")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Выберите продукт")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("300x400")

        listbox = tk.Listbox(dialog)
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        for _, name in self.products_list:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if not sel:
                return
            prod_id, prod_name = self.products_list[sel[0]]
            component = {
                'type': 'product',
                'id': prod_id,
                'name': prod_name,
                'serving_weight': None,  # будет задано позже
                'product_data': database.get_product(prod_id)
            }
            self.components.append(component)
            self.update_components_list()
            dialog.destroy()

        ttk.Button(dialog, text="Выбрать", command=select).pack(pady=5)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)

    def delete_component(self):
        """Удаление выбранного компонента."""
        if self.current_component_index is None:
            return
        if messagebox.askyesno("Подтверждение", "Удалить этот компонент?"):
            del self.components[self.current_component_index]
            self.current_component_index = None
            self.update_components_list()
            self.clear_details()
            self.update_totals()

    def update_components_list(self):
        """Обновляет список компонентов в Listbox."""
        self.components_listbox.delete(0, tk.END)
        for i, comp in enumerate(self.components):
            text = f"{'🍲' if comp['type']=='dish' else '🍎'} {comp['name']}"
            self.components_listbox.insert(tk.END, text)

    def on_component_select(self, event):
        """Обработчик выбора компонента из списка."""
        sel = self.components_listbox.curselection()
        if not sel:
            return
        index = sel[0]
        # Проверка на несохранённые изменения в предыдущем компоненте
        if not self.check_unsaved_changes():
            # Возвращаем выделение на предыдущий
            self.components_listbox.selection_set(self.current_component_index)
            return
        self.current_component_index = index
        self.show_component_details(index)

    def check_unsaved_changes(self):
        """
        Проверяет, есть ли в текущем компоненте-блюде несохранённые изменения.
        Возвращает True, если можно переключаться, иначе False (после обработки).
        """
        if self.current_component_index is None:
            return True
        comp = self.components[self.current_component_index]
        if comp['type'] != 'dish':
            return True
        # Сравниваем текущие веса с исходными (original_weight)
        changed = False
        for item in comp['composition']:
            if item['current_weight'] != item['original_weight']:
                changed = True
                break
        if not changed:
            return True

        # Спрашиваем пользователя
        answer = messagebox.askyesnocancel(
            "Несохранённые изменения",
            f"В составе блюда '{comp['name']}' есть изменения. Сохранить их как новый рецепт?",
            detail="Да — сохранить как новое блюдо\nНет — отбросить изменения\nОтмена — остаться на текущем компоненте"
        )
        if answer is None:  # Отмена
            return False
        elif answer:  # Да
            self.save_as_recipe(comp)
        else:  # Нет
            # Откатываем изменения: возвращаем original_weight
            for item in comp['composition']:
                item['current_weight'] = item['original_weight']
        return True

    def save_as_recipe(self, comp):
        """Сохранение текущего состава блюда как нового рецепта."""
        # Диалог выбора: новое блюдо или обновить существующее
        dialog = tk.Toplevel(self)
        dialog.title("Сохранение рецепта")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Сохранить как:").pack(pady=5)
        var = tk.StringVar(value="new")
        ttk.Radiobutton(dialog, text="Новое блюдо", variable=var, value="new").pack(anchor='w', padx=20)
        ttk.Radiobutton(dialog, text="Обновить текущее", variable=var, value="update").pack(anchor='w', padx=20)

        def do_save():
            if var.get() == "new":
                new_name = simpledialog.askstring("Новое блюдо", "Введите название:", parent=dialog)
                if not new_name:
                    return
                # Создаём новое блюдо
                dish_id = database.add_dish(new_name, comp['pan_id'], comp['cooked_weight'])
                # Добавляем состав
                for item in comp['composition']:
                    database.add_dish_composition(dish_id, item['product_id'], item['current_weight'])
                # Обновляем списки
                self.load_lists()
                messagebox.showinfo("Инфо", "Новое блюдо сохранено")
                # Не меняем текущий компонент, но можно предложить заменить?
                # Оставляем как есть.
            else:  # update
                # Обновляем существующее блюдо
                database.update_dish(comp['id'], comp['name'], comp['pan_id'], comp['cooked_weight'])
                # Очищаем старый состав и добавляем новый
                current_comp = database.get_dish_composition(comp['id'])
                for item in current_comp:
                    database.delete_dish_composition(comp['id'], item['product_id'])
                for item in comp['composition']:
                    database.add_dish_composition(comp['id'], item['product_id'], item['current_weight'])
                # Теперь обновляем original_weight в текущем компоненте, чтобы новые изменения считались от новой базы
                for item in comp['composition']:
                    item['original_weight'] = item['current_weight']
                messagebox.showinfo("Инфо", "Рецепт обновлён")
            dialog.destroy()

        ttk.Button(dialog, text="Сохранить", command=do_save).pack(pady=5)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack(pady=5)

    def show_component_details(self, index):
        """Отображает панель деталей для компонента с заданным индексом."""
        self.clear_details()
        comp = self.components[index]
        if comp['type'] == 'product':
            self.show_product_details(index, comp)
        else:
            self.show_dish_details(index, comp)

    def clear_details(self):
        for widget in self.details_frame.winfo_children():
            widget.destroy()

    def show_product_details(self, index, comp):
        """Панель для продукта."""
        ttk.Label(self.details_frame, text=f"Продукт: {comp['name']}", font=('Arial', 11, 'bold')).pack(anchor='w', pady=5)

        frame = ttk.Frame(self.details_frame)
        frame.pack(fill='x', pady=5)
        ttk.Label(frame, text="Вес порции (г):").pack(side='left')
        weight_var = tk.StringVar()
        if comp['serving_weight']:
            weight_var.set(str(comp['serving_weight']))
        entry = ttk.Entry(frame, textvariable=weight_var, width=10)
        entry.pack(side='left', padx=5)
        entry.bind('<KeyRelease>', lambda e, idx=index: self.update_product_weight(idx, weight_var.get()))

        self.product_nutrition_label = ttk.Label(self.details_frame, text="")
        self.product_nutrition_label.pack(anchor='w', pady=5)

        if comp['serving_weight']:
            self.update_product_weight(index, weight_var.get())

    def update_product_weight(self, index, weight_str):
        """Обновляет вес продукта и пересчитывает итоги."""
        try:
            weight = float(weight_str)
        except ValueError:
            return
        comp = self.components[index]
        comp['serving_weight'] = weight
        nut = calculate_product_nutrition(comp['product_data'], weight)
        gn = calculate_gn(nut['carbs'], comp['product_data']['glycemic_index'])
        xe = calculate_xe(nut['carbs'], self.carbs_per_xe)
        self.product_nutrition_label.config(
            text=f"Ккал: {nut['calories']:.1f}, Белки: {nut['proteins']:.1f}, "
                 f"Жиры: {nut['fats']:.1f}, Углеводы: {nut['carbs']:.1f}, "
                 f"ГН: {gn:.1f}, ХЕ: {xe:.2f}"
        )
        self.update_totals()

    def show_dish_details(self, index, comp):
        """Панель для блюда."""
        title_frame = ttk.Frame(self.details_frame)
        title_frame.pack(fill='x', pady=5)
        ttk.Label(title_frame, text=f"Блюдо: {comp['name']}", font=('Arial', 11, 'bold')).pack(side='left')
        ttk.Button(title_frame, text="Сохранить как рецепт", command=lambda: self.save_as_recipe(comp)).pack(side='right')

        # Выбор кастрюли
        pan_frame = ttk.Frame(self.details_frame)
        pan_frame.pack(fill='x', pady=5)
        ttk.Label(pan_frame, text="Кастрюля:").pack(side='left')
        self.pan_var = tk.StringVar()
        pan_combo = ttk.Combobox(pan_frame, textvariable=self.pan_var, values=[p[1] for p in self.pans_list],
                                 state='readonly', width=30)
        pan_combo.pack(side='left', padx=5)
        current_pan_id = comp.get('pan_id')
        for i, (pid, name, _) in enumerate(self.pans_list):
            if pid == current_pan_id:
                pan_combo.current(i)
                break
        else:
            pan_combo.current(0)
        pan_combo.bind('<<ComboboxSelected>>', lambda e, idx=index: self.update_dish_pan(idx, self.pan_var.get()))

        # Вес готового блюда
        cooked_frame = ttk.Frame(self.details_frame)
        cooked_frame.pack(fill='x', pady=5)
        ttk.Label(cooked_frame, text="Вес готового блюда с кастрюлей (г):").pack(side='left')
        self.cooked_var = tk.StringVar()
        if comp.get('cooked_weight'):
            self.cooked_var.set(str(comp['cooked_weight']))
        cooked_entry = ttk.Entry(cooked_frame, textvariable=self.cooked_var, width=10)
        cooked_entry.pack(side='left', padx=5)
        cooked_entry.bind('<KeyRelease>', lambda e, idx=index: self.update_dish_cooked(idx, self.cooked_var.get()))

        # Вес порции
        serving_frame = ttk.Frame(self.details_frame)
        serving_frame.pack(fill='x', pady=5)
        ttk.Label(serving_frame, text="Вес порции (г):").pack(side='left')
        self.serving_var = tk.StringVar()
        if comp.get('serving_weight'):
            self.serving_var.set(str(comp['serving_weight']))
        serving_entry = ttk.Entry(serving_frame, textvariable=self.serving_var, width=10)
        serving_entry.pack(side='left', padx=5)
        serving_entry.bind('<KeyRelease>', lambda e, idx=index: self.update_dish_serving(idx, self.serving_var.get()))

        # Таблица состава
        ttk.Label(self.details_frame, text="Состав блюда (веса можно редактировать):").pack(anchor='w', pady=(10, 0))

        columns = ('product', 'weight')
        self.comp_tree = ttk.Treeview(self.details_frame, columns=columns, show='headings', height=8)
        self.comp_tree.heading('product', text='Продукт')
        self.comp_tree.heading('weight', text='Вес (г)')
        self.comp_tree.column('product', width=200)
        self.comp_tree.column('weight', width=100)
        self.comp_tree.pack(fill='both', expand=True, pady=5)

        for item in comp['composition']:
            self.comp_tree.insert('', 'end', values=(item['product_name'], item['current_weight']),
                                  tags=(item['product_id'],))

        self.comp_tree.bind('<Double-1>', self.on_dish_product_double_click)

        self.dish_nutrition_label = ttk.Label(self.details_frame, text="")
        self.dish_nutrition_label.pack(anchor='w', pady=5)

        self.update_dish_nutrition(index)

    def on_dish_product_double_click(self, event):
        """Редактирование веса продукта в составе блюда."""
        item = self.comp_tree.selection()
        if not item:
            return
        item = item[0]
        values = self.comp_tree.item(item, 'values')
        product_name = values[0]
        current_weight = values[1]
        new_weight = simpledialog.askfloat("Изменить вес", f"Новый вес для {product_name} (г):",
                                           initialvalue=current_weight, parent=self)
        if new_weight is not None and new_weight > 0:
            product_id = self.comp_tree.item(item, 'tags')[0]
            comp = self.components[self.current_component_index]
            for prod in comp['composition']:
                if prod['product_id'] == product_id:
                    prod['current_weight'] = new_weight
                    break
            self.comp_tree.item(item, values=(product_name, new_weight))
            self.update_dish_nutrition(self.current_component_index)

    def update_dish_pan(self, index, pan_name):
        """Обновляет выбранную кастрюлю."""
        comp = self.components[index]
        for pid, name, weight in self.pans_list:
            if name == pan_name:
                comp['pan_id'] = pid if pid != 0 else None
                comp['pan_name'] = name if pid != 0 else None
                comp['pan_weight'] = weight if pid != 0 else 0
                break
        self.update_dish_nutrition(index)

    def update_dish_cooked(self, index, weight_str):
        """Обновляет вес готового блюда."""
        try:
            weight = float(weight_str)
        except ValueError:
            return
        self.components[index]['cooked_weight'] = weight
        self.update_dish_nutrition(index)

    def update_dish_serving(self, index, weight_str):
        """Обновляет вес порции."""
        try:
            weight = float(weight_str)
        except ValueError:
            return
        self.components[index]['serving_weight'] = weight
        self.update_dish_nutrition(index)

    def update_dish_nutrition(self, index):
        """Пересчитывает и отображает КБЖУ для порции блюда."""
        comp = self.components[index]
        if not comp.get('cooked_weight') or not comp.get('serving_weight') or comp['pan_weight'] is None:
            self.dish_nutrition_label.config(text="Заполните вес готового блюда и порции, выберите кастрюлю")
            return

        cooked_with_pan = comp['cooked_weight']
        pan_weight = comp['pan_weight']
        net_weight = cooked_with_pan - pan_weight
        if net_weight <= 0:
            self.dish_nutrition_label.config(text="Ошибка: вес нетто блюда должен быть положительным")
            return

        portion = comp['serving_weight']
        if portion <= 0:
            self.dish_nutrition_label.config(text="Вес порции должен быть положительным")
            return

        factor = portion / net_weight

        total_calories = 0
        total_proteins = 0
        total_fats = 0
        total_carbs = 0
        total_gn = 0
        for prod in comp['composition']:
            nut = calculate_product_nutrition(prod['product_data'], prod['current_weight'])
            total_calories += nut['calories']
            total_proteins += nut['proteins']
            total_fats += nut['fats']
            total_carbs += nut['carbs']
            gn = calculate_gn(nut['carbs'], prod['product_data']['glycemic_index'])
            total_gn += gn

        cal_portion = total_calories * factor
        prot_portion = total_proteins * factor
        fat_portion = total_fats * factor
        carb_portion = total_carbs * factor
        gn_portion = total_gn * factor
        xe_portion = calculate_xe(carb_portion, self.carbs_per_xe)

        comp['_nutrition'] = {
            'calories': cal_portion,
            'proteins': prot_portion,
            'fats': fat_portion,
            'carbs': carb_portion,
            'gn': gn_portion,
            'xe': xe_portion
        }

        self.dish_nutrition_label.config(
            text=f"Порция: Ккал: {cal_portion:.1f}, Белки: {prot_portion:.1f}, "
                 f"Жиры: {fat_portion:.1f}, Углеводы: {carb_portion:.1f}, "
                 f"ГН: {gn_portion:.1f}, ХЕ: {xe_portion:.2f}"
        )
        self.update_totals()

    def update_totals(self):
        """Обновляет итоговые суммы по всем компонентам."""
        total_cal = total_prot = total_fat = total_carb = total_gn = 0.0
        for comp in self.components:
            if comp['type'] == 'product':
                if comp.get('serving_weight') and comp.get('product_data'):
                    nut = calculate_product_nutrition(comp['product_data'], comp['serving_weight'])
                    total_cal += nut['calories']
                    total_prot += nut['proteins']
                    total_fat += nut['fats']
                    total_carb += nut['carbs']
                    total_gn += calculate_gn(nut['carbs'], comp['product_data']['glycemic_index'])
            else:
                if '_nutrition' in comp:
                    n = comp['_nutrition']
                    total_cal += n['calories']
                    total_prot += n['proteins']
                    total_fat += n['fats']
                    total_carb += n['carbs']
                    total_gn += n['gn']
        total_xe = calculate_xe(total_carb, self.carbs_per_xe)
        self.total_vars['calories'].set(f"{total_cal:.1f}")
        self.total_vars['proteins'].set(f"{total_prot:.1f}")
        self.total_vars['fats'].set(f"{total_fat:.1f}")
        self.total_vars['carbs'].set(f"{total_carb:.1f}")
        self.total_vars['gn'].set(f"{total_gn:.1f}")
        self.total_vars['xe'].set(f"{total_xe:.2f}")

    def save_meal(self):
        """Сохраняет текущий приём пищи в историю."""
        if not self.components:
            messagebox.showwarning("Предупреждение", "Нет компонентов для сохранения")
            return
        for comp in self.components:
            if comp['type'] == 'product' and not comp.get('serving_weight'):
                messagebox.showerror("Ошибка", f"У продукта '{comp['name']}' не указан вес порции")
                return
            if comp['type'] == 'dish':
                if not comp.get('cooked_weight') or not comp.get('serving_weight') or comp.get('pan_weight') is None:
                    messagebox.showerror("Ошибка", f"У блюда '{comp['name']}' не заполнены все параметры")
                    return
                if comp['cooked_weight'] - comp['pan_weight'] <= 0:
                    messagebox.showerror("Ошибка", f"У блюда '{comp['name']}' вес нетто не положителен")
                    return

        dialog = tk.Toplevel(self)
        dialog.title("Сохранение приёма")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("300x250")

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        ttk.Label(dialog, text="Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ):").pack(pady=5)
        datetime_var = tk.StringVar(value=now)
        ttk.Entry(dialog, textvariable=datetime_var, width=20).pack()

        ttk.Label(dialog, text="Доза инсулина (ед):").pack(pady=5)
        insulin_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=insulin_var, width=10).pack()

        ttk.Label(dialog, text="Примечание:").pack(pady=5)
        notes_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=notes_var, width=30).pack()

        def do_save():
            dt = datetime_var.get().strip()
            insulin = insulin_var.get().strip()
            insulin = float(insulin) if insulin else None
            notes = notes_var.get().strip() or None

            components_for_db = []
            for comp in self.components:
                if comp['type'] == 'product':
                    components_for_db.append({
                        'type': 'product',
                        'id': comp['id'],
                        'name': comp['name'],
                        'serving_weight': comp['serving_weight']
                    })
                else:
                    net_weight = comp['cooked_weight'] - comp['pan_weight']
                    factor = comp['serving_weight'] / net_weight
                    composition_portion = []
                    for prod in comp['composition']:
                        composition_portion.append({
                            'product_id': prod['product_id'],
                            'weight': prod['current_weight'] * factor
                        })
                    components_for_db.append({
                        'type': 'dish',
                        'id': comp['id'],
                        'name': comp['name'],
                        'serving_weight': comp['serving_weight'],
                        'cooked_weight': comp['cooked_weight'],
                        'pan_id': comp['pan_id'],
                        'composition': composition_portion
                    })

            try:
                database.save_meal(dt, insulin, notes, components_for_db)
                messagebox.showinfo("Успех", "Приём пищи сохранён")
                dialog.destroy()
                if messagebox.askyesno("Очистить", "Очистить текущий приём?"):
                    self.components.clear()
                    self.current_component_index = None
                    self.update_components_list()
                    self.clear_details()
                    self.update_totals()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

        ttk.Button(dialog, text="Сохранить", command=do_save).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack()

    def _get_pan_name(self, pan_id):
        for pid, name, _ in self.pans_list:
            if pid == pan_id:
                return name
        return None

    def _get_pan_weight(self, pan_id):
        for pid, _, weight in self.pans_list:
            if pid == pan_id:
                return weight
        return 0