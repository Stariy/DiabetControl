import tkinter as tk
from tkinter import ttk, messagebox
import database

class HistoryTab(ttk.Frame):
    def __init__(self, parent, calculator_tab=None):
        super().__init__(parent)
        self.calculator_tab = calculator_tab  # ссылка на калькулятор для копирования
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Обновить", command=self.refresh_list).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Просмотреть", command=self.view_meal).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Копировать в калькулятор", command=self.copy_to_calculator).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_meal).pack(side='left', padx=2)

        # Таблица с историей
        columns = ('id', 'datetime', 'insulin', 'notes')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='ID')
        self.tree.heading('datetime', text='Дата и время')
        self.tree.heading('insulin', text='Инсулин (ед)')
        self.tree.heading('notes', text='Примечание')

        self.tree.column('id', width=40)
        self.tree.column('datetime', width=150)
        self.tree.column('insulin', width=80)
        self.tree.column('notes', width=200)

        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True, padx=(5,0), pady=5)
        scrollbar.pack(side='right', fill='y', padx=(0,5), pady=5)

        self.tree.bind('<Double-1>', lambda e: self.view_meal())

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        meals = database.get_all_meals()
        for m in meals:
            dt = m['datetime']
            insulin = f"{m['insulin_dose']:.1f}" if m['insulin_dose'] is not None else ''
            notes = m['notes'] if m['notes'] else ''
            self.tree.insert('', 'end', values=(m['id'], dt, insulin, notes))

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
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()

        # Основная информация
        info_frame = ttk.LabelFrame(dialog, text="Основное", padding=5)
        info_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(info_frame, text=f"Дата и время: {meal['datetime']}").pack(anchor='w')
        if meal['insulin_dose']:
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
        tree.column('name', width=150)
        tree.column('weight', width=80)
        tree.column('details', width=250)

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
                dish_item = tree.insert('', 'end', values=(
                    'Блюдо',
                    comp.get('dish_name', '?'),
                    f"{comp['serving_weight']:.1f}",
                    f"вес готового: {comp['cooked_dish_weight']:.1f} г"
                ))
                # Добавляем продукты блюда как дочерние
                for det in comp['details']:
                    tree.insert(dish_item, 'end', values=(
                        '  └ Продукт',
                        det.get('product_name', '?'),
                        f"{det['weight']:.1f}",
                        ''
                    ))

        # Кнопка закрытия
        ttk.Button(dialog, text="Закрыть", command=dialog.destroy).pack(pady=5)

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

        # Преобразуем в формат калькулятора, разворачивая блюда в отдельные продукты
        calc_components = []
        for comp in components:
            if comp['component_type'] == 'product':
                prod = database.get_product(comp['product_id'])
                if not prod:
                    continue
                calc_components.append({
                    'type': 'product',
                    'id': comp['product_id'],
                    'name': prod['name'],
                    'serving_weight': comp['serving_weight'],
                    'product_data': prod
                })
            else:  # dish
                # Разворачиваем блюдо в отдельные продукты
                for det in comp['details']:
                    prod = database.get_product(det['product_id'])
                    if not prod:
                        continue
                    calc_components.append({
                        'type': 'product',
                        'id': det['product_id'],
                        'name': prod['name'],
                        'serving_weight': det['weight'],  # вес в порции
                        'product_data': prod
                    })

        if not calc_components:
            messagebox.showwarning("Предупреждение", "Не удалось скопировать компоненты")
            return

        # Очищаем текущие компоненты в калькуляторе и загружаем новые
        if messagebox.askyesno("Подтверждение", "Заменить текущий состав в калькуляторе?"):
            self.calculator_tab.components = calc_components
            self.calculator_tab.current_component_index = None
            self.calculator_tab.update_components_list()
            self.calculator_tab.clear_details()
            self.calculator_tab.update_totals()
            # Переключаемся на вкладку калькулятора
            self.master.select(self.calculator_tab)

    def delete_meal(self):
        meal_id = self.get_selected_meal_id()
        if not meal_id:
            return
        if messagebox.askyesno("Подтверждение", "Удалить запись о приёме?"):
            database.delete_meal(meal_id)
            self.refresh_list()