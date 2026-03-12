import sqlite3
from config import DB_PATH


def get_connection():
    """Возвращает соединение с БД с включёнными внешними ключами."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт все таблицы, если они ещё не существуют."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                calories REAL NOT NULL,
                proteins REAL NOT NULL,
                fats REAL NOT NULL,
                carbs REAL NOT NULL,
                glycemic_index INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                weight REAL NOT NULL,
                photo_path TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                default_pan_id INTEGER,
                default_cooked_weight REAL,
                FOREIGN KEY (default_pan_id) REFERENCES pans(id) ON DELETE SET NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dish_composition (
                dish_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                PRIMARY KEY (dish_id, product_id),
                FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime TEXT NOT NULL,
                insulin_dose REAL,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id INTEGER NOT NULL,
                component_type TEXT NOT NULL CHECK(component_type IN ('product', 'dish')),
                product_id INTEGER,
                dish_id INTEGER,
                serving_weight REAL NOT NULL,
                cooked_dish_weight REAL,
                pan_id INTEGER,
                FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
                FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE SET NULL,
                FOREIGN KEY (pan_id) REFERENCES pans(id) ON DELETE SET NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_composition_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id INTEGER NOT NULL,
                meal_component_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                is_part_of_dish BOOLEAN NOT NULL,
                FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
                FOREIGN KEY (meal_component_id) REFERENCES meal_components(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            )
        ''')

        conn.commit()


def populate_initial_products():
    """Заполняет таблицу продуктов начальными данными, если она пуста."""
    products_data = [
        ("Морковь", 6.8),
        ("Перец болгарский красный", 4.9),
        ("Фасоль", 3.0),
        ("помидоры", 3.9),
        ("Картофель", 17.0),
        ("Лук репчатый", 9.3),
        ("Огурец свежий", 3.6),
        ("Помидор", 4.2),
        ("Капуста белокочанная", 6.8),
        ("Перец болгарский", 6.3),
        ("Салат листовой", 2.9),
        ("Шпинат", 3.6),
        ("Морковь сырая", 8.2),
        ("Свёкла сырая", 9.6),
        ("Картофель отварной", 17.0),
        ("Гречка отварная", 21.0),
        ("Овсянка на воде", 15.0),
        ("Рис бурый отварной", 23.0),
        ("Рис белый отварной", 28.0),
        ("Киноа отварная", 21.0),
        ("Перловка отварная", 22.0),
        ("Макароны твёрдых сортов", 28.0),
        ("Хлеб цельнозерновой", 40.0),
        ("Хлеб белый", 50.0),
        ("Куриная грудка отварная", 0.0),
        ("Индейка филе", 0.0),
        ("Говядина постная", 0.0),
        ("Рыба белая (треска)", 0.0),
        ("Лосось", 0.0),
        ("Яйцо куриное (1 шт.)", 0.7),
        ("Чечевица отварная", 20.0),
        ("Нут отварной", 27.0),
        ("Фасоль красная отварная", 23.0),
        ("Горох отварной", 20.0),
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
        ("Молоко 2,5%", 4.7),
        ("Кефир 2,5%", 4.0),
        ("Творог 5%", 1.8),
        ("Творог 0%", 1.3),
        ("Сыр твёрдый", 0.5),
        ("Йогурт натуральный без сахара", 5.0),
        ("Сметана 15%", 3.6),
        ("Миндаль", 21.0),
        ("Грецкий орех", 14.0),
        ("Семечки подсолнечника", 20.0),
        ("Арахис", 16.0),
        ("Мёд", 82.0),
        ("Сахар", 99.7),
        ("Белый хлеб", 50.0),
        ("Сладкие соки", 12.0),
        ("Печенье сладкое", 65.0),
    ]
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        if count == 0:
            for name, carbs in products_data:
                # Пропускаем строки-заголовки (их нет в списке, но оставим проверку на случай)
                if name in ["Овощи", "Крупы", "Белковые продукты", "Бобовые", "Фрукты и ягоды", "Молочные продукты",
                            "Орехи и семена", "Продукты с осторожностью"]:
                    continue
                # Вставим с нулевыми калориями, белками, жирами, и NULL ГИ
                cursor.execute('''
                    INSERT INTO products (name, calories, proteins, fats, carbs, glycemic_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, 0.0, 0.0, 0.0, carbs, None))
            conn.commit()


# ---- Функции для работы с продуктами ----
def get_all_products():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name")
        return cursor.fetchall()


def add_product(name, calories, proteins, fats, carbs, glycemic_index):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, calories, proteins, fats, carbs, glycemic_index)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, calories, proteins, fats, carbs, glycemic_index))
        conn.commit()
        return cursor.lastrowid


def update_product(product_id, name, calories, proteins, fats, carbs, glycemic_index):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products
            SET name=?, calories=?, proteins=?, fats=?, carbs=?, glycemic_index=?
            WHERE id=?
        ''', (name, calories, proteins, fats, carbs, glycemic_index, product_id))
        conn.commit()


def delete_product(product_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()


def get_product(product_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        return cursor.fetchone()


# ---- Функции для работы с кастрюлями ----
def get_all_pans():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pans ORDER BY name")
        return cursor.fetchall()


def add_pan(name, weight, photo_path):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pans (name, weight, photo_path)
            VALUES (?, ?, ?)
        ''', (name, weight, photo_path))
        conn.commit()
        return cursor.lastrowid


def update_pan(pan_id, name, weight, photo_path):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pans
            SET name=?, weight=?, photo_path=?
            WHERE id=?
        ''', (name, weight, photo_path, pan_id))
        conn.commit()


def delete_pan(pan_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pans WHERE id=?", (pan_id,))
        conn.commit()


def get_pan(pan_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pans WHERE id=?", (pan_id,))
        return cursor.fetchone()


def count_products():
    """Возвращает количество продуктов в таблице."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        return cursor.fetchone()[0]


# ---- Функции для работы с блюдами ----
def get_all_dishes():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dishes ORDER BY name")
        return cursor.fetchall()

def add_dish(name, default_pan_id=None, default_cooked_weight=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO dishes (name, default_pan_id, default_cooked_weight)
            VALUES (?, ?, ?)
        ''', (name, default_pan_id, default_cooked_weight))
        conn.commit()
        return cursor.lastrowid

def update_dish(dish_id, name, default_pan_id=None, default_cooked_weight=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE dishes
            SET name=?, default_pan_id=?, default_cooked_weight=?
            WHERE id=?
        ''', (name, default_pan_id, default_cooked_weight, dish_id))
        conn.commit()

def delete_dish(dish_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dishes WHERE id=?", (dish_id,))
        conn.commit()

def get_dish(dish_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dishes WHERE id=?", (dish_id,))
        return cursor.fetchone()

# ---- Функции для состава блюда ----
def get_dish_composition(dish_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT dc.*, p.name as product_name
            FROM dish_composition dc
            JOIN products p ON dc.product_id = p.id
            WHERE dc.dish_id = ?
            ORDER BY p.name
        ''', (dish_id,))
        return cursor.fetchall()

def add_dish_composition(dish_id, product_id, weight):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO dish_composition (dish_id, product_id, weight)
            VALUES (?, ?, ?)
        ''', (dish_id, product_id, weight))
        conn.commit()

def update_dish_composition(dish_id, product_id, weight):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE dish_composition
            SET weight=?
            WHERE dish_id=? AND product_id=?
        ''', (weight, dish_id, product_id))
        conn.commit()

def delete_dish_composition(dish_id, product_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM dish_composition
            WHERE dish_id=? AND product_id=?
        ''', (dish_id, product_id))
        conn.commit()

# ---- Функции для сохранения приёма пищи ----
def save_meal(datetime_str, insulin_dose, notes, components):
    """
    Сохраняет приём пищи.
    components: список словарей, каждый словарь описывает компонент:
        - type: 'product' или 'dish'
        - id: id продукта/блюда
        - name: название (для справки)
        - serving_weight: вес порции
        - для dish также:
            - cooked_weight: вес готового блюда с кастрюлей
            - pan_id: id кастрюли (может быть None)
            - composition: список продуктов в порции (уже с учётом коэффициента)
              каждый элемент: {'product_id': id, 'weight': вес в порции}
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Вставка в meals
        cursor.execute('''
            INSERT INTO meals (datetime, insulin_dose, notes)
            VALUES (?, ?, ?)
        ''', (datetime_str, insulin_dose, notes))
        meal_id = cursor.lastrowid

        for comp in components:
            # Вставка в meal_components
            if comp['type'] == 'product':
                cursor.execute('''
                    INSERT INTO meal_components
                    (meal_id, component_type, product_id, serving_weight)
                    VALUES (?, ?, ?, ?)
                ''', (meal_id, 'product', comp['id'], comp['serving_weight']))
                comp_id = cursor.lastrowid
                # Детальная запись для продукта
                cursor.execute('''
                    INSERT INTO meal_composition_details
                    (meal_id, meal_component_id, product_id, weight, is_part_of_dish)
                    VALUES (?, ?, ?, ?, 0)
                ''', (meal_id, comp_id, comp['id'], comp['serving_weight']))
            else:  # dish
                cursor.execute('''
                    INSERT INTO meal_components
                    (meal_id, component_type, dish_id, serving_weight, cooked_dish_weight, pan_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (meal_id, 'dish', comp['id'], comp['serving_weight'],
                      comp['cooked_weight'], comp.get('pan_id')))
                comp_id = cursor.lastrowid
                # Детальные записи для каждого продукта в составе блюда
                for prod in comp['composition']:
                    cursor.execute('''
                        INSERT INTO meal_composition_details
                        (meal_id, meal_component_id, product_id, weight, is_part_of_dish)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (meal_id, comp_id, prod['product_id'], prod['weight']))
        conn.commit()
        return meal_id