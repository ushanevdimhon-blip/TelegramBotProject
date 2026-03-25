from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.utils.markdown import hbold
from config import START_MESSAGE_EFFECT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_last_name = message.from_user.last_name or ''

    await message.answer(
        f'Здарова, {hbold(user_last_name).replace("<b>", "").replace("</b>", "")}!',
        message_effect_id=START_MESSAGE_EFFECT
    )