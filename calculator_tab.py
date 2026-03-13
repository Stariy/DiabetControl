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
        self.insulin_step = 0.5  # NEW: шаг дозирования инсулина (по умолчанию 0.5)

        # Коэффициенты для расчёта инсулина (будут загружены из БД)
        self.insulin_factors = {
            'carb_coefficient': 1.0,  # ед инсулина на 1 ХЕ
            'target_glucose': 6.0,  # целевой уровень сахара ммоль/л
            'sensitivity': 2.0  # на сколько ммоль/л снижает 1 ед инсулина
        }
        self.insulin_food_var = tk.StringVar(value="0.0")
        self.insulin_corr_var = tk.StringVar(value="0.0")
        self.insulin_dose_var = tk.StringVar(value="0.0")

        # NEW: переменные для отображения ближайших доз и выбора целевой
        self.insulin_lower_var = tk.StringVar(value="0.0")
        self.insulin_upper_var = tk.StringVar(value="0.0")
        self.target_dose_var = tk.StringVar(value="lower")

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
            self.carbs_per_xe = settings.get('carbs_per_xe', DEFAULT_CARBS_PER_XE)
            self.insulin_step = settings.get('insulin_step', 0.5)  # NEW

            # Обновляем поля ввода
            self.carb_coef_var.set(str(self.insulin_factors['carb_coefficient']))
            self.target_glucose_var.set(str(self.insulin_factors['target_glucose']))
            self.sensitivity_var.set(str(self.insulin_factors['sensitivity']))
            self.carbs_per_xe_var.set(str(self.carbs_per_xe))
            self.insulin_step_var.set(str(self.insulin_step))  # NEW

    def save_insulin_settings(self):
        """Сохраняет настройки инсулина в базу данных."""
        try:
            carb_coef = float(self.carb_coef_var.get())
            target_glucose = float(self.target_glucose_var.get())
            sensitivity = float(self.sensitivity_var.get())

            # Загружаем текущие настройки, чтобы не потерять carbs_per_xe и insulin_step
            settings = database.get_settings() or {}
            settings.update({
                'carb_coefficient': carb_coef,
                'target_glucose': target_glucose,
                'sensitivity': sensitivity
            })
            database.save_settings(settings)

            self.insulin_factors['carb_coefficient'] = carb_coef
            self.insulin_factors['target_glucose'] = target_glucose
            self.insulin_factors['sensitivity'] = sensitivity

            # Пересчитываем дозу инсулина
            self.update_insulin_dose()
            messagebox.showinfo("Успех", "Настройки инсулина сохранены")

        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность ввода коэффициентов")

    def save_xe_coefficient(self):
        """Сохраняет коэффициент пересчёта ХЕ в базу данных."""
        try:
            val = float(self.carbs_per_xe_var.get())
            if val <= 0:
                messagebox.showerror("Ошибка", "Значение должно быть положительным")
                self.carbs_per_xe_var.set(str(self.carbs_per_xe))
                return

            # Загружаем текущие настройки, чтобы не потерять остальные
            settings = database.get_settings() or {}
            settings['carbs_per_xe'] = val
            database.save_settings(settings)

            self.carbs_per_xe = val

            # Пересчитываем итоги (ХЕ изменится)
            self.update_totals()
            self.update_insulin_dose()
            messagebox.showinfo("Успех", "Коэффициент ХЕ сохранён")

        except ValueError:
            messagebox.showerror("Ошибка", "Введите число")
            self.carbs_per_xe_var.set(str(self.carbs_per_xe))

    # NEW: сохранение шага дозирования
    def save_insulin_step(self):
        try:
            val = float(self.insulin_step_var.get())
            if val <= 0:
                messagebox.showerror("Ошибка", "Шаг должен быть положительным числом")
                self.insulin_step_var.set(str(self.insulin_step))
                return
            settings = database.get_settings() or {}
            settings['insulin_step'] = val
            database.save_settings(settings)
            self.insulin_step = val
            self.update_insulin_dose()  # обновим отображение вариантов
            messagebox.showinfo("Успех", "Шаг дозирования сохранён")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите число")
            self.insulin_step_var.set(str(self.insulin_step))

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
        columns = ('adjust', 'name', 'calories', 'proteins', 'fats', 'carbs', 'gn', 'weight')  # NEW: добавили adjust
        self.tree = ttk.Treeview(top_frame, columns=columns, show='headings', height=10)

        # Настройка заголовков
        self.tree.heading('adjust', text='Корр.')
        self.tree.heading('name', text='Название')
        self.tree.heading('calories', text='Ккал/100г')
        self.tree.heading('proteins', text='Б/100г')
        self.tree.heading('fats', text='Ж/100г')
        self.tree.heading('carbs', text='У/100г')
        self.tree.heading('gn', text='ГН/100г')
        self.tree.heading('weight', text='Вес порции (г)')

        # Настройка ширины колонок
        self.tree.column('adjust', width=50, anchor='center')
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
        # NEW: привязываем клик для чекбоксов
        self.tree.bind('<Button-1>', self.on_tree_click)

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

        # Правая часть нижней панели - расчёт инсулина и настройки
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
        ttk.Button(coef_frame, text="✓", command=self.save_insulin_settings, width=3).grid(row=0, column=2)

        # Целевой сахар
        ttk.Label(coef_frame, text="Цель ммоль/л:").grid(row=1, column=0, sticky='w', pady=2)
        self.target_glucose_var = tk.StringVar(value=str(self.insulin_factors['target_glucose']))
        ttk.Entry(coef_frame, textvariable=self.target_glucose_var, width=8).grid(row=1, column=1, padx=5)

        # Чувствительность
        ttk.Label(coef_frame, text="1 ед снижает на:").grid(row=2, column=0, sticky='w', pady=2)
        self.sensitivity_var = tk.StringVar(value=str(self.insulin_factors['sensitivity']))
        ttk.Entry(coef_frame, textvariable=self.sensitivity_var, width=8).grid(row=2, column=1, padx=5)

        # --- NEW: шаг дозирования ---
        ttk.Label(coef_frame, text="Шаг ручки (ед):").grid(row=5, column=0, sticky='w', pady=2)
        self.insulin_step_var = tk.StringVar(value=str(self.insulin_step))
        ttk.Entry(coef_frame, textvariable=self.insulin_step_var, width=8).grid(row=5, column=1, padx=5)
        ttk.Button(coef_frame, text="✓", command=self.save_insulin_step, width=3).grid(row=5, column=2)

        # --- Коэффициент ХЕ ---
        ttk.Label(coef_frame, text="1 ХЕ = г углеводов:").grid(row=3, column=0, sticky='w', pady=2)
        self.carbs_per_xe_var = tk.StringVar(value=str(self.carbs_per_xe))
        ttk.Entry(coef_frame, textvariable=self.carbs_per_xe_var, width=8).grid(row=3, column=1, padx=5)
        ttk.Button(coef_frame, text="✓", command=self.save_xe_coefficient, width=3).grid(row=3, column=2)

        # Текущий сахар
        ttk.Label(coef_frame, text="Текущий сахар:").grid(row=4, column=0, sticky='w', pady=(10, 2))
        self.current_glucose_var = tk.StringVar()
        ttk.Entry(coef_frame, textvariable=self.current_glucose_var, width=8).grid(row=4, column=1, padx=5)
        self.current_glucose_var.trace('w', lambda *args: self.update_insulin_dose())

        # Результат
        result_frame = ttk.Frame(right_bottom)
        result_frame.pack(fill='x', pady=5)

        # Доза на еду
        food_frame = ttk.Frame(right_bottom)
        food_frame.pack(fill='x')
        ttk.Label(food_frame, text="На еду:", width=15).pack(side='left')
        self.insulin_food_var = tk.StringVar(value="0.0")
        ttk.Label(food_frame, textvariable=self.insulin_food_var, width=8, anchor='e').pack(side='left')
        ttk.Label(food_frame, text="ед").pack(side='left')

        # Коррекция
        corr_frame = ttk.Frame(right_bottom)
        corr_frame.pack(fill='x', pady=2)
        ttk.Label(corr_frame, text="Коррекция:", width=15).pack(side='left')
        self.insulin_corr_var = tk.StringVar(value="0.0")
        ttk.Label(corr_frame, textvariable=self.insulin_corr_var, width=8, anchor='e').pack(side='left')
        ttk.Label(corr_frame, text="ед").pack(side='left')

        # Общая доза (жирным)
        total_frame_label = ttk.Frame(right_bottom)
        total_frame_label.pack(fill='x', pady=(5, 10))
        ttk.Label(total_frame_label, text="ИТОГО:", font=('Arial', 10, 'bold')).pack(side='left')
        ttk.Label(total_frame_label, textvariable=self.insulin_dose_var, font=('Arial', 12, 'bold'),
                  foreground='blue').pack(side='left', padx=5)
        ttk.Label(total_frame_label, text="ед").pack(side='left')

        # --- NEW: панель коррекции дозы ---
        adjust_frame = ttk.LabelFrame(right_bottom, text="Коррекция дозы", padding=5)
        adjust_frame.pack(fill='x', pady=5)

        # Радиокнопки выбора целевой дозы
        ttk.Radiobutton(adjust_frame, text="Меньше: ", variable=self.target_dose_var, value="lower").pack(anchor='w')
        ttk.Label(adjust_frame, textvariable=self.insulin_lower_var).pack(anchor='w', padx=(20,0))

        ttk.Radiobutton(adjust_frame, text="Больше: ", variable=self.target_dose_var, value="upper").pack(anchor='w')
        ttk.Label(adjust_frame, textvariable=self.insulin_upper_var).pack(anchor='w', padx=(20,0))

        # Кнопка выполнения коррекции
        ttk.Button(adjust_frame, text="Скорректировать еду", command=self.adjust_meal).pack(pady=5)

        # Кнопка сохранения приёма
        ttk.Button(right_bottom, text="💾 Записать приём", command=self.save_meal).pack(pady=5)

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
                tree_id = self.tree.insert('', 'end',
                                 values=(
                                     '☑',  # NEW: по умолчанию отмечено
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
                    'tree_id': tree_id,
                    'adjustable': True  # NEW
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
            tree_id = self.tree.insert('', 'end',
                             values=(
                                 '☑',  # NEW: по умолчанию отмечено
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
                'tree_id': tree_id,
                'adjustable': True  # NEW
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

            # Обновляем отображение веса в таблице (сохраняя чекбокс)
            values = list(item['values'])
            values[7] = f"{weight:.0f}"  # вес порции теперь на позиции 7
            self.tree.item(tree_id, values=values)

            # Пересчитываем итоги
            self.update_totals()
            self.update_insulin_dose()

    # NEW: обработчик клика для переключения чекбокса
    def on_tree_click(self, event):
        """Обработчик клика для переключения чекбокса в колонке adjust."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        if column != '#1':  # колонка adjust первая
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Получаем текущее значение
        values = list(self.tree.item(item, 'values'))
        current = values[0]
        # Переключаем символ
        new_val = '☐' if current == '☑' else '☑'
        values[0] = new_val
        self.tree.item(item, values=values)

        # Обновляем состояние adjustable в компоненте
        for comp in self.components:
            if comp.get('tree_id') == item:
                comp['adjustable'] = (new_val == '☑')
                break

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
        """Рассчитывает дозу инсулина (пищевую и коррекцию) и определяет ближайшие допустимые значения."""
        try:
            # Пищевая доза (на ХЕ)
            xe = float(self.total_vars['xe'].get())
            food_dose = xe * self.insulin_factors['carb_coefficient']
            self.insulin_food_var.set(f"{food_dose:.1f}")

            # Коррекция по сахару
            current_glucose = float(self.current_glucose_var.get() or 0)
            if current_glucose > 0:
                target = self.insulin_factors['target_glucose']
                sensitivity = self.insulin_factors['sensitivity']
                correction = (current_glucose - target) / sensitivity
                if correction < 0:
                    correction = 0
            else:
                correction = 0
            self.insulin_corr_var.set(f"{correction:.1f}")

            # Общая доза
            total_dose = food_dose + correction
            self.insulin_dose_var.set(f"{total_dose:.1f}")

            # NEW: расчёт ближайших допустимых значений с учётом шага
            step = self.insulin_step
            # Округление вниз до ближайшего кратного шагу
            lower = round((total_dose // step) * step, 1)
            if lower < 0: lower = 0
            upper = lower + step
            # Убираем дублирование, если total_dose точно кратно шагу
            if abs(total_dose - lower) < 0.01:
                lower_display = lower
                upper_display = lower + step
            else:
                lower_display = lower
                upper_display = upper

            self.insulin_lower_var.set(f"{lower_display:.1f}")
            self.insulin_upper_var.set(f"{upper_display:.1f}")

        except (ValueError, ZeroDivisionError):
            self.insulin_food_var.set("0.0")
            self.insulin_corr_var.set("0.0")
            self.insulin_dose_var.set("0.0")
            self.insulin_lower_var.set("0.0")
            self.insulin_upper_var.set("0.0")

    # NEW: метод корректировки еды
    def adjust_meal(self):
        """Корректирует веса отмеченных продуктов для достижения выбранной целевой дозы."""
        # Проверяем, что все компоненты имеют вес
        for comp in self.components:
            if not comp.get('serving_weight'):
                messagebox.showerror("Ошибка", f"У компонента '{comp['name']}' не указан вес порции")
                return

        # Получаем целевую дозу
        target = self.target_dose_var.get()
        if target == 'lower':
            target_dose = float(self.insulin_lower_var.get())
        else:
            target_dose = float(self.insulin_upper_var.get())

        # Получаем текущую общую дозу
        total_dose = float(self.insulin_dose_var.get())
        if abs(total_dose - target_dose) < 0.01:
            messagebox.showinfo("Инфо", "Текущая доза уже равна целевой")
            return

        # Вычисляем текущие суммарные углеводы
        total_carbs = 0
        for comp in self.components:
            if comp['type'] == 'product':
                carbs = (comp['product_data']['carbs'] * comp['serving_weight']) / 100
                total_carbs += carbs
            else:  # dish
                if comp.get('nutrition_per_100'):
                    carbs = (comp['nutrition_per_100']['carbs'] * comp['serving_weight']) / 100
                    total_carbs += carbs

        # Целевые углеводы из целевой дозы (учитывая коррекцию)
        correction = float(self.insulin_corr_var.get())
        target_carbs = (target_dose - correction) * self.carbs_per_xe / self.insulin_factors['carb_coefficient']
        if target_carbs < 0:
            messagebox.showerror("Ошибка", "Целевая доза слишком мала (отрицательные углеводы)")
            return

        delta_carbs = target_carbs - total_carbs

        # Собираем отмеченные продукты, которые можно корректировать (только продукты, не блюда)
        adjustable_products = []
        for comp in self.components:
            if comp['type'] == 'product' and comp.get('adjustable', False):
                # Вычисляем текущие углеводы продукта
                carbs = (comp['product_data']['carbs'] * comp['serving_weight']) / 100
                adjustable_products.append({
                    'comp': comp,
                    'current_carbs': carbs,
                    'carbs_per_100': comp['product_data']['carbs']
                })

        if not adjustable_products:
            messagebox.showwarning("Предупреждение", "Не отмечено ни одного продукта для корректировки")
            return

        # Распределяем изменение углеводов пропорционально текущему вкладу
        total_adjustable_carbs = sum(p['current_carbs'] for p in adjustable_products)
        if total_adjustable_carbs == 0:
            messagebox.showerror("Ошибка", "Сумма углеводов в отмеченных продуктах равна 0")
            return

        # Изменяем веса продуктов
        for prod in adjustable_products:
            # Доля изменения, приходящаяся на этот продукт
            share = prod['current_carbs'] / total_adjustable_carbs
            prod_delta_carbs = delta_carbs * share
            new_carbs = prod['current_carbs'] + prod_delta_carbs
            if new_carbs < 0:
                new_carbs = 0
            # Новый вес
            new_weight = (new_carbs * 100) / prod['carbs_per_100']
            if new_weight < 0:
                new_weight = 0
            prod['comp']['serving_weight'] = new_weight

            # Обновляем в таблице
            tree_id = prod['comp']['tree_id']
            self.tree.item(tree_id, values=(
                '☑' if prod['comp']['adjustable'] else '☐',
                f"🍎 {prod['comp']['name']}",
                f"{prod['comp']['product_data']['calories']:.0f}",
                f"{prod['comp']['product_data']['proteins']:.1f}",
                f"{prod['comp']['product_data']['fats']:.1f}",
                f"{prod['comp']['product_data']['carbs']:.1f}",
                f"{calculate_gn(prod['comp']['product_data']['carbs'], prod['comp']['product_data']['glycemic_index']):.1f}",
                f"{new_weight:.0f}"
            ))

        # Пересчитываем итоги
        self.update_totals()
        self.update_insulin_dose()
        messagebox.showinfo("Успех", f"Веса скорректированы для достижения дозы {target_dose:.1f} ед")

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