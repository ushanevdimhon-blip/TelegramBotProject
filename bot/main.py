import asyncio
import logging
from bot import dp, bot
from bot.handlers import start, help, info

# Настройка логирования
logging.basicConfig(level=logging.INFO) #сохраняем логи на будущее (с уровня INFO и выше)


async def main():
    """Основная функция запуска бота"""

    # Регистрируем роутеры в диспетчере
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(info.router)

    # Запускаем polling
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('❌ Сервер не запущен')