from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.sheets import get_sheets_service
import logging

logger = logging.getLogger(__name__)
router = Router()


class PeerReviewState(StatesGroup):
    """Состояния для peer-to-peer ревью"""
    waiting_for_feedback = State()  # Ожидаем текст ревью
    waiting_for_score = State()     # Ожидаем оценку


def get_peer_review_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для peer ревью (только кнопка отмены)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать ревью", callback_data=f"peer_write_{submission_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"peer_cancel_{submission_id}")],
    ])


@router.message(Command("next2"))
async def cmd_next2(message: Message, state: FSMContext):
    """
    Получение работы для peer-to-peer проверки.
    Каждый студент получает N чужих работ на проверку
    """
    student_id = message.from_user.id
    sheets = get_sheets_service()

    if not sheets:
        await message.answer("⚠️ Сервис временно недоступен, попробуйте позже")
        return

    # ЗНАЧЕНИЕ N ПОТОМ ПОЛУЧАТЬ ИЗ ДАННЫХ ОРГАНИЗАТОРА
    # получаем работы для проверки (n работ, где n можно настроить)
    submissions = sheets.get_n_submissions(asker_tg_id=student_id, n=2)

    if not submissions or len(submissions) == 0:
        await message.answer(
            "Все доступные работы распределены!\n\n"
            "Пока нет новых работ для проверки.\n"
            "Попробуйте позже."
        )
        return

    # ФИЛЬТРАЦИЯ: убираем работы, которые студент уже проверял, НЕ УБИРАТЬ
    reviews_worksheet = sheets.reviews_worksheet
    if reviews_worksheet:
        try:
            all_reviews = reviews_worksheet.get_all_records()
            # Получаем список submission_id, которые уже проверил этот студент
            reviewed_ids = [
                int(str(review.get('Submission_ID')))
                for review in all_reviews
                if int(str(review.get('Reviewer_ID', 0))) == student_id
            ]

            # Фильтруем работы, оставляя только те, которые студент ещё не проверял
            submissions = [
                sub for sub in submissions
                if int(str(sub.get('ID'))) not in reviewed_ids
            ]
        except Exception as e:
            logger.error(f"Ошибка фильтрации проверенных работ: {e}")

    # Если после фильтрации работ не осталось
    if not submissions or len(submissions) == 0:
        await message.answer(
            "🎉 Вы проверили все доступные работы!\n\n"
            "Пока нет новых работ для проверки."
        )
        return

    # Берём первую работу из отфильтрованного списка
    submission = submissions[0]
    submission_id = int(submission.get("ID"))
    file_link = submission.get("File_link", "Не указана")

    # Сохраняем данные в state
    await state.update_data(
        submission_id=submission_id,
        student_id=student_id,
    )

    await message.answer(
        f"📋 **РЕЖИМ 2: PEER-TO-PEER РЕВЬЮ**\n\n"
        f"🔗 Ссылка: `{file_link}`\n\n"
        f"Проверьте работу и оставьте обратную связь:",
        parse_mode="Markdown",
        reply_markup=get_peer_review_keyboard(submission_id)
    )


@router.callback_query(F.data.startswith("peer_write_"))
async def start_peer_review(callback: CallbackQuery, state: FSMContext):
    """Начало написания peer ревью"""

    await callback.message.answer(
        "✍️ **НАПИШИТЕ ОБРАТНУЮ СВЯЗЬ**\n\n"
        "Отправьте текст ревью для этой работы.\n"
        "После отправки ревью вам будет предложено поставить оценку\n",
        parse_mode="Markdown"
    )

    await state.set_state(PeerReviewState.waiting_for_feedback)
    await callback.answer()


@router.message(PeerReviewState.waiting_for_feedback, F.text)
async def handle_peer_feedback(message: Message, state: FSMContext):
    """Получили feedback - сохранили - просим оценку"""

    feedback = message.text.strip()
    data = await state.get_data()
    submission_id = data.get('submission_id')
    reviewer_id = data.get('student_id')  # В peer-to-peer ревьюер = студент

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("❌ Ошибка: сервис недоступен")
        await state.clear()
        return

    # Создаём запись о ревью
    if not sheets.add_review(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            feedback=feedback,
            score=-1  # Пока без оценки
    ):
        await message.answer("❌ Не удалось сохранить ревью")
        await state.clear()
        return

    # Сохраняем feedback в state
    await state.update_data(feedback=feedback)

    await message.answer(
        "📜**РЕВЬЮ СОХРАНЕНО**\n\n"
        "Теперь поставьте **оценку** работе.\n",
        parse_mode="Markdown"
    )

    await state.set_state(PeerReviewState.waiting_for_score)


@router.message(PeerReviewState.waiting_for_score, F.text)
async def handle_peer_score(message: Message, state: FSMContext):
    """Получили оценку - сохраняем - завершаем ревью"""

    score_text = message.text.strip()
    data = await state.get_data()
    submission_id = data.get('submission_id')
    reviewer_id = data.get('student_id')
    feedback = data.get('feedback', '')

    # Парсим оценку
    if not score_text.isdigit():
        await message.answer(
            "⚠️ Не удалось распознать оценку.\n\n"
            "Пожалуйста, отправьте **число**\n "
            "Или напишите /cancel чтобы отменить",
            parse_mode="Markdown"
        )
        return

    score = int(score_text)

    sheets = get_sheets_service()
    if not sheets:
        await message.answer("❌ Ошибка: сервис недоступен")
        await state.clear()
        return

    # Находим ID ревью
    review_id = sheets.get_review_id(submission_id, reviewer_id)

    if not review_id:
        await message.answer("❌ Не найдена запись о проверке")
        await state.clear()
        return

    # Обновляем оценку
    result = sheets.update_review(review_id=review_id, score=score)

    if result:
        await message.answer(
            f"✅ **РЕВЬЮ ЗАВЕРШЕНО!**\n\n"
            f"📝 Работа проверена\n"
            f"⭐ Ваша оценка: {score}\n"
            f"📄 Ревью: {feedback[:100]}{'...' if len(feedback) > 100 else ''}\n\n"
            f"Используйте /next2 чтобы проверить следующую работу.",
            parse_mode="Markdown"
        )
        logger.info(f"Студент {reviewer_id} проверил работу #{submission_id} (оценка: {score})")
    else:
        await message.answer("❌ Не удалось сохранить оценку")
        logger.error(f"Не удалось сохранить оценку для работы #{submission_id}")

    await state.clear()


@router.callback_query(F.data.startswith("peer_cancel_"))
async def cancel_peer_review(callback: CallbackQuery, state: FSMContext):
    """Отмена peer ревью через inline-кнопку (удаляет запись о проверке)"""

    try:
        submission_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    reviewer_id = callback.from_user.id
    sheets = get_sheets_service()

    if sheets:
        # Находим и удаляем запись о ревью
        review_id = sheets.get_review_id(submission_id, reviewer_id)
        if review_id:
            sheets.delete_review(review_id)
            logger.info(f"Review {review_id} удалена (студент {reviewer_id} отменил проверку)")

    await state.clear()

    try:
        await callback.message.delete()
    except:
        await callback.message.edit_text("❌ Проверка отменена")

    await callback.answer("❌ Отменено", show_alert=False)
    await callback.message.answer(
        "❌ **Проверка отменена.**\n\n"
        "Используйте /next2 чтобы взять работу заново.",
        parse_mode="Markdown"
    )


@router.message(Command("my_reviews2"))
async def cmd_my_reviews(message: Message):
    """Показать сколько работ студент уже проверил"""

    student_id = message.from_user.id
    sheets = get_sheets_service()

    if not sheets:
        await message.answer("⚠️ Сервис недоступен")
        return

    # Считаем количество ревью от этого студента
    reviews_worksheet = sheets.reviews_worksheet
    if not reviews_worksheet:
        await message.answer("❌ Ошибка доступа к таблице")
        return

    all_reviews = reviews_worksheet.get_all_records()
    my_reviews = [r for r in all_reviews if int(r.get('Reviewer_ID', 0)) == student_id]

    await message.answer(
        f"📊 **ВАША СТАТИСТИКА (Режим 2)**\n\n"
        f"Проверено работ: {len(my_reviews)}\n\n"
        f"Используйте /next2 чтобы проверить следующую работу.",
        parse_mode="Markdown"
    )