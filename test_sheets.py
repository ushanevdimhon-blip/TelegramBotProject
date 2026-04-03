import random
from services.sheets import get_sheets_service



ALPHABET = "abcdefghijklmnopqrstuvwxyz"


print("\n" + "=" * 40)
print("БАЗОВЫЕ ТЕСТЫ GOOGLE SHEETS")
print("=" * 40 + "\n")

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Подключение
# ─────────────────────────────────────────────────────────────
print("1. Подключение к Google Sheets...")
sheets = get_sheets_service()

if sheets:
    print("   ✅ Сервис инициализирован")
else:
    print("   ❌ Сервис не инициализирован")
    exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Таблица открыта
# ─────────────────────────────────────────────────────────────
print("2. Проверка таблицы...")
try:
    print(f"   ✅ Таблица: {sheets.spreadsheet.title}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Добавить пользователя
# ─────────────────────────────────────────────────────────────
print("4. Добавление тестового пользователя...")
users_id = []
for i in range(3):
    test_id = random.randint(1, 100)
    test_name = ALPHABET[random.randint(0, len(ALPHABET) - 1)] + "_test"

    result = sheets.add_user(test_id, test_name)
    if result:
        print(f"   ✅ Пользователь {test_id} добавлен/обновлён")
        users_id.append(test_id)
    else:
        print(f"   ❌ Не удалось добавить")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Получить пользователя
# ─────────────────────────────────────────────────────────────
print("5. Получение пользователя...")
for id in users_id:
    user = sheets.get_user(id)

    if user:
        print(f"   ✅ Пользователь найден: {user}")
    else:
        print(f"   ❌ Пользователь не найден")
        exit(1)


# ─────────────────────────────────────────────────────────────
# ТЕСТ: Добавить submission по тг id
# ─────────────────────────────────────────────────────────────
print("6. Добавление тестовых submission...")
test_id = []
for i in range(3):
    test_id.append(random.randint(1, 100))
for id in test_id:
    result = sheets.add_submission(id)
    if result:
        print(f"   ✅ Submission добавлен: submission__id={id}")
    else:
        print(f"   ❌ Не удалось добавить submission для submission__id={id}")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Добавить submission по ФИО студента и ссылки на файл
# ─────────────────────────────────────────────────────────────
print("7. Добавление тестовых submission...")
test_id = []
for i in range(4):
    test_id.append(random.randint(1, 100))
for id in test_id:
    result = sheets.add_submission(student_name=f"test_name{id}", file_link="https://example.com/submissions")
    if result:
        print(f"   ✅ Submission добавлен: submission__id={id}")
    else:
        print(f"   ❌ Не удалось добавить submission для submission__id={id}")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Получить и обновить submission
# ─────────────────────────────────────────────────────────────
print("8. Получение и обновление тестовых submission...")

for id in test_id[:2]:
    file_link = "https://example.com/submissions"
    record = sheets.get_submission()
    result = sheets.update_submission(record['ID'], new_status='in_progress')
    if result:
        print(f"   ✅ Submission получен и обновлен: {result}")
    else:
        print(f"   ❌ Не удалось получить submission")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Добавить review
# ─────────────────────────────────────────────────────────────
print("9. Добавление тестовых review...")
test_id = []
for i in range(7):
    test_id.append(random.randint(1, 100))

for id in test_id:
    result = sheets.add_review(id, id + 1)
    if result:
        print(f"   ✅ review добавлен: review_id={id}")
    else:
        print(f"   ❌ Не удалось добавить review для review_id={id}")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Получить review
# ─────────────────────────────────────────────────────────────
print("10. Получение тестовых review...")
for i in range(4):
    record = sheets.get_review(random.randint(1, 7))
    if record:
        print(f"   ✅ review получен: id={record}")
    else:
        print(f"   ❌ Не удалось получить review для review_id={i}")
        exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Обновить review
# ─────────────────────────────────────────────────────────────
print("11. Обновление тестовых review...")
for i in range(4):
    record = sheets.get_review(random.randint(1, 7))
    result = sheets.update_review(record["ID"], 'feedback', 100)
    if record:
        print(f"   ✅ review обновлен: {record}")
    else:
        print(f"   ❌ Не удалось обновить review для review_id={i}")
        exit(1)

print("\n" + "=" * 40)
print("Тесты пройдены")
print("=" * 40 + "\n")
