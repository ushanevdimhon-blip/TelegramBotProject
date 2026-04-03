from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.utils.markdown import hbold
from services.sheets import get_sheets_service
from config import START_MESSAGE_EFFECT


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start (Регистрация пользователя)"""
    user_id = message.from_user.id
    username = message.from_user.username or "empty"
    full_name = message.from_user.full_name or "username"

    sheets = get_sheets_service()

    if not sheets:
        await message.answer("Google sheets временно недоступен, попробуйте позже")
        return

    if sheets.add_user(telegram_id = user_id, username = username):
        await message.answer(
            f"Привет, {full_name}!\n\n"
            f"Вы зарегистрированы в системе.\n"
            f"Используйте /submit чтобы сдать работу\n"
            f"Используйте /next чтобы взять работу на проверку",
            message_effect_id=START_MESSAGE_EFFECT
        )
    else:
        await message.answer(
            f"Привет, {full_name}!\n"
            f"Нам не удалось вас зарегистрировать, пожалуйста, попробуйте позже"
        )