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
    print("   ✅ Сервис подключён")
else:
    print("   ❌ Сервис НЕ подключён")
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
# ТЕСТ: Лист Users существует
# ─────────────────────────────────────────────────────────────
print("3. Проверка листа Users...")
worksheet = sheets.get_worksheet('Users')

if worksheet:
    print(f"   ✅ Лист найден: {worksheet.title}")
else:
    print("   ❌ Лист не найден (создай лист 'Users' в таблице)")
    exit(1)

# ─────────────────────────────────────────────────────────────
# ТЕСТ: Добавить пользователя
# ─────────────────────────────────────────────────────────────
print("4. Добавление тестового пользователя...")
users_id = []
for i in range(10):
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

print("\n" + "=" * 40)
print("Тесты пройдены")
print("=" * 40 + "\n")