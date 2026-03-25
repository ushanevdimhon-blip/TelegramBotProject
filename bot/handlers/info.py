from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("info"))
async def c_info(message: Message):
    """Обработчик команды /info"""
    #TODO: Расширить описание функционала бота
    await message.answer(
        "О ПРОЕКТЕ\n\n"
        "Сервис для сбора экспертной обратной связи по проектам.\n\n"
    )