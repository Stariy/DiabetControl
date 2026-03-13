import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import database
import os
from PIL import Image, ImageTk
from config import BASE_DIR


class DishesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.current_dish_id = None
        self.pans_list = []  # список кортежей (id, name, weight, photo_path)
        self.products_list = []  # список кортежей (id, name)

        # Получаем стандартную высоту строки для Listbox
        self.listbox_rowheight = self._get_listbox_rowheight()

        self.create_widgets()

        # Привязываем событие появления вкладки
        self.bind('<Map>', self.on_tab_show)

        # Загружаем данные при создании
        self.load_pans()
        self.load_products()
        self.refresh_dishes_list()

    def on_tab_show(self, event):
        """Вызывается при активации вкладки."""
        # Перезагружаем списки кастрюль и продуктов
        self.load_pans()
        self.load_products()
        # Обновляем состав текущего блюда, если оно выбрано
        if self.current_dish_id is not None:
            self.load_dish_details()
        # Обновляем список блюд (на случай, если они изменились в другой вкладке)
        self.refresh_dishes_list()

    def _get_listbox_rowheight(self):
        """Определяет оптимальную высоту строки для Listbox на основе текущего шрифта."""
        temp_listbox = tk.Listbox(self)
        temp_listbox.insert(tk.END, "Тест")
        # Получаем высоту строки в пикселях
        rowheight = temp_listbox.bbox(0 )
        temp_listbox.destroy()
        if rowheight:
            return rowheight[3] + 2  # добавляем небольшой отступ
        return 20  # значение по умолчанию, если не удалось определить

    def _configure_listbox_height(self, listbox):
        """Настраивает высоту строк Listbox для правильного отображения текста."""
        # Устанавливаем явный шрифт
        try:
            listbox.config(font=('Arial', 14))
        except:
            pass

    def _create_colored_listbox(self, parent, bg_light="#f0f0f0", bg_dark="#ffffff"):
        """
        Создает Listbox с чередованием фона через каждые две строки.
        Возвращает созданный Listbox.
        """
        listbox = tk.Listbox(parent, bg=bg_light, selectbackground='#0078d7',
                             selectforeground='white', relief='solid', borderwidth=1)

        # Переопределяем метод insert для автоматической раскраски
        original_insert = listbox.insert

        def colored_insert(index, *args, **kwargs):
            result = original_insert(index, *args, **kwargs)
            # Перекрашиваем все строки
            for i in range(listbox.size()):
                # Каждые две строки - один фон
                if (i // 2) % 2 == 0:
                    listbox.itemconfig(i, bg=bg_light)
                else:
                    listbox.itemconfig(i, bg=bg_dark)
            return result

        listbox.insert = colored_insert

        # Переопределяем метод delete для обновления цветов после удаления
        original_delete = listbox.delete

        def colored_delete(first, last=None):
            result = original_delete(first, last)
            # Перекрашиваем оставшиеся строки
            for i in range(listbox.size()):
                if (i // 2) % 2 == 0:
                    listbox.itemconfig(i, bg=bg_light)
                else:
                    listbox.itemconfig(i, bg=bg_dark)
            return result

        listbox.delete = colored_delete

        return listbox

    def create_widgets(self):
        # Левая панель со списком блюд
        left_frame = ttk.Frame(self, width=300, relief='sunken', padding=5)
        left_frame.pack(side='left', fill='y', padx=(5, 0), pady=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Блюда", font=('Arial', 14, 'bold')).pack(anchor='w')

        # Создаем Listbox с чередованием фона
        self.dishes_listbox = self._create_colored_listbox(left_frame, bg_light="#f5f5f5", bg_dark="#ffffff")
        self.dishes_listbox.pack(fill='both', expand=True, pady=5)
        self.dishes_listbox.bind('<<ListboxSelect>>', self.on_dish_select)
        # Настраиваем высоту строк
        self._configure_listbox_height(self.dishes_listbox)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Новое", command=self.new_dish).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_dish).pack(side='left', padx=2)

        # Правая панель (детали блюда)
        right_frame = ttk.Frame(self, padding=5)
        right_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Верхняя панель с названием и фото
        top_frame = ttk.Frame(right_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 5))

        # Левая часть верхней панели (поля ввода)
        fields_frame = ttk.Frame(top_frame)
        fields_frame.pack(side='left', fill='x', expand=True)

        # Правая часть верхней панели (фото)
        photo_frame = ttk.Frame(top_frame, width=200, height=200)
        photo_frame.pack(side='right', padx=(10, 0))
        photo_frame.pack_propagate(False)

        # Метка для фото
        self.pan_photo_label = ttk.Label(photo_frame, relief='solid', borderwidth=1)
        self.pan_photo_label.pack(fill='both', expand=True)
        self.photo_image = None  # для хранения ссылки на изображение

        # Поле названия
        ttk.Label(fields_frame, text="Название:").grid(row=0, column=0, sticky='e', pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(fields_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky='w', pady=2)
        self.name_entry.bind('<FocusOut>', lambda e: self.save_dish_details())

        # Выбор кастрюли по умолчанию
        ttk.Label(fields_frame, text="Кастрюля:").grid(row=1, column=0, sticky='e', pady=2)
        self.pan_var = tk.StringVar()  # хранит id кастрюли
        self.pan_combo = ttk.Combobox(fields_frame, textvariable=self.pan_var, width=38, state='readonly')
        self.pan_combo.grid(row=1, column=1, sticky='w', pady=2)
        self.pan_combo.bind('<<ComboboxSelected>>', self.on_pan_selected)

        # Типичный вес готового блюда
        ttk.Label(fields_frame, text="Вес БРУТТО готового блюда (г):").grid(row=2, column=0, sticky='e', pady=2)
        self.weight_var = tk.StringVar()
        self.weight_entry = ttk.Entry(fields_frame, textvariable=self.weight_var, width=40)
        self.weight_entry.grid(row=2, column=1, sticky='w', pady=2)
        self.weight_entry.bind('<FocusOut>', lambda e: self.save_dish_details())

        # Таблица состава блюда
        ttk.Label(right_frame, text="Состав блюда:", font=('Arial', 10, 'bold')).grid(row=1, column=0, columnspan=2,
                                                                                      sticky='w', pady=(10, 0))

        # Кнопки управления составом
        comp_btn_frame = ttk.Frame(right_frame)
        comp_btn_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        ttk.Button(comp_btn_frame, text="Добавить продукт", command=self.add_product_to_dish).pack(side='left', padx=2)
        ttk.Button(comp_btn_frame, text="Изменить вес", command=self.edit_product_weight).pack(side='left', padx=2)
        ttk.Button(comp_btn_frame, text="Удалить продукт", command=self.delete_product_from_dish).pack(side='left',
                                                                                                       padx=2)

        # Таблица состава
        columns = ('product', 'weight')
        self.comp_tree = ttk.Treeview(right_frame, columns=columns, show='headings', height=10)
        self.comp_tree.heading('product', text='Продукт')
        self.comp_tree.heading('weight', text='Вес (г)')
        self.comp_tree.column('product', width=200)
        self.comp_tree.column('weight', width=100)

        # Настраиваем высоту строк Treeview и добавляем чередование строк
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=25)
        style.map('Custom.Treeview',
                  background=[('selected', '#0078d7')],
                  foreground=[('selected', 'white')])
        self.comp_tree.configure(style="Custom.Treeview")

        # Включаем чередование строк в Treeview
        self.comp_tree.tag_configure('oddrow', background='#f5f5f5')
        self.comp_tree.tag_configure('evenrow', background='#ffffff')

        scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.comp_tree.yview)
        self.comp_tree.configure(yscrollcommand=scrollbar.set)

        self.comp_tree.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=5)
        scrollbar.grid(row=3, column=2, sticky='ns')

        # Настройка весов для растяжения
        right_frame.columnconfigure(1, weight=1)
        right_frame.rowconfigure(3, weight=1)
        right_frame.columnconfigure(0, weight=1)

    def load_pans(self):
        """Загружает список кастрюль для комбобокса."""
        self.pans_list = [(0, '— нет —', 0, None)]  # нулевой ID для "нет"
        pans = database.get_all_pans()
        for p in pans:
            self.pans_list.append((p['id'], p['name'], p['weight'], p['photo_path']))
        self.pan_combo['values'] = [name for _, name, _, _ in self.pans_list]

    def load_products(self):
        """Загружает список продуктов для диалогов."""
        prods = database.get_all_products()
        self.products_list = [(p['id'], p['name']) for p in prods]

    def refresh_dishes_list(self):
        """Обновляет список блюд в левой панели."""
        # Сохраняем текущее выделение, если есть
        current_selection = self.current_dish_id

        self.dishes_listbox.delete(0, tk.END)
        dishes = database.get_all_dishes()
        self.dish_items = []  # список кортежей (id, name)
        for d in dishes:
            self.dishes_listbox.insert(tk.END, d['name'])
            self.dish_items.append((d['id'], d['name']))

        # Восстанавливаем выделение, если блюдо все еще существует
        if current_selection is not None:
            for i, (did, _) in enumerate(self.dish_items):
                if did == current_selection:
                    self.dishes_listbox.selection_set(i)
                    break

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
        photo_path = None
        for i, (pid, _, _, photo) in enumerate(self.pans_list):
            if pid == pan_id:
                pan_index = i
                photo_path = photo
                break
        self.pan_combo.current(pan_index)

        # Отображаем фото кастрюли
        self.show_pan_photo(photo_path)

        # Типичный вес
        if dish['default_cooked_weight'] is not None:
            self.weight_var.set(str(dish['default_cooked_weight']))
        else:
            self.weight_var.set('')

        # Загружаем состав
        self.refresh_composition_table()

    def on_pan_selected(self, event):
        """Обработчик выбора кастрюли."""
        # Сохраняем изменения
        self.save_dish_details()

        # Отображаем фото выбранной кастрюли
        pan_index = self.pan_combo.current()
        if pan_index >= 0 and pan_index < len(self.pans_list):
            photo_path = self.pans_list[pan_index][3]
            self.show_pan_photo(photo_path)

    def show_pan_photo(self, photo_path):
        """Отображает фото кастрюли."""
        if not photo_path:
            # Если нет фото, показываем заглушку
            self.pan_photo_label.config(image='', text='Нет фото')
            return

        try:
            # Формируем полный путь к фото
            if not os.path.isabs(photo_path):
                photo_path = os.path.join(BASE_DIR, photo_path)

            if os.path.exists(photo_path):
                # Загружаем и масштабируем изображение
                image = Image.open(photo_path)
                image = image.resize((200, 200), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(image)
                self.pan_photo_label.config(image=self.photo_image, text='')
            else:
                self.pan_photo_label.config(image='', text='Фото не найдено')
        except Exception as e:
            print(f"Ошибка загрузки фото: {e}")
            self.pan_photo_label.config(image='', text='Ошибка загрузки')

    def clear_right_panel(self):
        """Очищает правую панель (когда блюдо не выбрано)."""
        self.name_var.set('')
        self.pan_combo.current(0)
        self.weight_var.set('')
        self.pan_photo_label.config(image='', text='Нет фото')
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

    def refresh_composition_table(self):
        """Обновляет таблицу состава для текущего блюда."""
        for row in self.comp_tree.get_children():
            self.comp_tree.delete(row)
        if self.current_dish_id is None:
            return
        comp = database.get_dish_composition(self.current_dish_id)
        for i, item in enumerate(comp):
            # Чередуем фоны для строк
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.comp_tree.insert('', 'end', values=(item['product_name'], item['weight']),
                                  tags=(tag, item['product_id']))

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

        # Получаем размеры экрана и устанавливаем размер диалога
        screen_height = dialog.winfo_screenheight()
        dialog.geometry(f"600x{screen_height - 100}")  # Ширина 600, высота почти весь экран

        # Переменная для хранения выбранного продукта
        selected_product_id = None
        selected_product_name = None

        # Верхняя часть: список продуктов
        list_label = ttk.Label(dialog, text="Выберите продукт:", font=('Arial', 10, 'bold'))
        list_label.pack(pady=(10, 5))

        # Список продуктов с прокруткой
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        scrollbar_y = ttk.Scrollbar(list_frame, orient='vertical')
        scrollbar_y.pack(side='right', fill='y')

        # Создаем Listbox с чередованием фона
        listbox = self._create_colored_listbox(list_frame, bg_light="#f5f5f5", bg_dark="#ffffff")
        listbox.pack(side='left', fill='both', expand=True)

        # Настраиваем высоту строк для Listbox в диалоге
        self._configure_listbox_height(listbox)

        scrollbar_y.config(command=listbox.yview)

        # Заполняем список продуктами (всегда загружаем свежие данные)
        products = database.get_all_products()
        product_map = {}
        for p in products:
            listbox.insert(tk.END, p['name'])
            product_map[p['name']] = p['id']

        # Нижняя часть: ввод веса и кнопки
        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(fill='x', padx=10, pady=10)

        # Поле ввода веса
        weight_frame = ttk.Frame(bottom_frame)
        weight_frame.pack(fill='x', pady=5)
        ttk.Label(weight_frame, text="Вес (г):", font=('Arial', 10)).pack(side='left', padx=(0, 10))
        weight_entry = ttk.Entry(weight_frame, width=15, font=('Arial', 10))
        weight_entry.pack(side='left')
        weight_entry.insert(0, "100")

        # Кнопки
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(fill='x', pady=10)

        def on_product_select(event):
            """Обработчик выбора продукта из списка."""
            nonlocal selected_product_id, selected_product_name
            selection = listbox.curselection()
            if selection:
                selected_product_name = listbox.get(selection[0])
                selected_product_id = product_map[selected_product_name]
                # Перемещаем фокус на поле ввода веса
                weight_entry.focus_set()

        def on_weight_return(event):
            """Обработчик нажатия Enter в поле веса."""
            if selected_product_id is not None:
                add()
            else:
                messagebox.showerror("Ошибка", "Сначала выберите продукт из списка")

        def add():
            if selected_product_id is None:
                messagebox.showerror("Ошибка", "Выберите продукт из списка")
                return
            try:
                weight = float(weight_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Вес должен быть числом")
                return

            # Проверяем, есть ли уже такой продукт в составе
            comp = database.get_dish_composition(self.current_dish_id)
            existing = [item for item in comp if item['product_id'] == selected_product_id]
            if existing:
                if messagebox.askyesno("Подтверждение",
                                       f"Продукт '{selected_product_name}' уже есть в составе.\nЗаменить вес?"):
                    database.update_dish_composition(self.current_dish_id, selected_product_id, weight)
                else:
                    return
            else:
                database.add_dish_composition(self.current_dish_id, selected_product_id, weight)

            self.refresh_composition_table()
            dialog.destroy()

        def cancel():
            dialog.destroy()

        # Привязываем события
        listbox.bind('<<ListboxSelect>>', on_product_select)
        weight_entry.bind('<Return>', on_weight_return)

        # Кнопки
        ttk.Button(button_frame, text="Добавить", command=add, width=15).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Отмена", command=cancel, width=15).pack(side='left', padx=5)

        # Центрируем кнопки
        button_frame.pack_configure(anchor='center')

        # Устанавливаем фокус на список продуктов
        listbox.focus_set()

    def edit_product_weight(self):
        """Изменение веса выбранного продукта в составе."""
        if self.current_dish_id is None:
            return
        selected = self.comp_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите продукт в таблице состава")
            return
        item = self.comp_tree.item(selected[0])
        product_id = item['tags'][1]  # product_id теперь на позиции 1 (после тега строки)
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
        product_id = item['tags'][1]  # product_id теперь на позиции 1
        product_name = item['values'][0]
        if messagebox.askyesno("Подтверждение", f"Удалить '{product_name}' из состава?"):
            database.delete_dish_composition(self.current_dish_id, product_id)
            self.refresh_composition_table()