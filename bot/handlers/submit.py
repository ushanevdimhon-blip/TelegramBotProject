from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
import logging

logger = logging.getLogger(__name__)
router = Router()

class SubmitState(StatesGroup):
    waiting_for_link = State()

@router.message(Command("submit"))
async def cmd_submit_start(message: Message, state: FSMContext):
    """Проверка регистрации и начало загрузки работы"""

    user_id = message.from_user.id
    username = message.from_user.username or 'не указан'

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Сервис таблиц временно недоступен. Попробуйте позже.")
        return

    user = sheets.get_user(user_id)

    if not user:
        #Зарегистрирован ли пользователь
        await message.answer(
            f"👋 Привет, @{username}!\n\n"
            f"⚠️ Сначала зарегистрируйтесь командой /start,\n"
            f"затем используйте /submit для загрузки работы."
        )
        return

    full_name = user.get('user_full_name', 'пользователь')

    await message.answer(
        f"<b>ЗАГРУЗКА РАБОТЫ</b>\n\n"
        f"👤 {full_name}, отправьте ссылку на вашу работу.\n\n"
        f"<b>Примеры:</b>\n"
        f"• Google Doc: https://docs.google.com/document/d/...\n"
        f"• GitHub: https://github.com/user/repo\n"
        f"• Google Drive: https://drive.google.com/...\n\n",
        parse_mode="HTML"
    )

    # сохраняем user_id в state и переходим в состояние ожидания ссылки
    await state.update_data(user_id=user_id)
    await state.set_state(SubmitState.waiting_for_link)

@router.message(SubmitState.waiting_for_link, F.text)
async def handle_work_link(message: Message, state: FSMContext):
    """Получение ссылки, валидация и сохранение в таблицу"""

    file_link = message.text.strip()
    data = await state.get_data()
    user_id = data.get('user_id')


    #TODO:Прописать проверку ссылки на валидность (если проходит - ок, нет - просим еще раз)
    #TODO: Если одна работа пользователя уже есть в таблице - сообщаем и предлагаем обновить (/update link или т.п)
    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Сервис таблиц временно недоступен. Попробуйте позже.")
        await state.clear()
        return

    user = sheets.get_user(user_id)
    full_name = user.get('user_full_name', '') if user else ''

    # Сохраняем работу в таблицу
    result = sheets.add_submission(
        telegram_id=user_id,
        student_name=full_name,
        file_link=file_link
    )

    if result:

        submission_id = sheets.get_submission_id(user_id) #НЕ МЕНЯТЬ НА get_submission(), получаем только по id
        #иначе автоматически ставит статус in_progress и сносит очередь

        await message.answer(
            f"✅ Работа загружена!\n\n"
            f"ID: #{submission_id}\n"
            f"Ссылка: {file_link}\n"
            f"Статус: В очереди на проверку"
        )
        logger.info(f"Студент {user_id} загрузил работу #{submission_id}")
    else:
        await message.answer(
            "❌ Не удалось сохранить работу.\n"
            "Попробуйте /submit ещё раз."
        )
        logger.error(f"Ошибка сохранения работы для пользователя {user_id}")

    await state.clear()