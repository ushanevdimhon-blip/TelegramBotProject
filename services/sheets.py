import gspread
from google.oauth2.service_account import Credentials
from gspread import worksheet

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
import logging

logger = logging.getLogger(__name__)

class SheetsService:
    """Сервис для работы с Google Таблицами"""

    def __init__(self):
        self._reviews_worksheet = None
        self._submissions_worksheet = None
        self._users_worksheet = None
        try:
            credentials = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH,
                scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
                ]
            )
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)
        except Exception as e:
            logger.error(f"Ошибка авторизации Google Sheets: {e}")

    def get_worksheet(self, worksheet_name: str):
        """Получить вкладку таблицы (лист) по названию"""
        try:
            return self.spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            logger.error(f"Лист '{worksheet_name}' не существует")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения листа {worksheet_name}: {e}")
            return None

    @property
    def users_worksheet(self):
        """Получение Users листа"""
        if self._users_worksheet is None:
            self._users_worksheet = self.get_worksheet('Users')
        return self._users_worksheet

    @property
    def submissions_worksheet(self):
        """Получение Submissions листа"""
        if self._submissions_worksheet is None:
            self._submissions_worksheet = self.get_worksheet('Submissions')
        return self._submissions_worksheet

    @property
    def reviews_worksheet(self):
        """Получение Reviews листа"""
        if self._reviews_worksheet is None:
            self._reviews_worksheet = self.get_worksheet('Reviews')
        return self._reviews_worksheet

    def add_user(self, telegram_id: int, username: str, role: str = 'student') -> bool:
        """Добавить пользователя в таблицу"""
        if self.users_worksheet is None:
            logger.error(f"self.users_worksheet is None")
            return False
        try:
            # Проверяем есть ли уже пользователь
            existing = self.get_user(telegram_id)
            if existing:
                logger.info(f"Пользователь {telegram_id} уже существует")
                return True

            # Добавляем нового
            from datetime import datetime
            self.users_worksheet.append_row([
                telegram_id,
                username,
                role,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
            logger.info(f"Пользователь {telegram_id} добавлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return False

    def get_user(self, telegram_id: int) -> dict | None:
        """Получить пользователя по Telegram ID"""
        if self.users_worksheet is None:
            logger.error(f"self.users_worksheet is None")
            return None
        try:
            all_records = self.users_worksheet.get_all_records()
            for record in all_records:
                if int(record.get('telegram_id', 0)) == telegram_id:
                    return record
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None

    @staticmethod
    def _generate_id(worksheet) -> int:
        """
        метод для генерации нового уникального ID.
        Берёт максимальное значение ID из первого столбца и прибавляет 1.
        Если записей ещё нет — возвращает 1.
        """
        rows = worksheet.get_all_values()
        if len(rows) > 1:
            existing_ids = [int(row[0]) for row in rows[1:] if row[0].isdigit()]
            return max(existing_ids) + 1 if existing_ids else 1
        else:
            return 1

    def add_submission(self, telegram_id: int=-1, student_name: str='', file_link: str='') -> bool:
        """
        Добавить submission по Telegram ID или по ФИО студента, также можно добавить ссылку на файл
        При добавлении чего-то одного нужно явно указать, что именно(student_name=...)
        """
        if (file_link != '' and file_link == -1 and student_name == '')  or (file_link == '' and file_link == -1 and student_name == ''):
            logger.error("Ошибка добавления submission: для добавления submission необходимо хотя бы указать"
                         "Telegram ID или по ФИО студента")
            return False
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return False
        try:
            submission_id = self._generate_id(self.submissions_worksheet)

            from datetime import datetime
            self.submissions_worksheet.append_row([
                submission_id,
                telegram_id,
                student_name,
                file_link,
                'not_solved',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
            logger.info(f"submission {submission_id} добавлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления submission: {e}")
            return False

    def get_submission(self, submission_id=None) -> dict | None:
        """
        Получить not_solved submission в порядке очереди,
        либо submission с любым статусом по id
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return None
        try:
            all_records = self.submissions_worksheet.get_all_records()
            if submission_id:
                for record in all_records:
                    if int(record.get('ID', 0)) == submission_id:
                        return record
            for record in all_records:
                if record.get('Status') == 'not_solved':
                    return record
        except Exception as e:
            logger.error(f"Ошибка получения submission: {e}")
            return None

    def update_submission(self, submission_id: int, file_link: str='', new_status: str='') -> bool:
        """
        Опционально обновить статус и/или file_link submission по ID.
        Для обновления чего-то одного необходимо явно указать, что именно(file_link=...).
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return False
        try:
            all_records = self.submissions_worksheet.get_all_records()
            row_index = None
            for i, record in enumerate(all_records):
                if int(record.get('ID', 0)) == submission_id:
                    row_index = i + 2
                    break

            if row_index is None:
                logger.error(f"Submission с ID {submission_id} не найдена")
                return False

            if new_status != '' and file_link != '':
                self.submissions_worksheet.update_cell(row_index, 5, new_status)  # 4 — индекс столбца "Status"
                self.submissions_worksheet.update_cell(row_index, 4, file_link)  # 3 — индекс столбца "File_link"
                logger.info(f"Status and File_link submission {submission_id} обновлёны")
            elif new_status != '':
                self.submissions_worksheet.update_cell(row_index, 5, new_status)
                logger.info(f"Status submission {submission_id} обновлён")
            elif file_link != '':
                self.submissions_worksheet.update_cell(row_index, 4, file_link)
                logger.info(f"Feedback submission {submission_id} обновлён")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления submission: {e}")
            return False

    def add_review(self, submission_id: int, reviewer_id: int) -> bool:
        """Добавить review по индексу submission и телеграм id проверяющего"""
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return False
        try:
            review_id = self._generate_id(self.reviews_worksheet)

            from datetime import datetime
            self.reviews_worksheet.append_row([
                review_id,
                submission_id,
                reviewer_id,
                '',
                -1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
            return True
        except Exception as e:
            logger.error(f"ошибка добавления review: {e}")
            return False

    def get_review(self, review_id: int) -> dict | None:
        """Получить review по его id"""
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return None
        try:
            all_records = self.reviews_worksheet.get_all_records()
            for record in all_records:
                if int(record.get('ID', 0)) == review_id:
                    return record
        except Exception as e:
            logger.error(f"Ошибка получения review: {e}")

    def update_review(self, review_id: int, feedback: str='', score: int=-1) -> bool:
        """
        Обновить либо feedback, либо score, либо и то и то.
        Для обновления чего-то одного необходимо явно указать что именно(feedback=...).
        """
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return False
        try:
            all_records = self.reviews_worksheet.get_all_records()
            row_index = None
            for i, record in enumerate(all_records):
                if int(record.get('ID', 0)) == review_id:
                    row_index = i + 2
                    break

            if row_index is None:
                logger.error(f"Review с ID {review_id} не найдена")
                return False

            if feedback != '' and score != -1:
                self.reviews_worksheet.update_cell(row_index, 4, feedback)  # 4 — индекс столбца "Feedback"
                self.reviews_worksheet.update_cell(row_index, 5, score)  # 5 — индекс столбца "Score"
                logger.info(f"Feedback and Score review с id={review_id} обновлёны")
            elif feedback != '':
                self.reviews_worksheet.update_cell(row_index, 4, feedback)
                logger.info(f"Feedback review с id={review_id} обновлён")
            elif score != -1:
                self.reviews_worksheet.update_cell(row_index, 5, score)
                logger.info(f"Score review с id={review_id} обновлён")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления review: {e}")
            return False




_sheets_service = None

def get_sheets_service() -> SheetsService | None:
    """Получить экземпляр сервиса"""
    global _sheets_service

    if _sheets_service is None:
        try:
            _sheets_service = SheetsService()
            logger.info("SheetsService инициализирован")
        except Exception as e:
            logger.error(f"Не удалось инициализировать SheetsService: {e}")
            return None

    return _sheets_service
