import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
import logging

logger = logging.getLogger(__name__)

class SheetsService:
    """Сервис для работы с Google Таблицами"""

    def __init__(self):
        """Инициализация подключения к Google Sheets"""
        self.client = self._authenticate() #Подключение к sheets
        self.spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID) #открывает нужную таблицу

    def _authenticate(self):
        """Авторизация в Google API"""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ] #Что именно мы подключаем

        try:
            credentials = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_PATH,
                scopes=scopes
            )
            return gspread.authorize(credentials) #Авторизованый клиент
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


_sheets_service = None


def get_sheets_service() -> SheetsService | None:
    """Получить экземпляр сервиса (singleton)"""
    global _sheets_service

    if _sheets_service is None:
        try:
            _sheets_service = SheetsService()
            logger.info("✅ SheetsService инициализирован")
        except Exception as e:
            logger.error(f"❌ Не удалось инициализировать SheetsService: {e}")
            return None

    return _sheets_service
