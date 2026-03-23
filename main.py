import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import BasicAuth
from config import BOT_TOKEN, PROXY_IP, PROXY_PORT, PROXY_LOGIN, PROXY_PASSWORD


auth = BasicAuth(login=PROXY_LOGIN, password=PROXY_PASSWORD)
session = AiohttpSession(proxy=(f"socks5://{PROXY_IP}:{PROXY_PORT}", auth))
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

@dp.message(CommandStart())
async def c_start(message: Message):
    await message.answer(f'Здарова, '
                         f'{html.bold(message.from_user.last_name).replace('<b>','').replace('</b>','')}',
    message_effect_id = '5046509860389126442')

async def main():
    await dp.start_polling(bot)

if __name__=='__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Сервер не запущен')