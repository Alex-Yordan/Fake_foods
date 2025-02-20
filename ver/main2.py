import os
import sqlite3
import telebot
from telebot import types
from config import TOKEN
import re

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
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в сервис заказа еды. Выберите категорию:")
    show_categories(message)


def show_categories(message):
    """Отображает список категорий"""
    conn = sqlite3.connect("../database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()
    conn.close()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for category in categories:
        keyboard.add(types.KeyboardButton(category[0]))
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)


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


@bot.message_handler(func=lambda message: check_category_exists(message.text))
def show_dishes(message):
    category = message.text
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
                    bot.send_photo(message.chat.id, photo, caption=response, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, response, parse_mode="Markdown")

            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("🍽️ 1", callback_data=f"{dish_name}-1"),
                types.InlineKeyboardButton("🍽️🍽️ 2", callback_data=f"{dish_name}-2"),
                types.InlineKeyboardButton("🍽️🍽️🍽️ 3", callback_data=f"{dish_name}-3")
            )
            bot.send_message(message.chat.id, "Выберите количество:", reply_markup=keyboard)

        bottom_keyboard = types.InlineKeyboardMarkup()
        bottom_keyboard.add(
            types.InlineKeyboardButton("🛒 Корзина", callback_data="cart"),
            types.InlineKeyboardButton("💳 Оплатить", callback_data="pay"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories")
        )
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=bottom_keyboard)
    else:
        bot.send_message(message.chat.id, "В этой категории пока нет блюд.")


bot.polling(none_stop=True)
