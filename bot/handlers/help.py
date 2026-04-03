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
        "/info - посмотреть информацию о боте\n"
        "/submit - отправить работу на проверку\n"
        "/next - проверить следующую работу\n"
    )