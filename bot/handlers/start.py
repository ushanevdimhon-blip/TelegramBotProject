from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
from config import START_MESSAGE_EFFECT, ORGANIZER_PASSWORD, EXPERT_PASSWORD
import logging


logger = logging.getLogger(__name__)
router = Router()

class RegisterState(StatesGroup):
    """Состояния для процесса регистрации"""
    waiting_for_full_name = State()
    waiting_for_role = State()
    waiting_for_password = State()


def get_role_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками выбора роли"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🎓 Студент", callback_data="role_student")],
        [InlineKeyboardButton(text="👨‍🏫 Эксперт", callback_data="role_expert")],
        [InlineKeyboardButton(text="👔 Организатор", callback_data="role_organizer")],
    ])


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

    if existing_user: #Блок выполняется, если пользователь уже есть в таблице
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


    await state.update_data(user_id=user_id, username=username)
    await state.set_state(RegisterState.waiting_for_full_name)


@router.message(RegisterState.waiting_for_full_name, F.text)
async def handle_full_name(message: Message, state: FSMContext):
    """Сохранение ФИО пользователя в таблицу"""

    full_name = message.text.strip()
    # TODO: проверять валидность введенных данных?

    # Сохраняем ФИО
    await state.update_data(full_name=full_name)

    # Показываем выбор роли
    await message.answer(
        f"ФИО: {full_name}\n\n"
        f"<b>ВЫБЕРИТЕ ВАШУ РОЛЬ:</b>",
        reply_markup=get_role_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(RegisterState.waiting_for_role)

#Обработка выбора роли
@router.callback_query(RegisterState.waiting_for_role, F.data.startswith("role_"))
async def handle_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора роли"""

    role = callback.data.split("_")[1]
    await state.update_data(role=role)

    if role == "student":
        await register_user(callback.message, state)
        await callback.answer("Регистрация завершена", show_alert=False)
        return

    role_names = {
        "expert": "эксперт",
        "organizer": "организатор"
    }

    await callback.message.answer(
        f" Для регистрации в роли <b>{role_names[role]}</b> введите пароль:",
        parse_mode="HTML"
    )

    await state.set_state(RegisterState.waiting_for_password)
    await callback.answer()

#Обработка введенного пароля
@router.message(RegisterState.waiting_for_password, F.text)
async def handle_password(message: Message, state: FSMContext):
    """Проверка пароля и завершение регистрации"""

    password = message.text.strip()
    data = await state.get_data()
    role = data.get("role")

    #Определяем правильный пароль
    correct_password = None
    if role == "expert":
        correct_password = EXPERT_PASSWORD
    elif role == "organizer":
        correct_password = ORGANIZER_PASSWORD

    #Проверяем пароль
    if password == correct_password:
        await register_user(message, state)
    else:
        await message.answer(
            "<b>Неверный пароль!</b>\n\n"
            "Попробуйте /start чтобы начать регистрацию заново.",
            parse_mode="HTML"
        )
        logger.warning(f"Неверный пароль для роли {role} от пользователя {data.get('user_id')}")
        await state.clear()

async def register_user(message: Message, state: FSMContext):
    """Сохранение пользователя в google sheets"""

    data = await state.get_data()
    user_id = data.get("user_id")
    username = data.get("username")
    full_name = data.get("full_name")
    role = data.get("role","student")

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Ошибка: сервис недоступен, попробуйте позже")
        await state.clear()
        return

    role_names = {
        "student": "студент",
        "expert": "эксперт",
        "organizer": "организатор"
    }

    result = sheets.add_user(
        telegram_id=user_id,
        username=username,
        user_full_name=full_name,
        role=role
    )

    if result:
        await message.answer(
            f"✅ <b>Регистрация успешна!</b>\n\n"
            f"ФИО: {full_name}\n"
            f"Роль: {role_names[role]}\n\n"
            f"Используйте /help чтобы посмотреть список доступных команд",
            parse_mode="HTML",
            message_effect_id=START_MESSAGE_EFFECT
        )
        logger.info(f"Зарегистрирован: {user_id} — {full_name} ({role})")
    else:
        await message.answer(
            "❌ Не удалось сохранить данные.\n"
            "Попробуйте /start ещё раз."
        )
        logger.error(f"Ошибка регистрации: {user_id}")

    await state.clear()