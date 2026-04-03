import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем переменные окружения

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_TOKEN = os.getenv('BOT_TOKEN')

PROXY_LOGIN = os.getenv("PROXY_LOGIN")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
GOOGLE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')


START_MESSAGE_EFFECT = os.getenv('START_MESSAGE_EFFECT', '5046509860389126442')


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
