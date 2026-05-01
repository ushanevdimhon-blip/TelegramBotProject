from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
from services.whisper import get_whisper_service
import logging

logger = logging.getLogger(__name__)
router = Router()

class ReviewState(StatesGroup):
    """Состояния для процесса проверки работ"""
    waiting_for_feedback = State()
    waiting_for_score = State()

def get_review_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """inline-кнопки для работы с ревью"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать ревью", callback_data=f"write_feedback_{submission_id}")],
        [InlineKeyboardButton(text="❌ Отменить проверку", callback_data=f"cancel_review_{submission_id}")],
    ])


@router.message(Command("next"))
async def next_message(message: Message, state: FSMContext):
    """Взятие следующей работы из очереди"""
    reviewer_id = message.from_user.id
    sheets = get_sheets_service()

    if not sheets:
        await message.answer("Таблица временно недоступна, попробуйте позже 🥺")
        return

    submission = sheets.get_submission()

    if not submission:
        await message.answer("🔥 Очередь пуста, все работы проверены 🔥")
        return

    submission_id = int(submission.get("ID"))
    student_id = submission.get("Student_ID","")
    file_link = submission.get("File_link","Не указана")

    # Сохраняем данные в state
    await state.update_data(
        submission_id=submission_id,
        reviewer_id=reviewer_id,
        student_id=student_id
    )

    status = "Не проверено" if submission.get("Status", "") == "not_solved" \
        else "Проверяется" if submission.get("Status", "") == "in_progress" \
        else "Проверено"

    if not sheets.add_review(submission_id=submission_id, reviewer_id=reviewer_id):
        await message.answer("Не удалось создать запись о проверке 🥺")
        return

    # Формируем информацию о студенте
    student_info = ""
    if student_id:
        student_info = f"👤 Студент: ID `{student_id}`\n"

    await message.answer(
        f"**НОВАЯ РАБОТА #{submission_id}**\n\n"
        f"{student_info}"
        f"Ссылка:  {file_link}\n"
        f"Статус:  `{status}`\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_review_keyboard(submission_id)
    )

#Callback: начать написание ревью
@router.callback_query(F.data.startswith("write_feedback"))
async def start_write_feedback(callback: CallbackQuery, state: FSMContext):
    """Начало написания ревью"""

    await callback.message.answer(
        "✍️ **НАПИШИТЕ ОБРАТНУЮ СВЯЗЬ**\n\n"
        "Отправьте текст ревью для этой работы.\n"
        "Можете записать голосовое сообщение\n\n"
        "После отправки текста вас попросят поставить оценку",
        parse_mode="Markdown"
    )

    await state.set_state(ReviewState.waiting_for_feedback)
    await callback.answer()

#Обработка текста ревью
@router.message(ReviewState.waiting_for_feedback, F.text | F.voice)
async def handle_feedback_text(message: Message, state: FSMContext):
    """Получили текст - сохранили - просим оценку"""

    if message.voice:
        whisper = get_whisper_service()

        if not whisper:
            await message.answer("Распознавание голосовых сообщений"
                                 " временно недоступно 🥺, вы можете отправить текст")
            return
        feedback = await whisper.extract(message.voice.file_id)

    if message.text:
        feedback = message.text.strip()

    data = await state.get_data()
    submission_id = data.get("submission_id")
    reviewer_id = data.get("reviewer_id")

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("Сервис временно недоступен, попробуйте позже")
        await state.clear()
        return

    review_id = sheets.get_review_id(submission_id, reviewer_id)

    if not review_id:
        await message.answer("Не найдена запись о проверке")
        await state.clear()
        return

    result = sheets.update_review(review_id=review_id, feedback=feedback)

    if result:
        await state.update_data(feedback=feedback)

        await message.answer(
            "✅ **РЕВЬЮ СОХРАНЕНО**\n\n"
            "Теперь поставьте **оценку** работе.\n\n",
            parse_mode="Markdown"
        )

        await state.set_state(ReviewState.waiting_for_score)
    else:
        await message.answer("Не удалось сохранить ревью, попробуйте еще раз")
        await state.clear()


@router.message(ReviewState.waiting_for_score, F.text)
async def handle_score(message: Message, state: FSMContext):
    """Получаем оценку - сохраняем - завершаем проверку"""

    score_text = message.text.strip()
    data = await state.get_data()
    submission_id = data.get("submission_id")
    reviewer_id = data.get("reviewer_id")
    feedback = data.get("feedback")

    if not score_text.isdigit():
        await message.answer(
            "⚠️ Не удалось распознать оценку.\n\n"
            "Пожалуйста, отправьте **число**\n"
            "Или напишите /cancel чтобы отменить",
            parse_mode="Markdown"
        )

    score = int(score_text)

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("❌ Ошибка: сервис недоступен")
        await state.clear()
        return

    # Находим id ревью
    review_id = sheets.get_review_id(submission_id, reviewer_id)

    if not review_id:
        await message.answer("❌ Не найдена запись о проверке")
        await state.clear()
        return

    # Сохраняем оценку
    result = sheets.update_review(review_id=review_id, score=score)

    if result:
        sheets.update_submission(submission_id, new_status='solved')

        await message.answer(
            f"✅ **ПРОВЕРКА ЗАВЕРШЕНА!**\n\n"
            f"📝 Работа #{submission_id}\n"
            f"⭐ Оценка: {score}\n"
            f"📄 Ревью: {feedback[:100]}{'...' if len(feedback) > 100 else ''}\n\n"
            f"Статус работы изменён на: \"Проверено\"\n\n"
            f"Используйте /next чтобы взять следующую работу.",
            parse_mode="Markdown"
        )

        logger.info(f"Эксперт {reviewer_id} проверил работу #{submission_id} (оценка: {score})")
    else:
        await message.answer("❌ Не удалось сохранить оценку")
        logger.error(f"Не удалось сохранить оценку для работы #{submission_id}")

    await state.clear()

#нужен ли метод для _skip????

@router.callback_query(F.data.startswith("cancel_review_"))
async def cancel_review(callback: CallbackQuery, state: FSMContext):
    """Отмена проверки через inline-кнопку"""

    try:
        submission_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    reviewer_id = callback.from_user.id
    sheets = get_sheets_service()

    if sheets:
        review_id = sheets.get_review_id(submission_id, reviewer_id)
        if review_id:
            sheets.delete_review(review_id)
            sheets.update_submission(submission_id, new_status='not_solved')

    await state.clear()

    try:
        await callback.message.delete()
    except:
        await callback.message.edit_text("🔸 Проверка отменена")

    await callback.answer("🔸 Отменено", show_alert=False)
    await callback.message.answer(
        "🔸 Проверка отменена.\nИспользуйте /next чтобы взять другую работу.",
        parse_mode="Markdown"
    )
