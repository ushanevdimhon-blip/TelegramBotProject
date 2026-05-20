from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    #TODO: Внести сюда список доступных команд с объяснением их работы
    """Обработчик команды /help"""
    await message.answer(
        "/start - начать работу бота\n"
        "/help - получить справку по командам\n"
        "/info - посмотреть информацию о боте\n\n"
        "/submit - отправить работу на проверку\n\n"
        "/next1 - проверить следующую работу для первого режима бота\n"
        "/next2 - проверить следующую работу для второго режима бота\n\n"
        "/check_status - узнать статус своей работы"
    )