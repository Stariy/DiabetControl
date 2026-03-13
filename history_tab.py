import tkinter as tk
from tkinter import ttk, messagebox
import database

from utils import calculate_gn
class HistoryTab(ttk.Frame):
    def __init__(self, parent, calculator_tab=None):
        super().__init__(parent)
        self.calculator_tab = calculator_tab  # ссылка на калькулятор для копирования
        self.create_widgets()
        self.refresh_list()
        # Привязываем событие появления вкладки
        self.bind('<Map>', self.on_tab_show)

    def on_tab_show(self, event):
        """Обновляет список при активации вкладки."""
        self.refresh_list()
    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Обновить", command=self.refresh_list).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Просмотреть", command=self.view_meal).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Копировать в калькулятор", command=self.copy_to_calculator).pack(side='left',
                                                                                                     padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_meal).pack(side='left', padx=2)

        # Таблица с историей
        columns = ('id', 'datetime', 'glucose', 'insulin', 'notes')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='ID')
        self.tree.heading('datetime', text='Дата и время')
        self.tree.heading('glucose', text='Сахар (ммоль/л)')
        self.tree.heading('insulin', text='Инсулин (ед)')
        self.tree.heading('notes', text='Примечание')

        self.tree.column('id', width=40)
        self.tree.column('datetime', width=150)
        self.tree.column('glucose', width=80)
        self.tree.column('insulin', width=80)
        self.tree.column('notes', width=200)

        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0, 5), pady=5)

        self.tree.bind('<Double-1>', lambda e: self.view_meal())

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        meals = database.get_all_meals()
        for m in meals:
            dt = m['datetime']
            glucose = f"{m['glucose']:.1f}" if m['glucose'] is not None else ''
            insulin = f"{m['insulin_dose']:.1f}" if m['insulin_dose'] is not None else ''
            notes = m['notes'] if m['notes'] else ''
            self.tree.insert('', 'end', values=(m['id'], dt, glucose, insulin, notes))

    def get_selected_meal_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите запись в истории")
            return None
        item = self.tree.item(sel[0])
        return item['values'][0]

    def view_meal(self):
        meal_id = self.get_selected_meal_id()
        if not meal_id:
            return
        # Получаем данные
        meal = database.get_meal(meal_id)
        components = database.get_meal_components(meal_id)
        self.show_meal_details(meal, components)

    def show_meal_details(self, meal, components):
        """Отображает окно с деталями приёма."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Приём от {meal['datetime']}")
        dialog.geometry("700x500")
        dialog.transient(self)
        dialog.grab_set()

        # Основная информация
        info_frame = ttk.LabelFrame(dialog, text="Основное", padding=5)
        info_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(info_frame, text=f"Дата и время: {meal['datetime']}").pack(anchor='w')

        # Проверяем наличие glucose через обращение по ключу (для sqlite3.Row)
        if 'glucose' in meal.keys() and meal['glucose'] is not None:
            ttk.Label(info_frame, text=f"Сахар: {meal['glucose']:.1f} ммоль/л").pack(anchor='w')

        if meal['insulin_dose'] is not None:
            ttk.Label(info_frame, text=f"Доза инсулина: {meal['insulin_dose']:.1f} ед").pack(anchor='w')

        if meal['notes']:
            ttk.Label(info_frame, text=f"Примечание: {meal['notes']}").pack(anchor='w')

        # Состав
        comp_frame = ttk.LabelFrame(dialog, text="Состав", padding=5)
        comp_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Создаём дерево для отображения состава
        columns = ('type', 'name', 'weight', 'details')
        tree = ttk.Treeview(comp_frame, columns=columns, show='tree headings', height=15)
        tree.heading('type', text='Тип')
        tree.heading('name', text='Название')
        tree.heading('weight', text='Вес порции (г)')
        tree.heading('details', text='Детали')

        tree.column('type', width=60)
        tree.column('name', width=200)
        tree.column('weight', width=80)
        tree.column('details', width=300)

        scrollbar = ttk.Scrollbar(comp_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Заполняем
        for comp in components:
            if comp['component_type'] == 'product':
                tree.insert('', 'end', values=(
                    'Продукт',
                    comp.get('product_name', '?'),
                    f"{comp['serving_weight']:.1f}",
                    ''
                ))
            else:  # dish
                # Формируем детали для блюда
                details = []
                if comp.get('cooked_dish_weight'):
                    details.append(f"вес готового: {comp['cooked_dish_weight']:.1f} г")
                if comp.get('pan_id'):
                    pan_name = self._get_pan_name(comp['pan_id'])
                    if pan_name:
                        details.append(f"кастрюля: {pan_name}")

                details_str = ", ".join(details) if details else ""

                dish_item = tree.insert('', 'end', values=(
                    'Блюдо',
                    comp.get('dish_name', '?'),
                    f"{comp['serving_weight']:.1f}",
                    details_str
                ))

                # Добавляем продукты блюда как дочерние
                for det in comp.get('details', []):
                    tree.insert(dish_item, 'end', values=(
                        '  └ Продукт',
                        det.get('product_name', '?'),
                        f"{det['weight']:.1f}",
                        ''
                    ))

        # Кнопка закрытия
        ttk.Button(dialog, text="Закрыть", command=dialog.destroy).pack(pady=5)
    def _get_pan_name(self, pan_id):
        """Получает название кастрюли по ID."""
        if not pan_id:
            return None
        pan = database.get_pan(pan_id)
        return pan['name'] if pan else None

    def copy_to_calculator(self):
        """Копирует выбранный приём в калькулятор (загружает компоненты)."""
        if not self.calculator_tab:
            messagebox.showerror("Ошибка", "Калькулятор не доступен")
            return
        meal_id = self.get_selected_meal_id()
        if not meal_id:
            return
        # Получаем детальный состав приёма
        components = database.get_meal_components(meal_id)
        if not components:
            messagebox.showwarning("Предупреждение", "Приём не содержит компонентов")
            return

        # Очищаем текущие компоненты в калькуляторе
        self.calculator_tab.components.clear()
        for item in self.calculator_tab.tree.get_children():
            self.calculator_tab.tree.delete(item)

        # Преобразуем в формат калькулятора
        for comp in components:
            if comp['component_type'] == 'product':
                prod = database.get_product(comp['product_id'])
                if not prod:
                    continue

                # Добавляем в таблицу калькулятора
                tag = 'product'
                tree_id = self.calculator_tab.tree.insert('', 'end',
                                                          values=(
                                                              f"🍎 {prod['name']}",
                                                              f"{prod['calories']:.0f}",
                                                              f"{prod['proteins']:.1f}",
                                                              f"{prod['fats']:.1f}",
                                                              f"{prod['carbs']:.1f}",
                                                              f"{calculate_gn(prod['carbs'], prod['glycemic_index']):.1f}",
                                                              f"{comp['serving_weight']:.0f}"
                                                          ),
                                                          tags=(tag,)
                                                          )

                self.calculator_tab.components.append({
                    'type': 'product',
                    'id': prod['id'],
                    'name': prod['name'],
                    'product_data': prod,
                    'serving_weight': comp['serving_weight'],
                    'tree_id': tree_id
                })

            else:  # dish
                dish = database.get_dish(comp['dish_id'])
                if not dish:
                    continue

                # Получаем состав блюда для расчёта КБЖУ на 100 г
                composition = database.get_dish_composition(comp['dish_id'])
                nutrition = self.calculator_tab._calculate_dish_nutrition_per_100(composition)

                if nutrition:
                    # Добавляем в таблицу калькулятора
                    tag = 'dish'
                    tree_id = self.calculator_tab.tree.insert('', 'end',
                                                              values=(
                                                                  f"🍲 {dish['name']}",
                                                                  f"{nutrition['calories']:.0f}",
                                                                  f"{nutrition['proteins']:.1f}",
                                                                  f"{nutrition['fats']:.1f}",
                                                                  f"{nutrition['carbs']:.1f}",
                                                                  f"{nutrition['gn']:.1f}",
                                                                  f"{comp['serving_weight']:.0f}"
                                                              ),
                                                              tags=(tag,)
                                                              )

                    self.calculator_tab.components.append({
                        'type': 'dish',
                        'id': dish['id'],
                        'name': dish['name'],
                        'composition': composition,
                        'nutrition_per_100': nutrition,
                        'serving_weight': comp['serving_weight'],
                        'tree_id': tree_id
                    })

        # Пересчитываем итоги в калькуляторе
        self.calculator_tab.update_totals()
        self.calculator_tab.update_insulin_dose()

        # Переключаемся на вкладку калькулятора
        self.master.select(self.calculator_tab)

        messagebox.showinfo("Успех", "Приём скопирован в калькулятор")

    def delete_meal(self):
        meal_id = self.get_selected_meal_id()
        if not meal_id:
            return
        if messagebox.askyesno("Подтверждение", "Удалить запись о приёме?"):
            database.delete_meal(meal_id)
            self.refresh_list()