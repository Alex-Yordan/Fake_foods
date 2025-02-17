import os
import sqlite3
import telebot
from telebot import types
from config import TOKEN
import re

bot = telebot.TeleBot(TOKEN)
IMAGE_FOLDER = "images"

# Создание таблицы корзины, если ее нет
conn = sqlite3.connect("database.db")
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
    conn = sqlite3.connect("database.db")
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
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()
    conn.close()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for category in categories:
        keyboard.add(types.KeyboardButton(category[0]))
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: check_category_exists(message.text))
def show_dishes(message):
    category = message.text
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, price, image_url FROM menu WHERE category = ?", (category,))
    dishes = cursor.fetchall()
    conn.close()

    if dishes:
        keyboard = types.InlineKeyboardMarkup()
        for dish in dishes:
            dish_name, description, price, image_filename = dish
            image_path = os.path.join(IMAGE_FOLDER, image_filename)
            response = f"*{dish_name}*\n_{description}_\n💰 Цена: {price} ₽"

            if os.path.exists(image_path):
                with open(image_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=response, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, response, parse_mode="Markdown")

            row = [
                types.InlineKeyboardButton(f"{dish_name}", callback_data="ignore"),
                types.InlineKeyboardButton("🍽️", callback_data=f"{dish_name}-1"),
                types.InlineKeyboardButton("🍽️🍽️", callback_data=f"{dish_name}-2"),
                types.InlineKeyboardButton("🍽️🍽️🍽️", callback_data=f"{dish_name}-3")
            ]
            keyboard.row(*row)

        keyboard.add(types.InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
        bot.send_message(message.chat.id, "Выберите блюдо и количество:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "В этой категории пока нет блюд.")


@bot.callback_query_handler(func=lambda call: re.match(r"^.+-\\d+$", call.data))
def handle_dish_selection(call):
    user_id = call.message.chat.id
    match = re.match(r"^(.+)-(\\d+)$", call.data)
    if not match:
        bot.answer_callback_query(call.id, "Ошибка при добавлении блюда.")
        return

    dish_name = match.group(1)
    quantity = int(match.group(2))

    add_to_cart(user_id, dish_name, quantity)
    bot.answer_callback_query(call.id, f"✅ {dish_name} ({quantity} шт.) добавлено в корзину!")


def add_to_cart(user_id, dish_name, quantity):
    """Добавляет выбранное блюдо в корзину пользователя"""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM menu WHERE name=?", (dish_name,))
    dish = cursor.fetchone()

    if dish:
        dish_id = dish[0]
        cursor.execute("INSERT INTO cart (user_id, dish_id, quantity) VALUES (?, ?, ?)", (user_id, dish_id, quantity))
        conn.commit()

    conn.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_one-"))
def remove_one(call):
    user_id = call.message.chat.id
    dish_name = call.data.split("-")[1]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id=? AND dish_id=(SELECT id FROM menu WHERE name=?) LIMIT 1",
                   (user_id, dish_name))
    conn.commit()
    conn.close()
    show_cart(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_all-"))
def remove_all(call):
    user_id = call.message.chat.id
    dish_name = call.data.split("-")[1]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id=? AND dish_id=(SELECT id FROM menu WHERE name=?)",
                   (user_id, dish_name))
    conn.commit()
    conn.close()
    show_cart(call)


@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def clear_cart(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    show_cart(call)


bot.polling(none_stop=True)
