from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import BasicAuth
from config import BOT_TOKEN, PROXY_IP, PROXY_PORT, PROXY_LOGIN, PROXY_PASSWORD

# Настройка прокси
auth = BasicAuth(login=PROXY_LOGIN, password=PROXY_PASSWORD)
session = AiohttpSession(proxy=(f"socks5://{PROXY_IP}:{PROXY_PORT}", auth))

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

__all__ = ['bot', 'dp'] #Список того что можно импортировать отсюда