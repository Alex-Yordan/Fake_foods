import sqlite3

def update_database(db_path="database.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Удаляем таблицы, которые нужно пересоздать
    cursor.execute("DROP TABLE IF EXISTS cart")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS customers")

    # ВАЖНО: таблицу menu НЕ трогаем и НЕ удаляем, чтобы сохранить данные!

    # Создаём таблицу customers (только id и user_id)
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL
        )
    """)

    # Создаём таблицу orders
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            name TEXT,
            phone TEXT,
            review TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # Создаём таблицу cart
    cursor.execute("""
        CREATE TABLE cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dish_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (dish_id) REFERENCES menu(id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_database("database.db")
    print("База данных успешно обновлена!\n"
          "Таблица menu сохранена, а таблицы customers, orders, cart пересозданы.")
