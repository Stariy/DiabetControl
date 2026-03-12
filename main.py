import tkinter as tk
from tkinter import ttk
import database
from products_tab import ProductsTab
from pans_tab import PansTab
from dishes_tab import DishesTab
from calculator_tab import CalculatorTab


def populate_initial_data():
    """Заполняет базу начальными продуктами, если таблица пуста."""
    if database.count_products() == 0:
        # Список продуктов: название, углеводы (остальное = 0, ГИ = None)
        products = [
            ("Морковь", 6.8),
            ("Перец болгарский красный", 4.9),
            ("Фасоль", 3.0),
            ("помидоры", 3.9),
            ("Картофель", 17.0),
            ("Лук репчатый", 9.3),
            ("Овощи", 0.0),  # заглушка
            ("Огурец свежий", 3.6),
            ("Помидор", 4.2),
            ("Капуста белокочанная", 6.8),
            ("Перец болгарский", 6.3),
            ("Салат листовой", 2.9),
            ("Шпинат", 3.6),
            ("Морковь сырая", 8.2),
            ("Свёкла сырая", 9.6),
            ("Картофель отварной", 17.0),
            ("Крупы", 0.0),
            ("Гречка отварная", 21.0),
            ("Овсянка на воде", 15.0),
            ("Рис бурый отварной", 23.0),
            ("Рис белый отварной", 28.0),
            ("Киноа отварная", 21.0),
            ("Перловка отварная", 22.0),
            ("Макароны твёрдых сортов", 28.0),
            ("Хлеб цельнозерновой", 40.0),
            ("Хлеб белый", 50.0),
            ("Белковые продукты", 0.0),
            ("Куриная грудка отварная", 0.0),
            ("Индейка филе", 0.0),
            ("Говядина постная", 0.0),
            ("Рыба белая (треска)", 0.0),
            ("Лосось", 0.0),
            ("Яйцо куриное (1 шт.)", 0.7),
            ("Бобовые", 0.0),
            ("Чечевица отварная", 20.0),
            ("Нут отварной", 27.0),
            ("Фасоль красная отварная", 23.0),
            ("Горох отварной", 20.0),
            ("Фрукты и ягоды", 0.0),
            ("Яблоко зелёное", 10.0),
            ("Груша", 10.7),
            ("Апельсин", 10.0),
            ("Грейпфрут", 7.3),
            ("Клубника", 7.5),
            ("Малина", 9.0),
            ("Черника", 14.0),
            ("Банан", 23.0),
            ("Виноград", 17.0),
            ("Арбуз", 9.0),
            ("Молочные продукты", 0.0),
            ("Молоко 2,5%", 4.7),
            ("Кефир 2,5%", 4.0),
            ("Творог 5%", 1.8),
            ("Творог 0%", 1.3),
            ("Сыр твёрдый", 0.5),
            ("Йогурт натуральный без сахара", 5.0),
            ("Сметана 15%", 3.6),
            ("Орехи и семена", 0.0),
            ("Миндаль", 21.0),
            ("Грецкий орех", 14.0),
            ("Семечки подсолнечника", 20.0),
            ("Арахис", 16.0),
            ("Продукты с осторожностью", 0.0),
            ("Мёд", 82.0),
            ("Сахар", 99.7),
            ("Белый хлеб", 50.0),
            ("Сладкие соки", 12.0),
            ("Печенье сладкое", 65.0)
        ]
        for name, carbs in products:
            database.add_product(name, 0, 0, 0, carbs, None)

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Учёт питания при диабете")
        self.root.geometry("1000x700")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        # Вкладки

        self.calculator_tab = CalculatorTab(self.notebook)
        self.notebook.add(self.calculator_tab, text="Калькулятор")

        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="История")

        self.products_tab = ProductsTab(self.notebook)
        self.notebook.add(self.products_tab, text="Продукты")

        self.dishes_tab = DishesTab(self.notebook)
        self.notebook.add(self.dishes_tab, text="Блюда")

        self.pans_tab = PansTab(self.notebook)
        self.notebook.add(self.pans_tab, text="Кастрюли")



if __name__ == "__main__":
    database.init_db()
    populate_initial_data()  # заполняем начальными продуктами, если нужно
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()