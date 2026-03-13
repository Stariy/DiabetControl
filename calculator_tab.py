import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database
from utils import calculate_product_nutrition, calculate_gn, calculate_xe
from config import DEFAULT_CARBS_PER_XE


class CalculatorTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.components = []  # список компонентов текущего приёма
        self.products_list = []  # список продуктов для диалогов
        self.dishes_list = []  # список блюд
        self.carbs_per_xe = DEFAULT_CARBS_PER_XE

        # Коэффициенты для расчёта инсулина (будут загружены из БД)
        self.insulin_factors = {
            'carb_coefficient': 1.0,  # ед инсулина на 1 ХЕ
            'target_glucose': 6.0,  # целевой уровень сахара ммоль/л
            'sensitivity': 2.0  # на сколько ммоль/л снижает 1 ед инсулина
        }

        self.create_widgets()
        self.load_lists()
        self.load_settings()

        # Привязываем событие появления вкладки для обновления списков
        self.bind('<Map>', self.on_tab_show)

    def on_tab_show(self, event):
        """Вызывается при активации вкладки для обновления списков."""
        self.load_lists()
        self.load_settings()

    def load_settings(self):
        """Загружает настройки из базы данных."""
        settings = database.get_settings()
        if settings:
            self.insulin_factors['carb_coefficient'] = settings.get('carb_coefficient', 1.0)
            self.insulin_factors['target_glucose'] = settings.get('target_glucose', 6.0)
            self.insulin_factors['sensitivity'] = settings.get('sensitivity', 2.0)

            # Обновляем поля ввода
            self.carb_coef_var.set(str(self.insulin_factors['carb_coefficient']))
            self.target_glucose_var.set(str(self.insulin_factors['target_glucose']))
            self.sensitivity_var.set(str(self.insulin_factors['sensitivity']))

    def save_settings(self):
        """Сохраняет настройки в базу данных."""
        try:
            carb_coef = float(self.carb_coef_var.get())
            target_glucose = float(self.target_glucose_var.get())
            sensitivity = float(self.sensitivity_var.get())

            database.save_settings({
                'carb_coefficient': carb_coef,
                'target_glucose': target_glucose,
                'sensitivity': sensitivity
            })

            self.insulin_factors['carb_coefficient'] = carb_coef
            self.insulin_factors['target_glucose'] = target_glucose
            self.insulin_factors['sensitivity'] = sensitivity

            # Пересчитываем дозу инсулина
            self.update_insulin_dose()

        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность ввода коэффициентов")

    def create_widgets(self):
        # Создаём PanedWindow для разделения на верхнюю и нижнюю части
        main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)

        # ==================== ВЕРХНЯЯ ЧАСТЬ ====================
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=2)

        # Кнопки добавления
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill='x', pady=(0, 5))

        ttk.Button(btn_frame, text="+ Добавить блюдо", command=self.add_dish).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="+ Добавить продукт", command=self.add_product).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить выбранное", command=self.delete_component).pack(side='left', padx=2)

        # Таблица состава приёма
        columns = ('name', 'calories', 'proteins', 'fats', 'carbs', 'gn', 'weight')
        self.tree = ttk.Treeview(top_frame, columns=columns, show='headings', height=10)

        # Настройка заголовков
        self.tree.heading('name', text='Название')
        self.tree.heading('calories', text='Ккал/100г')
        self.tree.heading('proteins', text='Б/100г')
        self.tree.heading('fats', text='Ж/100г')
        self.tree.heading('carbs', text='У/100г')
        self.tree.heading('gn', text='ГН/100г')
        self.tree.heading('weight', text='Вес порции (г)')

        # Настройка ширины колонок
        self.tree.column('name', width=250, anchor='w')
        self.tree.column('calories', width=80, anchor='center')
        self.tree.column('proteins', width=60, anchor='center')
        self.tree.column('fats', width=60, anchor='center')
        self.tree.column('carbs', width=60, anchor='center')
        self.tree.column('gn', width=70, anchor='center')
        self.tree.column('weight', width=100, anchor='center')

        # Настраиваем теги для чередования фона
        self.tree.tag_configure('oddrow', background='#f0f0f0')
        self.tree.tag_configure('evenrow', background='#ffffff')
        self.tree.tag_configure('dish', font=('Arial', 10, 'bold'))
        self.tree.tag_configure('product', font=('Arial', 10))

        # Привязываем двойной щелчок для редактирования веса
        self.tree.bind('<Double-1>', self.on_item_double_click)

        # Скроллбар для таблицы
        scrollbar = ttk.Scrollbar(top_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Размещаем таблицу и скроллбар
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # ==================== НИЖНЯЯ ЧАСТЬ ====================
        bottom_frame = ttk.Frame(main_paned, relief='raised', padding=5)
        main_paned.add(bottom_frame, weight=1)

        # Левая часть нижней панели - итоговые КБЖУ
        left_bottom = ttk.Frame(bottom_frame)
        left_bottom.pack(side='left', fill='both', expand=True)

        ttk.Label(left_bottom, text="ИТОГО:", font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 5))

        # Создаём переменные для итогов
        self.total_vars = {
            'calories': tk.StringVar(value='0.0'),
            'proteins': tk.StringVar(value='0.0'),
            'fats': tk.StringVar(value='0.0'),
            'carbs': tk.StringVar(value='0.0'),
            'gn': tk.StringVar(value='0.0'),
            'xe': tk.StringVar(value='0.0')
        }

        # Сетка для итогов
        total_frame = ttk.Frame(left_bottom)
        total_frame.pack(fill='x', pady=5)

        row1 = ttk.Frame(total_frame)
        row1.pack(fill='x', pady=2)
        ttk.Label(row1, text="Калории:", width=15).pack(side='left')
        ttk.Label(row1, textvariable=self.total_vars['calories'], width=10, anchor='e').pack(side='left')
        ttk.Label(row1, text="ккал", width=5).pack(side='left')

        ttk.Label(row1, text="Белки:", width=15).pack(side='left', padx=(20, 0))
        ttk.Label(row1, textvariable=self.total_vars['proteins'], width=10, anchor='e').pack(side='left')
        ttk.Label(row1, text="г", width=5).pack(side='left')

        row2 = ttk.Frame(total_frame)
        row2.pack(fill='x', pady=2)
        ttk.Label(row2, text="Жиры:", width=15).pack(side='left')
        ttk.Label(row2, textvariable=self.total_vars['fats'], width=10, anchor='e').pack(side='left')
        ttk.Label(row2, text="г", width=5).pack(side='left')

        ttk.Label(row2, text="Углеводы:", width=15).pack(side='left', padx=(20, 0))
        ttk.Label(row2, textvariable=self.total_vars['carbs'], width=10, anchor='e').pack(side='left')
        ttk.Label(row2, text="г", width=5).pack(side='left')

        row3 = ttk.Frame(total_frame)
        row3.pack(fill='x', pady=2)
        ttk.Label(row3, text="ГН:", width=15).pack(side='left')
        ttk.Label(row3, textvariable=self.total_vars['gn'], width=10, anchor='e').pack(side='left')

        ttk.Label(row3, text="ХЕ:", width=15).pack(side='left', padx=(20, 0))
        ttk.Label(row3, textvariable=self.total_vars['xe'], width=10, anchor='e').pack(side='left')

        # Правая часть нижней панели - расчёт инсулина
        right_bottom = ttk.Frame(bottom_frame, relief='groove', padding=10)
        right_bottom.pack(side='right', fill='both', padx=(10, 0))

        ttk.Label(right_bottom, text="РАСЧЁТ ИНСУЛИНА", font=('Arial', 11, 'bold')).pack(anchor='w', pady=(0, 10))

        # Коэффициенты
        coef_frame = ttk.Frame(right_bottom)
        coef_frame.pack(fill='x', pady=5)

        # Коэффициент на ХЕ
        ttk.Label(coef_frame, text="1 ед на ХЕ:").grid(row=0, column=0, sticky='w', pady=2)
        self.carb_coef_var = tk.StringVar(value=str(self.insulin_factors['carb_coefficient']))
        ttk.Entry(coef_frame, textvariable=self.carb_coef_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Button(coef_frame, text="✓", command=self.save_settings, width=3).grid(row=0, column=2)

        # Целевой сахар
        ttk.Label(coef_frame, text="Цель ммоль/л:").grid(row=1, column=0, sticky='w', pady=2)
        self.target_glucose_var = tk.StringVar(value=str(self.insulin_factors['target_glucose']))
        ttk.Entry(coef_frame, textvariable=self.target_glucose_var, width=8).grid(row=1, column=1, padx=5)

        # Чувствительность
        ttk.Label(coef_frame, text="1 ед снижает на:").grid(row=2, column=0, sticky='w', pady=2)
        self.sensitivity_var = tk.StringVar(value=str(self.insulin_factors['sensitivity']))
        ttk.Entry(coef_frame, textvariable=self.sensitivity_var, width=8).grid(row=2, column=1, padx=5)

        # Текущий сахар
        ttk.Label(coef_frame, text="Текущий сахар:").grid(row=3, column=0, sticky='w', pady=(10, 2))
        self.current_glucose_var = tk.StringVar()
        ttk.Entry(coef_frame, textvariable=self.current_glucose_var, width=8).grid(row=3, column=1, padx=5)
        self.current_glucose_var.trace('w', lambda *args: self.update_insulin_dose())

        # Результат
        result_frame = ttk.Frame(right_bottom)
        result_frame.pack(fill='x', pady=10)

        ttk.Label(result_frame, text="Доза инсулина:", font=('Arial', 10, 'bold')).pack(side='left')
        self.insulin_dose_var = tk.StringVar(value="0.0")
        ttk.Label(result_frame, textvariable=self.insulin_dose_var, font=('Arial', 12, 'bold'),
                  foreground='blue').pack(side='left', padx=5)
        ttk.Label(result_frame, text="ед").pack(side='left')

        # Кнопка сохранения приёма
        ttk.Button(right_bottom, text="💾 Записать приём", command=self.save_meal).pack(pady=10)

    def load_lists(self):
        """Загружает списки продуктов и блюд."""
        prods = database.get_all_products()
        self.products_list = [(p['id'], p['name'], p) for p in prods]

        dishes = database.get_all_dishes()
        self.dishes_list = []
        for dish_id, dish_name in [(d['id'], d['name']) for d in dishes]:
            composition = database.get_dish_composition(dish_id)
            # Рассчитываем КБЖУ на 100 г
            nutrition = self._calculate_dish_nutrition_per_100(composition)
            self.dishes_list.append((dish_id, dish_name, composition, nutrition))

    def _calculate_dish_nutrition_per_100(self, composition):
        """Рассчитывает КБЖУ и ГН блюда на 100 г."""
        total_calories = 0
        total_proteins = 0
        total_fats = 0
        total_carbs = 0
        total_gn = 0
        total_weight = 0

        for item in composition:
            prod = database.get_product(item['product_id'])
            if prod:
                nut = calculate_product_nutrition(prod, item['weight'])
                total_calories += nut['calories']
                total_proteins += nut['proteins']
                total_fats += nut['fats']
                total_carbs += nut['carbs']
                total_gn += calculate_gn(nut['carbs'], prod['glycemic_index'])
                total_weight += item['weight']

        if total_weight > 0:
            factor_100 = 100 / total_weight
            return {
                'calories': total_calories * factor_100,
                'proteins': total_proteins * factor_100,
                'fats': total_fats * factor_100,
                'carbs': total_carbs * factor_100,
                'gn': total_gn * factor_100
            }
        return None

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
        dialog.geometry("400x500")

        ttk.Label(dialog, text="Выберите блюдо из списка:", font=('Arial', 10, 'bold')).pack(pady=5)

        # Список блюд
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)

        # Заполняем список (только названия)
        for _, name, _, _ in self.dishes_list:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if not sel:
                return
            dish_id, dish_name, composition, nutrition = self.dishes_list[sel[0]]

            # Добавляем в таблицу
            tag = 'dish'
            if nutrition:
                self.tree.insert('', 'end',
                                 values=(
                                     f"🍲 {dish_name}",
                                     f"{nutrition['calories']:.0f}",
                                     f"{nutrition['proteins']:.1f}",
                                     f"{nutrition['fats']:.1f}",
                                     f"{nutrition['carbs']:.1f}",
                                     f"{nutrition['gn']:.1f}",
                                     ""
                                 ),
                                 tags=(tag,)
                                 )

                # Сохраняем данные компонента
                self.components.append({
                    'type': 'dish',
                    'id': dish_id,
                    'name': dish_name,
                    'composition': composition,
                    'nutrition_per_100': nutrition,
                    'serving_weight': None,
                    'tree_id': self.tree.get_children()[-1]
                })

            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="Выбрать", command=select, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy, width=15).pack(side='left', padx=5)

    def add_product(self):
        """Добавление отдельного продукта."""
        if not self.products_list:
            messagebox.showwarning("Предупреждение", "Сначала создайте хотя бы один продукт")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Выберите продукт")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("400x500")

        ttk.Label(dialog, text="Выберите продукт из списка:", font=('Arial', 10, 'bold')).pack(pady=5)

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar.pack(side='right', fill='y')

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)

        # Заполняем список (только названия)
        for _, name, _ in self.products_list:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if not sel:
                return
            prod_id, prod_name, prod_data = self.products_list[sel[0]]

            # Добавляем в таблицу
            tag = 'product'
            self.tree.insert('', 'end',
                             values=(
                                 f"🍎 {prod_name}",
                                 f"{prod_data['calories']:.0f}",
                                 f"{prod_data['proteins']:.1f}",
                                 f"{prod_data['fats']:.1f}",
                                 f"{prod_data['carbs']:.1f}",
                                 f"{calculate_gn(prod_data['carbs'], prod_data['glycemic_index']):.1f}",
                                 ""
                             ),
                             tags=(tag,)
                             )

            # Сохраняем данные компонента
            self.components.append({
                'type': 'product',
                'id': prod_id,
                'name': prod_name,
                'product_data': prod_data,
                'serving_weight': None,
                'tree_id': self.tree.get_children()[-1]
            })

            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=10)
        ttk.Button(btn_frame, text="Выбрать", command=select, width=15).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy, width=15).pack(side='left', padx=5)

    def delete_component(self):
        """Удаление выбранного компонента."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите компонент для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный компонент?"):
            # Удаляем из списка компонентов
            tree_id = selected[0]
            for i, comp in enumerate(self.components):
                if comp.get('tree_id') == tree_id:
                    del self.components[i]
                    break

            # Удаляем из таблицы
            self.tree.delete(tree_id)

            # Пересчитываем итоги
            self.update_totals()
            self.update_insulin_dose()

    def on_item_double_click(self, event):
        """Обработчик двойного щелчка по строке таблицы."""
        selected = self.tree.selection()
        if not selected:
            return

        tree_id = selected[0]
        item = self.tree.item(tree_id)

        # Находим компонент
        comp = None
        for c in self.components:
            if c.get('tree_id') == tree_id:
                comp = c
                break

        if not comp:
            return

        # Диалог ввода веса
        current_weight = comp.get('serving_weight', '')
        weight = simpledialog.askfloat(
            "Вес порции",
            f"Введите вес порции для '{comp['name']}' (г):",
            initialvalue=current_weight if current_weight else 100,
            parent=self
        )

        if weight is not None and weight > 0:
            comp['serving_weight'] = weight

            # Обновляем отображение веса в таблице
            values = list(item['values'])
            values[6] = f"{weight:.0f}"  # вес порции
            self.tree.item(tree_id, values=values)

            # Пересчитываем итоги
            self.update_totals()
            self.update_insulin_dose()

    def update_totals(self):
        """Обновляет итоговые суммы по всем компонентам."""
        total_cal = total_prot = total_fat = total_carb = total_gn = 0.0

        for comp in self.components:
            if not comp.get('serving_weight'):
                continue

            weight = comp['serving_weight']

            if comp['type'] == 'product':
                nut = calculate_product_nutrition(comp['product_data'], weight)
                total_cal += nut['calories']
                total_prot += nut['proteins']
                total_fat += nut['fats']
                total_carb += nut['carbs']
                total_gn += calculate_gn(nut['carbs'], comp['product_data']['glycemic_index'])

            else:  # dish
                if comp.get('nutrition_per_100'):
                    n = comp['nutrition_per_100']
                    factor = weight / 100
                    total_cal += n['calories'] * factor
                    total_prot += n['proteins'] * factor
                    total_fat += n['fats'] * factor
                    total_carb += n['carbs'] * factor
                    total_gn += n['gn'] * factor

        total_xe = calculate_xe(total_carb, self.carbs_per_xe)

        self.total_vars['calories'].set(f"{total_cal:.1f}")
        self.total_vars['proteins'].set(f"{total_prot:.1f}")
        self.total_vars['fats'].set(f"{total_fat:.1f}")
        self.total_vars['carbs'].set(f"{total_carb:.1f}")
        self.total_vars['gn'].set(f"{total_gn:.1f}")
        self.total_vars['xe'].set(f"{total_xe:.2f}")

    def update_insulin_dose(self, *args):
        """Рассчитывает дозу инсулина."""
        try:
            # Доза на ХЕ
            xe = float(self.total_vars['xe'].get())
            carb_dose = xe * self.insulin_factors['carb_coefficient']

            # Коррекция по сахару
            current_glucose = float(self.current_glucose_var.get() or 0)
            if current_glucose > 0:
                target = self.insulin_factors['target_glucose']
                sensitivity = self.insulin_factors['sensitivity']
                correction_dose = (current_glucose - target) / sensitivity
                if correction_dose < 0:
                    correction_dose = 0
            else:
                correction_dose = 0

            total_dose = carb_dose + correction_dose
            self.insulin_dose_var.set(f"{total_dose:.1f}")

        except (ValueError, ZeroDivisionError):
            self.insulin_dose_var.set("0.0")

    def save_meal(self):
        """Сохраняет текущий приём пищи в историю."""
        if not self.components:
            messagebox.showwarning("Предупреждение", "Нет компонентов для сохранения")
            return

        # Проверяем, что у всех компонентов указан вес
        for comp in self.components:
            if not comp.get('serving_weight'):
                messagebox.showerror("Ошибка", f"У компонента '{comp['name']}' не указан вес порции")
                return

        # Диалог ввода даты/времени, дозы, примечания
        dialog = tk.Toplevel(self)
        dialog.title("Сохранение приёма")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("350x450")

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Дата и время
        ttk.Label(dialog, text="Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ):").pack(pady=5)
        datetime_var = tk.StringVar(value=now)
        ttk.Entry(dialog, textvariable=datetime_var, width=20).pack()

        # Текущий сахар
        ttk.Label(dialog, text="Уровень сахара (ммоль/л):").pack(pady=5)
        glucose_var = tk.StringVar(value=self.current_glucose_var.get())
        ttk.Entry(dialog, textvariable=glucose_var, width=10).pack()

        # Доза инсулина
        ttk.Label(dialog, text="Доза инсулина (ед):").pack(pady=5)
        insulin_var = tk.StringVar(value=self.insulin_dose_var.get())
        ttk.Entry(dialog, textvariable=insulin_var, width=10).pack()

        # Примечание
        ttk.Label(dialog, text="Примечание:").pack(pady=5)
        notes_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=notes_var, width=30).pack()

        def do_save():
            dt = datetime_var.get().strip()
            glucose = glucose_var.get().strip()
            insulin = insulin_var.get().strip()
            notes = notes_var.get().strip() or None

            # Формируем список компонентов для сохранения
            components_for_db = []
            for comp in self.components:
                if comp['type'] == 'product':
                    components_for_db.append({
                        'type': 'product',
                        'id': comp['id'],
                        'name': comp['name'],
                        'serving_weight': comp['serving_weight']
                    })
                else:  # dish
                    # Для блюда восстанавливаем состав продуктов
                    composition_portion = []
                    if comp.get('composition'):
                        total_weight = sum(item['weight'] for item in comp['composition'])
                        if total_weight > 0:
                            factor = comp['serving_weight'] / total_weight
                            for item in comp['composition']:
                                composition_portion.append({
                                    'product_id': item['product_id'],
                                    'weight': item['weight'] * factor
                                })

                    components_for_db.append({
                        'type': 'dish',
                        'id': comp['id'],
                        'name': comp['name'],
                        'serving_weight': comp['serving_weight'],
                        'composition': composition_portion
                    })

            try:
                database.save_meal(
                    dt,
                    float(insulin) if insulin else None,
                    notes,
                    components_for_db,
                    float(glucose) if glucose else None
                )
                messagebox.showinfo("Успех", "Приём пищи сохранён")
                dialog.destroy()

                if messagebox.askyesno("Очистить", "Очистить текущий приём?"):
                    # Очищаем таблицу и список компонентов
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    self.components.clear()
                    self.total_vars['calories'].set("0.0")
                    self.total_vars['proteins'].set("0.0")
                    self.total_vars['fats'].set("0.0")
                    self.total_vars['carbs'].set("0.0")
                    self.total_vars['gn'].set("0.0")
                    self.total_vars['xe'].set("0.0")
                    self.insulin_dose_var.set("0.0")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

        ttk.Button(dialog, text="Сохранить", command=do_save).pack(pady=10)
        ttk.Button(dialog, text="Отмена", command=dialog.destroy).pack()