from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from services.sheets import get_sheets_service
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("check_status"))
async def cmd_check1(message: Message):
    """
    Проверка статуса своей работы.
    Показывает: ID, ссылку, статус, и, если проверено - feedback и score.
    """

    student_id = message.from_user.id
    sheets = get_sheets_service()

    if not sheets:
        await message.answer("⚠️ Сервис временно недоступен, попробуйте позже")
        return

    submission_id = sheets.get_submission_id(student_id)
    if not submission_id:
        await message.answer(
            "У вас ещё нет работ в системе.\n\n"
            "Используйте /submit чтобы загрузить работу."
        )
        return

    submission = sheets.get_submission_by_id(submission_id)
    if not submission:
        await message.answer("❌ Не удалось получить информацию о работе")
        return

    file_link = submission.get("File_link")
    status = submission.get("Status")
    number_of_reviewers = int(str(submission.get("Number_of_reviewers", 0)))

    status_display = {
        "not_solved": "⏳ В очереди на проверку",
        "in_progress": "🔍 На проверке",
        "solved": "✅ Проверено",
        "redacting": "📝 Черновик"
    }.get(status, f"Неизвестный статус ({status})")

    reviews = get_reviews_for_submission(sheets, submission_id)

    text = (
        f"📋 **СТАТУС ВАШЕЙ РАБОТЫ**\n\n"
        f"📝 ID работы: `#{submission_id}`\n"
        f"🔗 Ссылка: `{file_link}`\n"
        f"📊 Статус: {status_display}\n"
        f"👥 Проверок: {number_of_reviewers}\n\n"
    )

    if reviews and len(reviews) > 0:
        # ОПРЕДЕЛЯЕМ РЕЖИМ ПО КОЛИЧЕСТВУ РЕВЬЮ
        if len(reviews) == 1:
            # 1 РЕВЬЮ - ПЕРВЫЙ РЕЖИМ
            review = reviews[0]
            feedback = review.get("Feedback", "Нет текста")
            score = review.get("Score", "-1")

            text += "📄 **ОБРАТНАЯ СВЯЗЬ**:\n\n"

            if score and score != "-1":
                text += f"⭐ Оценка: {score}\n"

            if feedback and feedback != "none":
                text += f"📝 Ревью: {feedback}\n"
            else:
                text += "⏳ Ревью ещё не заполнено\n"

        else:
            # 2 РЕЖИМ
            scores = []
            text += f"📄 **ОБРАТНАЯ СВЯЗЬ** ({len(reviews)} проверок):\n\n"

            for i, review in enumerate(reviews, 1):
                feedback = review.get("Feedback", "Нет текста")
                score = review.get("Score", "-1")

                # Собираем оценки для среднего
                if score and score != "-1":
                    try:
                        scores.append(int(score))
                    except ValueError:
                        pass

                # Показываем каждое ревью
                text += f"**Проверка #{i}**\n"

                if score and score != "-1":
                    text += f"⭐ Оценка: {score}\n"

                if feedback and feedback != "none":
                    # Обрезаем слишком длинные отзывы
                    feedback_text = feedback[:150] + ('...' if len(feedback) > 150 else '')
                    text += f"📝 Ревью: {feedback_text}\n"

                text += "\n"

            # Средний бал для второго режима
            if scores:
                average_score = sum(scores) / len(scores)
                text += (
                    f"📊 **СРЕДНИЙ БАЛЛ: {average_score:.2f}**\n\n"
                )
    else:
        text += "⏳ Работа проверяется, обратная связь скоро появится.\n\n"

    text += (
        "\n"
        "Используйте /help чтобы посмотреть другие команды"
    )

    await message.answer(text, parse_mode="Markdown")


def get_reviews_for_submission(sheets, submission_id: int) -> list:
    """
    Получить все ревью для работы.
    :param sheets: экземпляр SheetsService
    :param submission_id: ID работы
    :return: список ревью
    """
    try:
        reviews_worksheet = sheets.reviews_worksheet
        if not reviews_worksheet:
            return []

        all_reviews = reviews_worksheet.get_all_records()
        submission_reviews = []

        for review in all_reviews:
            review_submission_id_raw = review.get("Submission_ID", 0)

            try:
                review_submission_id = int(str(review_submission_id_raw)) if review_submission_id_raw else 0
            except (ValueError, TypeError):
                continue

            if review_submission_id == submission_id:
                submission_reviews.append({
                    "Feedback": review.get("Feedback", "Нет текста"),
                    "Score": review.get("Score", "-1"),
                    "Reviewer_ID": review.get("Reviewer_ID", "unknown"),
                    "Created_at": review.get("Created_at", "")
                })

        return submission_reviews
    except Exception as e:
        logger.error(f"Ошибка получения ревью для submission_id:{submission_id}: {e}")
        return []