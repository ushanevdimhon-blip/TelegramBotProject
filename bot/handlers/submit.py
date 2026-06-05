from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
import logging

logger = logging.getLogger(__name__)
router = Router()

class SubmitState(StatesGroup):
    waiting_for_link = State() #Первичная загрузка - сюда попадет пользователь при первой отправке
    waiting_for_new_link = State()  # Ожидание новой ссылки (обновление)

def get_update_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для обновления существующей работы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить работу", callback_data="update_work")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_update")]
    ])

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

    #Смотрим есть ли у пользователя уже загруженные работы
    existing_submission_id = sheets.get_submission_id(user_id)

    if existing_submission_id:
        # Получаем данные работы
        existing_submission = sheets.get_submission_by_id(existing_submission_id)

        if existing_submission:
            existing_link = existing_submission.get('File_link', 'не указана')
            existing_status = existing_submission.get('Status', 'unknown')

            # Если работа уже проверяется или проверена — не позволяем обновлять
            if existing_status in ['solved', 'in_progress']:
                status_display = {
                    'in_progress': '🔍 На проверке',
                    'solved': '✅ Проверено'
                }.get(existing_status, existing_status)

                await message.answer(
                    f"⚠️ <b>Обновление недоступно!</b>\n\n"
                    f"📝 ID: #{existing_submission_id}\n"
                    f"🔗 Ссылка: <code>{existing_link}</code>\n"
                    f"📊 Статус: {status_display}\n\n"
                    f"<i>Работа уже взята на проверку или проверена.\n"
                    f"Обновление возможно только для работ в очереди.</i>",
                    parse_mode="HTML"
                )
                return

            # Работа в очереди — предлагаем обновить
            await message.answer(
                f"📋 <b>У вас уже есть работа в системе!</b>\n\n"
                f"📝 ID: #{existing_submission_id}\n"
                f"🔗 Ссылка: <code>{existing_link}</code>\n"
                f"📊 Статус: В очереди на проверку\n\n"
                f"Вы можете <b>обновить работу</b> — загрузить новую версию.\n\n"
                f"⚠️ <i>При обновлении:</i>\n"
                f"• Ссылка заменится на новую\n"
                f"• Время отправки обновится\n"
                f"• ID работы останется прежним",
                reply_markup=get_update_keyboard(),
                parse_mode="HTML"
            )
            # Сохраняем данные для обновления
            await state.update_data(
                user_id=user_id,
                existing_submission_id=existing_submission_id
            )
            return

    #Если работы в системе нет - стандартная загрузка
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

#Нажата кнопка обновления работы - обрабатываем коллбэк
@router.callback_query(F.data == "update_work")
async def start_update_work(callback: CallbackQuery, state: FSMContext):
    """Начало процесса обновления работы"""

    await callback.message.answer(
        "🔄 <b>ОБНОВЛЕНИЕ РАБОТЫ</b>\n\n"
        "Отправьте <b>новую ссылку</b> на вашу работу.\n"
        "Старая ссылка будет заменена.\n\n"
        "<i>Время отправки обновится автоматически.</i>",
        parse_mode="HTML"
    )

    await state.set_state(SubmitState.waiting_for_new_link)
    await callback.answer()

#Пользователь отменил обновление работы
@router.callback_query(F.data == "cancel_update")
async def cancel_update(callback: CallbackQuery, state: FSMContext):
    """Отмена обновления"""

    await state.clear()
    try:
        await callback.message.edit_text("❌ Обновление отменено.")
    except:
        pass
    await callback.answer()

#Обработка новой ссылки
@router.message(SubmitState.waiting_for_new_link, F.text)
async def handle_new_link(message: Message, state: FSMContext):
    """Получили новую ссылку для обновления работы"""

    new_file_link = message.text.strip()
    data = await state.get_data()
    user_id = data.get('user_id')
    existing_id = data.get('existing_submission_id')

    # TODO: проверка ссылки на валидность

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Сервис таблиц временно недоступен.")
        await state.clear()
        return

    # ОБНОВЛЯЕМ СУЩЕСТВУЮЩУЮ РАБОТУ
    # При изменении file_link автоматически обновится Created_at
    result = sheets.update_submission(
        submission_id=existing_id,
        file_link=new_file_link,
        new_status='not_solved'  # Явно сбрасываем статус (на всякий случай)
    )

    if result:
        await message.answer(
            f"✅ <b>Работа успешно обновлена!</b>\n\n"
            f"📝 ID: #{existing_id}\n"
            f"🔗 Новая ссылка: <code>{new_file_link}</code>\n"
            f"📊 Статус: ⏳ В очереди на проверку\n",
            parse_mode="HTML"
        )
        logger.info(f"Студент {user_id} обновил работу #{existing_id}")
    else:
        await message.answer(
            "❌ Не удалось обновить работу.\n"
            "Попробуйте /submit ещё раз."
        )
        logger.error(f"Ошибка обновления работы #{existing_id} для пользователя {user_id}")

    await state.clear()

#Первичная загрузка работы
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