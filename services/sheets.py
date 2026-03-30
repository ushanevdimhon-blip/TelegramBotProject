import gspread
from google.oauth2.service_account import Credentials
from gspread import worksheet

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
import logging

logger = logging.getLogger(__name__)

class SheetsService:
    """Сервис для работы с Google Таблицами"""

    def __init__(self):
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
            raise

    def get_worksheet(self, worksheet_name: str):
        """Получить вкладку таблицы (лист) по названию"""
        try:
            return self.spreadsheet.worksheet(worksheet_name)
        except Exception as e:
            logger.error(f"Ошибка получения листа {worksheet_name}: {e}")
            return None
        #Пример использования: worksheet = sheets.get_worksheet('users') - получить лист users

    def add_user(self, telegram_id: int, username: str, role: str = 'student') -> bool:
        """Добавить пользователя в таблицу Users"""
        try:
            worksheet = self.get_worksheet('Users')
            if not worksheet:
                return False

            # Проверяем есть ли уже пользователь
            existing = self.get_user(telegram_id)
            if existing:
                logger.info(f"Пользователь {telegram_id} уже существует")
                return True

            # Добавляем нового
            from datetime import datetime
            worksheet.append_row([
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
        try:
            worksheet = self.get_worksheet('Users')
            if not worksheet:
                return None

            all_records = worksheet.get_all_records()
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
        Приватный метод для генерации нового уникального ID.
        Берёт максимальное значение ID из первого столбца и прибавляет 1.
        Если записей ещё нет — возвращает 1.
        """
        rows = worksheet.get_all_values()
        if len(rows) > 1:
            existing_ids = [int(row[0]) for row in rows[1:] if row[0].isdigit()]
            return max(existing_ids) + 1 if existing_ids else 1
        else:
            return 1

    def add_submission(self, worksheet: str, telegram_id: int , submission_id: int | None, file_link: str, status='not_solved', time=None) -> bool:
        """Добавить submission по Telegram ID"""
        try:
            worksheet = self.get_worksheet(worksheet)
            if not worksheet:
                return False

            submission_id = self._generate_id(worksheet) if submission_id is None else submission_id

            from datetime import datetime

            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if time is None else time
            worksheet.append_row([
                submission_id,
                telegram_id,
                file_link,
                status,
                time
            ])
            logger.info(f"submission {submission_id} добавлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления submission: {e}")
            return False

    def get_submission(self, worksheet_name: str='Not_Solved_Submissions') -> dict | None:
        """Получить submission из очереди указанного листа"""
        try:
            worksheet = self.get_worksheet(worksheet_name)
            if not worksheet:
                return None
            all_records = worksheet.get_all_records()
            return all_records[0] if all_records else None
        except Exception as e:
            logger.error(f"Ошибка получения submission: {e}")
            return None

    def update_submission(self, old_worksheet_name, new_worksheet_name, record: dict, new_status: str) -> bool:
        """обновить статус submission и переместить в соответствующий статусу лист"""
        try:
            old_worksheet = self.get_worksheet(old_worksheet_name)
            cell = old_worksheet.find(str(record['ID']))

            if cell:
                #обновляем ячейку по ряду и колонке
                old_worksheet.update_cell(cell.row, 4, new_status)
                record['Status'] = new_status
                #проверяем соответствие листа и статуса
                if new_worksheet_name == 'In_Progress_Submissions' and record['Status'] == 'in_progress':
                    #добавляем строку в новый лист
                    self.add_submission(new_worksheet_name, record['Student_ID'],
                                        record['ID'], record['File_link'], record['Status'], record['Created_at'])
                    #удаляем строку из прошлого листа
                    old_worksheet.delete_rows(cell.row)
                elif new_worksheet_name == 'Done_Submissions' and record['Status'] == 'done':
                    # добавляем строку в новый лист
                    self.add_submission(new_worksheet_name, record['Student_ID'],
                                        record['ID'], record['File_link'], record['Status'], record['Created_at'])
                    # удаляем строку из прошлого листа
                    old_worksheet.delete_rows(cell.row)
                return True
            else:
                print(f"Submission ID {record['ID']} not found.")
                return False
        except Exception as e:
            print(f"Error updating submission {record['ID']}: {e}")
            return False

    # TODO: рефакторинг, добавить методы add/get и update для reviews



_sheets_service = None

def get_sheets_service() -> SheetsService | None:
    """Получить экземпляр сервиса (singleton)"""
    global _sheets_service

    if _sheets_service is None:
        try:
            _sheets_service = SheetsService()
            logger.info("SheetsService инициализирован")
        except Exception as e:
            logger.error(f"Не удалось инициализировать SheetsService: {e}")
            return None

    return _sheets_service
