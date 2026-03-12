import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')

# Проверка, что ключи загружены
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")