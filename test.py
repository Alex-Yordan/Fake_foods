import sqlite3


def update_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Создание новой таблицы с автоинкрементным order_number
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        total_price REAL NOT NULL DEFAULT 0,  -- Устанавливаем дефолтное значение 0
        order_number INTEGER UNIQUE
    )""")

    # Вставляем данные только тех заказов, у которых total_price не NULL
    cursor.execute("""
    INSERT INTO orders_new (user_id, name, phone, total_price)
    SELECT user_id, name, phone, total_price 
    FROM orders 
    WHERE total_price IS NOT NULL
    """)

    # Удаление старой таблицы
    cursor.execute("DROP TABLE orders")

    # Переименование новой таблицы в orders
    cursor.execute("ALTER TABLE orders_new RENAME TO orders")

    # Применяем изменения
    conn.commit()
    conn.close()


# Запуск функции для обновления базы данных
update_database()
