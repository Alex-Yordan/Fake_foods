import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Добавляем столбец image_url, если его нет
try:
    cursor.execute("ALTER TABLE menu ADD COLUMN image_url TEXT")
    conn.commit()
    print("✅ Столбец image_url добавлен в таблицу menu!")
except sqlite3.OperationalError:
    print("⚠ Столбец image_url уже существует!")

conn.close()
