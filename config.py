import os

# Путь к папке с программой
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Путь к базе данных
DB_PATH = os.path.join(BASE_DIR, 'food.db')

# Папка для фото кастрюль
PANS_PHOTO_DIR = os.path.join(BASE_DIR, 'pans_photos')
if not os.path.exists(PANS_PHOTO_DIR):
    os.makedirs(PANS_PHOTO_DIR)

# Настройки по умолчанию (позже будут загружаться из конфига)
DEFAULT_CARBS_PER_XE = 12