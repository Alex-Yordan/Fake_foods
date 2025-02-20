import os
import sqlite3
import telebot
from telebot import types
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
IMAGE_FOLDER = "images"

# Создание таблицы корзины, если ее нет
conn = sqlite3.connect("../database.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dish_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (dish_id) REFERENCES menu (id)
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT,
        phone TEXT,
        order_number INTEGER,
        review TEXT
    )
""")
conn.commit()
conn.close()


def check_category_exists(category):
    """Проверяет, существует ли категория"""
    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu WHERE category = ?", (category,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


@bot.message_handler(commands=['start'])
def start(message):
    """Отправляем кнопку 'Старт'"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_button = types.KeyboardButton("Старт")
    keyboard.add(start_button)

    bot.send_message(message.chat.id, "Привет! Добро пожаловать в сервис заказа еды. Нажмите 'Старт', чтобы начать.",
                     reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Старт")
def handle_start(message):
    """Удаляем кнопку 'Старт' и начинаем работу"""
    user_id = message.chat.id
    bot.delete_message(message.chat.id, message.message_id)  # Убираем кнопку 'Старт'
    show_categories(message)  # Переходим к выбору категорий


def show_categories(message):
    """Отображает список категорий в InlineKeyboard"""
    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()
    conn.close()

    # Используем InlineKeyboardMarkup для кнопок категорий
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for category in categories:
        keyboard.add(types.InlineKeyboardButton(category[0], callback_data=category[0]))

    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in [category[0] for category in
                                                            sqlite3.connect("../database.db").cursor().execute(
                                                                "SELECT DISTINCT category FROM menu").fetchall()])
def show_dishes(call):
    """Отображает блюда из выбранной категории"""
    category = call.data
    conn = sqlite3.connect("../database.db")
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
    conn = sqlite3.connect("../database.db")
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
    response = "🛒 *Ваша корзина:*\n\n"
    response += "🔔 Нажав на кнопку с названием блюда, вы удалите его из корзины.\n\n"  # Пояснение

    keyboard = types.InlineKeyboardMarkup()

    for name, price, quantity, cart_id in cart_items:
        # Создаем строку с названием блюда и кнопкой удаления
        dish_text = f"{name} - {quantity} шт. (💰 {price} ₽ за шт.) = {price * quantity} ₽"
        keyboard.add(
            types.InlineKeyboardButton(dish_text, callback_data=f"remove_{cart_id}")
        )

    response += f"\n💰 *Итого: {total_price} ₽*"

    # Кнопки очистки корзины, оплаты и назад
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

    conn = sqlite3.connect("../database.db")
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

    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "Корзина очищена.")
    show_cart(call)


@bot.callback_query_handler(func=lambda call: '-' in call.data)
def add_to_cart(call):
    """Добавляет блюдо в корзину"""
    dish_name, quantity = call.data.split("-")
    quantity = int(quantity)
    user_id = call.message.chat.id

    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, price FROM menu WHERE name = ?", (dish_name,))
    dish = cursor.fetchone()
    conn.close()

    if dish:
        dish_id, price = dish
        conn = sqlite3.connect("../database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cart (user_id, dish_id, quantity)
            VALUES (?, ?, ?)
        """, (user_id, dish_id, quantity))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, f"Блюдо {dish_name} добавлено в корзину ({quantity} шт.).")
        show_cart(call)


@bot.callback_query_handler(func=lambda call: call.data == "pay")
def start_payment(call):
    """Запрашивает имя и телефон для оплаты"""
    user_id = call.message.chat.id
    bot.send_message(user_id, "Для оформления заказа, введите ваше имя.")
    bot.register_next_step_handler(call.message, get_name)


def get_name(message):
    """Получает имя клиента"""
    user_id = message.chat.id
    name = message.text

    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO customers (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()

    bot.send_message(user_id, "Теперь введите ваш номер телефона.")
    bot.register_next_step_handler(message, get_phone)


def get_phone(message):
    """Получает телефон клиента"""
    user_id = message.chat.id
    phone = message.text

    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET phone = ? WHERE user_id = ?", (phone, user_id))
    conn.commit()

    # Генерация номера заказа
    cursor.execute("SELECT MAX(order_number) FROM customers")
    result = cursor.fetchone()
    order_number = result[0] + 1 if result[0] else 1
    cursor.execute("UPDATE customers SET order_number = ? WHERE user_id = ?", (order_number, user_id))
    conn.commit()
    conn.close()

    # Кнопка для подтверждения оплаты
    bot.send_message(user_id, f"Ваш заказ № {order_number}. Для подтверждения нажмите оплатить.")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(f"💳 Оплатить заказ № {order_number}", callback_data=f"pay_order_{order_number}"))
    bot.send_message(user_id, "Подтвердите оплату.", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_order_"))
def process_payment(call):
    """Процесс оплаты"""
    order_number = int(call.data.split("_")[-1])
    user_id = call.message.chat.id
    bot.send_message(user_id, f"Оплата заказа № {order_number} в процессе...")

    # Симуляция задержки на 10 секунд (оплата)
    import time
    time.sleep(10)

    # Очистить корзину после оплаты
    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    bot.send_message(user_id, f"Оплата заказа № {order_number} успешно завершена.")
    bot.send_message(user_id, f"Ваш заказ № {order_number} принят в работу.")
    bot.send_message(user_id, f"Ваша еда готовится! 🍳👨‍🍳")

    time.sleep(30)

    bot.send_message(user_id, f"Ваш заказ № {order_number} готов! 🍽️")

    time.sleep(20)

    bot.send_message(user_id, "Спасибо, что воспользовались услугами нашего ресторана! Оставьте отзыв.")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Оставить отзыв", callback_data="leave_review"))
    bot.send_message(user_id, "Надеемся, вам понравилось!", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "leave_review")
def leave_review(call):
    """Запрашивает отзыв и отображает кнопки 'Отправить отзыв' и 'Без отзыва'"""
    user_id = call.message.chat.id
    bot.send_message(user_id, "Пожалуйста, оставьте ваш отзыв.", reply_markup=types.ReplyKeyboardRemove())

    # Включаем inline-кнопки "Отправить отзыв" и "Без отзыва"
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    send_review_button = types.InlineKeyboardButton("Отправить отзыв", callback_data="send_review")
    no_review_button = types.InlineKeyboardButton("Без отзыва", callback_data="no_review")
    keyboard.add(send_review_button, no_review_button)

    bot.send_message(user_id, "Вы можете отправить отзыв или пропустить.", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "send_review")
def send_review(call):
    """Обрабатывает отправку отзыва"""
    user_id = call.message.chat.id
    review_text = call.message.text

    # Записываем отзыв в базу данных
    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET review = ? WHERE user_id = ?", (review_text, user_id))
    conn.commit()
    conn.close()

    bot.send_message(user_id, "Спасибо за ваш отзыв!")

    # Отправляем кнопку 'Старт' для начала нового заказа
    start_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_button = types.KeyboardButton("Старт")
    start_keyboard.add(start_button)
    bot.send_message(user_id, "Нажмите 'Старт' для начала нового заказа.", reply_markup=start_keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "no_review")
def no_review(call):
    """Обрабатывает ситуацию, когда пользователь не оставляет отзыв"""
    user_id = call.message.chat.id

    # Просто отправляем сообщение, что отзыв не был оставлен
    bot.send_message(user_id, "Вы выбрали не оставлять отзыв.")

    # Отправляем кнопку 'Старт' для начала нового заказа
    start_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_button = types.KeyboardButton("Старт")
    start_keyboard.add(start_button)
    bot.send_message(user_id, "Нажмите 'Старт' для начала нового заказа.", reply_markup=start_keyboard)


if __name__ == '__main__':
    bot.polling(none_stop=True)
