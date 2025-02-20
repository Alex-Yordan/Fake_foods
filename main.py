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
    """Отправляем кнопку 'Старт'"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_btn = types.KeyboardButton("Старт")
    keyboard.add(start_btn)
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
    # Проверяем, есть ли запись в customers для user_id
    cursor.execute("SELECT id FROM customers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO customers (user_id) VALUES (?)", (user_id,))
        conn.commit()
        customer_id = cursor.lastrowid
    else:
        customer_id = row[0]
    # Создаем заказ
    cursor.execute("INSERT INTO orders (customer_id, name) VALUES (?, ?)", (customer_id, name))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    current_order[user_id] = order_id
    bot.send_message(user_id, "Теперь введите ваш номер телефона.")
    bot.register_next_step_handler(message, get_phone)


def get_phone(message):
    """Получает номер телефона и обновляет заказ в таблице orders"""
    user_id = message.chat.id
    phone = message.text
    order_id = current_order.get(user_id)
    if order_id is None:
        bot.send_message(user_id, "Ошибка оформления заказа. Пожалуйста, начните заново.")
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET phone = ? WHERE id = ?", (phone, order_id))
    conn.commit()
    conn.close()

    # Предлагаем кнопку "Оплатить заказ #X"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"Оплатить заказ #{order_id}", callback_data=f"pay_order_{order_id}"))
    bot.send_message(user_id, f"Заказ #{order_id} оформлен.\nНажмите кнопку ниже, чтобы оплатить заказ.", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_order_"))
def process_payment(call):
    """
    Процесс оплаты
    После оплаты очищаем корзину, выводим сообщения о готовке, предлагаем отзыв
    """
    order_id = int(call.data.split("_")[-1])
    user_id = call.message.chat.id

    bot.send_message(user_id, f"Оплата заказа #{order_id} в процессе...")
    time.sleep(5)  # Эмуляция задержки оплаты

    # Очищаем корзину после оплаты
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    bot.send_message(user_id, f"Оплата заказа #{order_id} успешно завершена.")
    bot.send_message(user_id, f"Ваш заказ #{order_id} принят в работу.")
    bot.send_message(user_id, "Ваша еда готовится! 🍳👨‍🍳")
    time.sleep(5)
    bot.send_message(user_id, f"Ваш заказ #{order_id} готов! 🍽️")
    time.sleep(3)
    bot.send_message(user_id, "Спасибо, что воспользовались услугами нашего ресторана! Оставьте отзыв.")

    # Кнопки "Оставить отзыв" и "Без отзыва"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Оставить отзыв", callback_data="leave_review"),
        types.InlineKeyboardButton("Без отзыва", callback_data="no_review")
    )
    bot.send_message(user_id, "Надеемся, вам понравилось!", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "leave_review")
def leave_review_handler(call):
    """
    Пользователь хочет оставить отзыв.
    Просим ввести отзыв текстом через register_next_step_handler
    """
    user_id = call.message.chat.id
    bot.send_message(user_id, "Пожалуйста, оставьте ваш отзыв (или напишите 'нет', если передумали).")
    bot.register_next_step_handler(call.message, process_review)


def process_review(message):
    """Получает текст отзыва от пользователя и сохраняет его в заказе"""
    user_id = message.chat.id
    review_text = message.text.strip()
    order_id = current_order.get(user_id)

    if not order_id:
        bot.send_message(user_id, "Ошибка: не найден текущий заказ.")
        return

    if review_text.lower() == "нет":
        bot.send_message(user_id, "Вы выбрали не оставлять отзыв.")
    else:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET review = ? WHERE id = ?", (review_text, order_id))
        conn.commit()
        conn.close()
        bot.send_message(user_id, "Спасибо за ваш отзыв!")

    # Выводим кнопку "Старт" для нового заказа
    start_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_btn = types.KeyboardButton("Старт")
    start_keyboard.add(start_btn)
    bot.send_message(user_id, "Нажмите 'Старт' для начала нового заказа.", reply_markup=start_keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "no_review")
def no_review_handler(call):
    """Если пользователь не хочет оставлять отзыв"""
    user_id = call.message.chat.id
    bot.send_message(user_id, "Вы выбрали не оставлять отзыв.")
    start_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_btn = types.KeyboardButton("Старт")
    start_keyboard.add(start_btn)
    bot.send_message(user_id, "Нажмите 'Старт' для начала нового заказа.", reply_markup=start_keyboard)


if __name__ == '__main__':
    bot.polling(none_stop=True)
