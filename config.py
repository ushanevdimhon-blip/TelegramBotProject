import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
PROXY_LOGIN = os.getenv("PROXY_LOGIN")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# Проверка, что ключи загружены
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")
if not PROXY_LOGIN:
    raise ValueError("PROXY_LOGIN не найден в .env файле")
if not PROXY_PASSWORD:
    raise ValueError("PROXY_PASSWORD не найден в .env файле")
if not PROXY_IP:
    raise ValueError("PROXY_IP не найден в .env файле")
if not PROXY_PORT:
    raise ValueError("PROXY_PORT не найден в .env файле")
