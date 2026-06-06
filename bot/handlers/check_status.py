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

    #ID стикера можно менять
    loading_message = await message.answer_sticker(
        sticker = "CAACAgIAAxkBAAEEUVVqHrGEn3W-h2ewC56tOzoOhWEO_gACRAEAAs0bMAh9vsuIBiz2FjsE")

    submission_id = sheets.get_submission_id(student_id)
    if not submission_id:
        await loading_message.delete() #Эту команду использовать при каждом ответе - чтобы сообщение о загрузке удалялось
        await message.answer(
            "У вас ещё нет работ в системе.\n\n"
            "Используйте /submit чтобы загрузить работу."
        )
        return

    submission = sheets.get_submission_by_id(submission_id)
    if not submission:
        await loading_message.delete()
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

    text = (
        f"📋 **СТАТУС ВАШЕЙ РАБОТЫ**\n\n"
        f"📝 ID работы: `#{submission_id}`\n"
        f"🔗 Ссылка: `{file_link}`\n"
        f"📊 Статус: {status_display}\n"
        f"👥 Проверок: {number_of_reviewers}\n\n"
    )

    aggregated_results = sheets.get_aggregated_result(student_id)

    # если есть агрегированные результаты
    if aggregated_results and len(aggregated_results) > 0:

        text += (
            f"🎉 **РАБОТА ПРОВЕРЕНА!**\n\n"
            f"📄 **ОБРАТНАЯ СВЯЗЬ** ({len(aggregated_results)} проверок):\n\n"
        )

        scores = []
        for i, result in enumerate(aggregated_results, 1):
            feedback = result.get("Feedback", "Нет текста")
            score = result.get("Score", "-1")

            if score and score != "-1":
                try:
                    scores.append(int(score))
                except ValueError:
                    pass

            text += f"**Проверка #{i}**\n"

            if score and score != "-1":
                text += f"⭐ Оценка: {score}\n"

            if feedback and feedback != "none":
                feedback_text = feedback[:150] + ('...' if len(feedback) > 150 else '')
                text += f"📝 Ревью: {feedback_text}\n"

            text += "\n"

        if scores:
            average_score = sum(scores) / len(scores)
            text += (
                f"📊 **СРЕДНИЙ БАЛЛ: {average_score:.2f}**\n"
            )

        text += "Ревью сохранены в таблице с обновлённым средним баллом.\n"

        # Если нет агрег.рез. Показываем текущие
    else:
        reviews = sheets.get_reviews_for_submission(submission_id)

        if reviews and len(reviews) > 0:
            text += f"📄 **ОБРАТНАЯ СВЯЗЬ** ({len(reviews)} проверок):\n\n"

            for i, review in enumerate(reviews, 1):
                feedback = review.get("Feedback", "Нет текста")
                score = review.get("Score", "-1")

                text += f"**Проверка #{i}**\n"

                if score and score != "-1":
                    text += f"⭐ Оценка: {score}\n"

                if feedback and feedback != "none":
                    feedback_text = feedback[:150] + ('...' if len(feedback) > 150 else '')
                    text += f"📝 Ревью: {feedback_text}\n"

                text += "\n"

            text += "⏳Ожидаются остальные проверки...\n\n"
        else:
            text += "⏳ Работа проверяется, обратная связь скоро появится.\n\n"

    text += "\nИспользуйте /help чтобы посмотреть другие команды"

    await loading_message.delete()

    await message.answer(text, parse_mode="Markdown")

