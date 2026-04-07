from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
import logging
from config import START_MESSAGE_EFFECT

logger = logging.getLogger(__name__)
router = Router()

class RegisterState(StatesGroup):
    """Состояния для процесса регистрации"""
    waiting_for_full_name = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start (Регистрация пользователя)"""
    user_id = message.from_user.id
    username = message.from_user.username or "не указан"

    sheets = get_sheets_service()

    if not sheets:
        await message.answer("Google sheets временно недоступен, попробуйте позже")
        return

    existing_user = sheets.get_user(user_id)
    if existing_user:
        full_name = existing_user.get("user_full_name")
        role = existing_user.get("role")
        await message.answer(
            f"👋 Привет, {full_name}!\n\n"
            f"Вы уже зарегистрированы.\n"
            f"Ваша роль - {role}\n"
            f"Используйте /submit чтобы загрузить работу.\n"
            f"Используйте /help чтобы получить справку по доступным командам\n"
        )
        await state.clear()
        return

    await message.answer(
        f"Привет, @{username}!\n\n"
        f"<b>РЕГИСТРАЦИЯ В СИСТЕМЕ</b>\n\n"
        f"Пожалуйста, введите ваше <b>полное ФИО</b>:\n",
        parse_mode="HTML"
    )

    #TODO: проверять валидность введенных данных?
    await state.update_data(user_id=user_id)
    await state.set_state(RegisterState.waiting_for_full_name)


@router.message(RegisterState.waiting_for_full_name, F.text)
async def save_user_name(message: Message, state: FSMContext):
    """Сохранение ФИО пользователя в таблицу"""

    full_name = message.text.strip()
    data = await state.get_data()
    user_id = data.get('user_id')

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Ошибка: сервис недоступен, попробуйте позже")
        await state.clear()
        return

    # Сохраняем пользователя в таблицу
    result = sheets.add_user(
        telegram_id=user_id,
        username=message.from_user.username or 'не указан',
        user_full_name=full_name,
        role='student'
    )

    if result:
        await message.answer(
            f"✅ Готово, {full_name}!\n\n"
            f"Теперь используйте /submit чтобы загрузить работу.",
            message_effect_id=START_MESSAGE_EFFECT
        )
        logger.info(f"Зарегистрирован: {user_id} — {full_name}")
    else:
        await message.answer(
            "Не удалось сохранить данные.\n"
            "Попробуйте /start ещё раз."
        )
        logger.error(f"Ошибка регистрации: {user_id}")

    await state.clear()