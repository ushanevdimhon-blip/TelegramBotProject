import gspread
from google.oauth2.service_account import Credentials
from gspread import worksheet
from pip._internal.operations import check

from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
import logging

logger = logging.getLogger(__name__)

class SheetsService:    #возможно стоит сделать асинхронным - вызовы в отдельном потоке
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

    def add_user(self, telegram_id: int, username: str, user_full_name: str, role: str = '') -> bool:
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
                user_full_name,
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

    #TODO: рефакторинг: добавить подписи методам, изменить уже существующие: params & returns
    # ?возможно надо добавить разброс оценок
    # ?возможно стоит добавить увеличивать number_of_reviewers и для первого режима

    def get_aggregated_result(self, telegram_id: int, n: int) -> list | bool:
        """
        Ищет подходящие N review, удаляет их из листа review, вычисляет
        средний балл и формирует список result из словарей результатов
        :param telegram_id: id студента
        :param n: число N для второго режима, задаваемое организатором
        :return: bool и список словарей результатов
        """
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return False
        if not self.check(telegram_id, n):
            logger.error(f"check failed: {telegram_id}")
            return False
        submission_id = self.get_submission_id(telegram_id)
        scores = []
        reviewers = []
        feedbacks = []
        rows_to_delete = []
        result = []
        try:
            cells = self.reviews_worksheet.findall(str(submission_id), in_column=2)
            for cell in cells:
                scores.append(int(str(self.reviews_worksheet.cell(cell.row, 5).value)))
                reviewers.append(str(self.reviews_worksheet.cell(cell.row, 3).value))
                feedbacks.append(str(self.reviews_worksheet.cell(cell.row, 4).value))
                rows_to_delete.append(cell.row)
            middle_score = sum(scores) / len(scores)
            for i in range(0,n):
                result.append({
                    "Reviewer_ID": reviewers[i],
                    "Student_ID": telegram_id,
                    "Feedback": feedbacks[i],
                    "Score": scores[i],
                    "Middle_score": middle_score
                    }
                )
            for row in sorted(rows_to_delete, reverse=True):
                self.reviews_worksheet.delete_rows(row)
            return result
        except Exception as e:
            logger.error(f"Не удалось получить: {e}")
            return False

    def check(self, telegram_id: int, n: int) -> bool:
        """
        Находит все подходящие review по тг id и проверяет равно ли количество готовых review N
        :param telegram_id: id студента
        :param n: число N для второго режима, задаваемое организатором
        :return: bool
        """
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return False
        try:
            submission_id = self.get_submission_id(telegram_id)
            cells = self.reviews_worksheet.findall(str(submission_id), in_column=2)
            if len(cells) != n: return False
            for cell in cells:
                review_id = self.reviews_worksheet.cell(cell.row, 1).value
                review = self.get_review(int(review_id))
                if review["Feedback"] == "none" or review["Score"] == "-1":
                    return False
            return True
        except Exception as e:
            logger.error(f"Не удалось проверить: {e}")
            return False

    def add_submission(self, telegram_id: int, student_name: str, file_link: str) -> bool:
        """
        Добавить submission по Telegram ID, по ФИО студента и ссылки на файл
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return False
        try:
            submission_id = self._generate_id(self.submissions_worksheet)
            status = "redacting"

            if student_name != '' and file_link != '':
                status = "not_solved"

            from datetime import datetime
            self.submissions_worksheet.append_row([
                submission_id,
                telegram_id,
                student_name,
                file_link,
                status,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                0
            ])
            logger.info(f"submission {submission_id} добавлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления submission: {e}")
            return False

    def get_submission_id(self, telegram_id: int) -> int | None:
        """Получить submission ID по telegram ID"""
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return None
        try:
            cell = self.submissions_worksheet.find(str(telegram_id), in_column=2)
            if cell is not None:
                submission_id_cell = self.submissions_worksheet.cell(cell.row, 1)
                return int(str(submission_id_cell.value))
            else:
                logger.info(f"Telegram ID {telegram_id} не найден")
                return None
        except Exception as e:
            logger.error(f"Ошибка получения submission_id: {e}")

    #стоит разделить на 2 метода для получения в порядке очереди и для получения по id, чтобы не менять статус
    #при получении по id
    def get_submission(self, submission_id=None) -> dict | None:
        """
        Получить not_solved submission в порядке очереди,
        либо submission с любым статусом по id.
        Меняет статус на in_progress
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return None
        try:
            all_records = self.submissions_worksheet.get_all_records()
            if submission_id:
                for record in all_records:
                    if int(record.get('ID', 0)) == submission_id:
                        self.update_submission(submission_id, new_status='in_progress')
                        record['Status'] = 'in_progress'
                        return record
            for record in all_records:
                if record.get('Status') == 'not_solved':
                    self.update_submission(record.get('ID'), new_status='in_progress')
                    record['Status'] = 'in_progress'
                    return record
        except Exception as e:
            logger.error(f"Ошибка получения submission: {e}")
            return None

    def get_submission_by_id(self, submission_id: int) -> dict | None:
        """
            Получить submission по id.
            Не меняет статус
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return None
        try:
            all_records = self.submissions_worksheet.get_all_records()
            for record in all_records:
                if int(record.get('ID', 0)) == submission_id:
                    return record
        except Exception as e:
            logger.error(f"Ошибка получения submission по id: {e}")

    # возможно стоит убрать логику обновления number_of_reviewers
    # просто проходится по записям и сравнивать n
    def get_n_submissions(self, asker_tg_id: int, n: int) -> list | None:
        """
        Получить n-ное количество работ, при нехватке работ возвращается список из тех, что есть
        :param asker_tg_id: tg id студента, от которого идет запрос на получение
        :param n: количество работ
        :return: список из n submissions
        """
        if self.submissions_worksheet is None:
            logger.error(f"self.submissions_worksheet is None")
            return None
        try:
            all_records = self.submissions_worksheet.get_all_records()
            submissions = []
            row_index = 1
            count = 0
            for record in all_records:
                row_index += 1
                number_of_reviewers = int(str(record.get("Number_of_reviewers")))
                student_id = int(str(record.get("Student_ID")))
                if number_of_reviewers == n or student_id == asker_tg_id or str(record.get("Status")=='redacting'):
                    continue
                count += 1
                if count > n:
                    break
                self.submissions_worksheet.update_cell(row_index, 7, number_of_reviewers + 1)
                submissions.append(record)
            return submissions
        except Exception as e:
            logger.error(f"Не удалось получить {n} submissions для {asker_tg_id}: {e}")
            return None

    def update_submission(self, submission_id: int, file_link: str='', new_status: str='', n_of_rev: int=0) -> bool:
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

            if new_status != '':
                self.submissions_worksheet.update_cell(row_index, 5, new_status)
                logger.info(f"Status submission {submission_id} обновлён")
            if file_link != '':
                self.submissions_worksheet.update_cell(row_index, 4, file_link)
                logger.info(f"Feedback submission {submission_id} обновлён")
            if n_of_rev != 0:
                self.submissions_worksheet.update_cell(row_index, 7, n_of_rev)
                logger.info(f"n_of_rev submission {submission_id} обновлён")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления submission: {e}")
            return False

    def add_review(self, submission_id: int, reviewer_id: int, feedback: str='none', score: int=-1) -> bool:
        """Добавить review"""
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
                feedback,
                score,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
            return True
        except Exception as e:
            logger.error(f"ошибка добавления review: {e}")
            return False

    def get_review_id(self, submission_id: int, reviewer_id: int=None) -> int | None:
        """Получить ID review по submission ID или по submission ID и ID проверяющего"""
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return None
        try:
            rows = self.reviews_worksheet.get_all_records()

            for row in rows:
                if row.get('Submission_ID') == submission_id:
                    if reviewer_id is not None:
                        if row.get('Reviewer_ID') == reviewer_id:
                            return int(str(row.get('ID')))
                        continue
                    else:
                        return int(str(row.get('ID')))
            return None
        except Exception as e:
            logger.error(f"Error while getting review_id: {e}")
            return None

    def get_review(self, review_id: int) -> dict | None:
        """Получить review по его id или по submission id"""
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

    # возможно стоит убрать логику обновления number_of_reviewers
    def delete_review(self, review_id: int) -> bool:
        if self.reviews_worksheet is None:
            logger.error(f"self.reviews_worksheet is None")
            return False
        try:
            cell = self.reviews_worksheet.find(str(review_id), in_column=1)
            subm_id = self.reviews_worksheet.cell(cell.row, 2).value
            subm = self.get_submission(int(subm_id))
            self.update_submission(int(subm_id), n_of_rev=(subm["Number_of_reviewers"]) - 1)
            self.reviews_worksheet.delete_rows(cell.row)
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления review: {e}")
            return False

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

            if feedback != '':
                self.reviews_worksheet.update_cell(row_index, 4, feedback)
                logger.info(f"Feedback review с id={review_id} обновлён")
            if score != -1:
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
