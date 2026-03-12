import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.filters import CommandStart
from aiogram.types import Message

bot = Bot('8705382496:AAH9AhsmnTTj64mAGihM5FPWnAKz3OtmhNg')
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