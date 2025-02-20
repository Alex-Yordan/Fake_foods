import os
import sqlite3
import telebot
from telebot import types
import time
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
IMAGE_FOLDER = "images"

# Глобальный словарь для хранения текущего заказа пользователя (order_id)
current_order = {}

# Глобальная переменная для пагинации отзывов
reviews_page = {}

# Создание таблиц, если их нет (таблица menu остаётся неизменённой)
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dish_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (dish_id) REFERENCES menu(id)
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        name TEXT,
        phone TEXT,
        review TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
""")
conn.commit()
conn.close()


def check_category_exists(category):
    """Проверяет, существует ли категория в меню"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu WHERE category = ?", (category,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


@bot.message_handler(commands=['start'])
def start(message):
    """Отправляем кнопки 'Старт' и 'Отзывы наших клиентов'"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_btn = types.KeyboardButton("Старт")
    reviews_btn = types.KeyboardButton("Отзывы наших клиентов")
    keyboard.add(start_btn, reviews_btn)
    bot.send_message(
        message.chat.id,
        "Привет! Добро пожаловать в сервис заказа еды. Нажмите 'Старт', чтобы начать.",
        reply_markup=keyboard
    )


@bot.message_handler(func=lambda message: message.text == "Старт")
def handle_start(message):
    """Удаляем кнопку 'Старт' и начинаем работу"""
    user_id = message.chat.id
    bot.delete_message(user_id, message.message_id)
    show_categories(message)


@bot.message_handler(func=lambda message: message.text == "Отзывы наших клиентов")
def handle_reviews(message):
    """Выводит отзывы клиентов с пагинацией"""
    user_id = message.chat.id

    # Устанавливаем страницу отзывов для пользователя, если не установлена
    if user_id not in reviews_page:
        reviews_page[user_id] = 0

    # Загружаем 5 отзывов
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.name, o.review
        FROM orders o
        WHERE o.review IS NOT NULL
        ORDER BY o.id DESC
        LIMIT 5 OFFSET ?
    """, (reviews_page[user_id] * 5,))
    reviews = cursor.fetchall()
    conn.close()

    if reviews:
        response = "Отзывы наших клиентов:\n\n"
        for i, (name, review) in enumerate(reviews, 1):
            response += f"{i}. {name} - {review}\n"

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Далее", callback_data="next_reviews"))
        bot.send_message(user_id, response, reply_markup=keyboard)
    else:
        bot.send_message(user_id, "Нет доступных отзывов.")

@bot.callback_query_handler(func=lambda call: call.data == "next_reviews")
def load_next_reviews(call):
    """Загружает следующие 5 отзывов"""
    user_id = call.message.chat.id

    # Увеличиваем номер страницы отзывов
    reviews_page[user_id] += 1

    # Загружаем 5 отзывов
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.name, o.review
        FROM orders o
        WHERE o.review IS NOT NULL
        ORDER BY o.id DESC
        LIMIT 5 OFFSET ?
    """, (reviews_page[user_id] * 5,))
    reviews = cursor.fetchall()
    conn.close()

    if reviews:
        response = "Отзывы наших клиентов:\n\n"
        for i, (name, review) in enumerate(reviews, 1):
            response += f"{i}. {name} - {review}\n"

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Далее", callback_data="next_reviews"))
        bot.edit_message_text(response, chat_id=user_id, message_id=call.message.message_id, reply_markup=keyboard)
    else:
        bot.edit_message_text("Больше отзывов нет.", chat_id=user_id, message_id=call.message.message_id)


def show_categories(message):
    """Отображает список категорий в InlineKeyboard"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()
    conn.close()

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for category in categories:
        keyboard.add(types.InlineKeyboardButton(category[0], callback_data=category[0]))

    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)


@bot.callback_query_handler(
    func=lambda call: call.data in [
        c[0] for c in sqlite3.connect("database.db").cursor()
        .execute("SELECT DISTINCT category FROM menu").fetchall()
    ]
)
def show_dishes(call):
    """Отображает блюда из выбранной категории"""
    category = call.data
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, price, image_url FROM menu WHERE category = ?", (category,))
    dishes = cursor.fetchall()
    conn.close()

    if dishes:
        for dish in dishes:
            dish_name, description, price, image_filename = dish
            image_path = os.path.join(IMAGE_FOLDER, image_filename)
            response = f"*{dish_name}*\n_{description}_\n💰 Цена: {price} ₽"
            if os.path.exists(image_path):
                with open(image_path, "rb") as photo:
                    bot.send_photo(call.message.chat.id, photo, caption=response, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

            # Кнопки выбора количества
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("🍽️ 1", callback_data=f"{dish_name}-1"),
                types.InlineKeyboardButton("🍽️🍽️ 2", callback_data=f"{dish_name}-2"),
                types.InlineKeyboardButton("🍽️🍽️🍽️ 3", callback_data=f"{dish_name}-3")
            )
            bot.send_message(call.message.chat.id, "Выберите количество:", reply_markup=keyboard)

        bottom_keyboard = types.InlineKeyboardMarkup()
        bottom_keyboard.add(
            types.InlineKeyboardButton("🛒 Корзина", callback_data="cart"),
            types.InlineKeyboardButton("💳 Оплатить", callback_data="pay"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories")
        )
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=bottom_keyboard)
    else:
        bot.send_message(call.message.chat.id, "В этой категории пока нет блюд.")


@bot.callback_query_handler(func=lambda call: call.data == "cart")
def show_cart(call):
    """Отображает содержимое корзины с возможностью удаления и очистки корзины"""
    user_id = call.message.chat.id
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT menu.name, menu.price, cart.quantity, cart.id
        FROM cart
        JOIN menu ON cart.dish_id = menu.id
        WHERE cart.user_id = ?
    """, (user_id,))
    cart_items = cursor.fetchall()
    conn.close()

    if not cart_items:
        bot.send_message(user_id, "Ваша корзина пуста.")
        return

    total_price = sum(item[2] * item[1] for item in cart_items)
    response = (
        "🛒 *Ваша корзина:*\n\n"
        "🔔 Нажав на кнопку с названием блюда, вы удалите его из корзины.\n\n"
    )
    keyboard = types.InlineKeyboardMarkup()
    for name, price, quantity, cart_id in cart_items:
        dish_text = f"{name} - {quantity} шт. (💰 {price} ₽ за шт.) = {price * quantity} ₽"
        keyboard.add(types.InlineKeyboardButton(dish_text, callback_data=f"remove_{cart_id}"))

    response += f"\n💰 *Итого: {total_price} ₽*"
    keyboard.add(types.InlineKeyboardButton("🧹 Очистить корзину", callback_data="clear_cart"))
    keyboard.add(types.InlineKeyboardButton("💳 Оплатить", callback_data="pay"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories"))
    bot.send_message(user_id, response, parse_mode="Markdown", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def back_to_categories(call):
    """Возвращает к выбору категорий"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_categories(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_"))
def remove_from_cart(call):
    """Удаляет элемент из корзины"""
    cart_id = int(call.data.split("_")[1])
    user_id = call.message.chat.id
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "Блюдо удалено из корзины.")
    show_cart(call)


@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def clear_cart(call):
    """Очищает корзину пользователя"""
    user_id = call.message.chat.id
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "Корзина очищена.")
    show_cart(call)


@bot.callback_query_handler(func=lambda call: '-' in call.data)
def add_to_cart(call):
    """Добавляет блюдо в корзину"""
    try:
        dish_name, quantity = call.data.split("-")
        quantity = int(quantity)
    except ValueError:
        bot.answer_callback_query(call.id, "Ошибка добавления в корзину. Попробуйте снова.")
        return

    user_id = call.message.chat.id
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, price FROM menu WHERE name = ?", (dish_name,))
    dish = cursor.fetchone()
    conn.close()

    if dish:
        dish_id, price = dish
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cart (user_id, dish_id, quantity)
            VALUES (?, ?, ?)
        """, (user_id, dish_id, quantity))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, f"Блюдо {dish_name} добавлено в корзину ({quantity} шт.).")
        show_cart(call)
    else:
        bot.answer_callback_query(call.id, f"Блюдо {dish_name} не найдено.")


@bot.callback_query_handler(func=lambda call: call.data == "pay")
def start_payment(call):
    """
    Запрашиваем имя и телефон для оформления заказа
    Но перед этим проверяем, есть ли блюда в корзине
    """
    user_id = call.message.chat.id

    # Проверка, пуста ли корзина
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
    count_cart = cursor.fetchone()[0]
    conn.close()

    if count_cart == 0:
        bot.send_message(user_id, "Ваша корзина пуста, оплата не требуется.")
        return

    # Иначе продолжаем оформлять заказ
    bot.send_message(user_id, "Для оформления заказа, введите ваше имя.")
    bot.register_next_step_handler(call.message, get_name)


def get_name(message):
    """Получает имя клиента и создает новый заказ в таблице orders"""
    user_id = message.chat.id
    name = message.text

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO customers (user_id) VALUES (?)", (user_id,))
    customer_id = cursor.lastrowid
    conn.commit()

    conn.close()

    bot.send_message(user_id, "Теперь введите ваш номер телефона.")
    bot.register_next_step_handler(message, get_phone, customer_id)


def get_phone(message, customer_id):
    """Получает телефон клиента и создает заказ"""
    phone = message.text

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (customer_id, name, phone)
        VALUES (?, ?, ?)
    """, (customer_id, message.text, phone))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "Ваш заказ оформлен. Благодарим за покупку!")
    bot.send_message(message.chat.id, "Вы можете оставить отзыв о заказе. Напишите его, пожалуйста.")

    bot.register_next_step_handler(message, save_review)


def save_review(message):
    """Сохраняет отзыв о заказе"""
    user_id = message.chat.id
    review = message.text

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders
        SET review = ?
        WHERE customer_id = (SELECT id FROM customers WHERE user_id = ?)
        ORDER BY id DESC LIMIT 1
    """, (review, user_id))
    conn.commit()
    conn.close()

    bot.send_message(user_id, "Спасибо за ваш отзыв!")
    bot.send_message(user_id, "Если хотите сделать новый заказ, нажмите кнопку 'Старт'.")


bot.polling(none_stop=True)
