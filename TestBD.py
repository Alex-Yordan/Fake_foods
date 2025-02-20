import sqlite3


def analyze_database(db_path):
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Извлечение списка всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    result = []

    # Для каждой таблицы извлекаем структуру и данные
    for table in tables:
        table_name = table[0]
        result.append(f"Таблица: {table_name}\n")

        # Получение информации о столбцах таблицы
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        result.append(f"Столбцы: {', '.join(column_names)}\n")

        # Получение всех данных из таблицы
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        if rows:
            result.append(f"Данные: \n")
            for row in rows:
                result.append(f"{row}\n")
        else:
            result.append("Данные отсутствуют.\n")

        result.append("\n" + "-" * 40 + "\n")

    # Закрытие подключения
    conn.close()

    return "\n".join(result)


# Пример использования
db_path = "database.db"
database_info = analyze_database(db_path)

# Выводим информацию
print(database_info)
