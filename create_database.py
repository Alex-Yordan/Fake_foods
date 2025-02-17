import sqlite3

def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Таблица меню
    cursor.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image TEXT
    )''')

    # Таблица заказов
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'В обработке',
        total_price REAL NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Таблица позиций заказа
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        menu_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (menu_id) REFERENCES menu(id)
    )''')

    # Таблица отзывов
    cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        review_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Добавим тестовые данные в меню
    cursor.executemany('''INSERT INTO menu (name, category, description, price, image) 
                          VALUES (?, ?, ?, ?, ?)''', [
        ("Борщ", "Супы", "Традиционный украинский борщ", 250, "https://example.com/borsh.jpg"),
        ("Цезарь", "Салат", "Салат с курицей, сыром и соусом Цезарь", 300, "https://example.com/cezar.jpg"),
        ("Пицца Пепперони", "Второе", "Острая пицца с пепперони", 500, "https://example.com/pizza.jpg"),
        ("Лимонад", "Напиток", "Свежий лимонад", 150, "https://example.com/lemonade.jpg")
    ])

    conn.commit()
    conn.close()
    print("База данных создана и заполнена тестовыми данными.")

if __name__ == "__main__":
    create_database()
