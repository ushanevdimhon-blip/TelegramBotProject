from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from services.sheets import get_sheets_service
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("next"))
async def next_message(message: Message):
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
    student_name = submission.get("Student_name","Не указано")
    file_link = submission.get("File_link","Не указана")

    #TODO: Если другой эксперт пропускает работу, то из Reviews удаляется запись об этой работе (часть с реализацией inline кнопки _skip)

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
    if student_name:
        student_info += f"ФИО:  {student_name}\n"

    #TODO: прописать логику пропуска работ и добавления ревью (лучше inline кнопками)

    await message.answer(
        f"**НОВАЯ РАБОТА #{submission_id}**\n\n"
        f"{student_info}"
        f"Ссылка:  {file_link}\n"
        f"Статус:  `{status}`\n\n"
        f"Проверьте работу и отправьте обратную связь:",
        parse_mode="Markdown"
    )
