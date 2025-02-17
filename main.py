import telebot
import sqlite3
import os

from config import TOKEN  # Импорт токена

bot = telebot.TeleBot(TOKEN)

IMAGE_FOLDER = "images"  # Папка с картинками


# 📌 Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📜 Меню", "🛒 Корзина", "✍ Отзывы")
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=keyboard)


# 📌 Показ категорий блюд
@bot.message_handler(func=lambda message: message.text == "📜 Меню")
def show_categories(message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()
    conn.close()

    if categories:
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in categories:
            keyboard.add(category[0])
        keyboard.add("🔙 Назад")  # Добавляем кнопку назад
        bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Меню пока пустое.")



@bot.message_handler(func=lambda message: check_category_exists(message.text))
def show_dishes(message):
    category = message.text
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, description, price, image_url FROM menu WHERE category = ?", (category,))
    dishes = cursor.fetchall()
    conn.close()

    if dishes:
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

        for dish in dishes:
            dish_name, description, price, image_filename = dish[1], dish[2], dish[3], dish[4]
            image_path = os.path.join(IMAGE_FOLDER, image_filename)  # Полный путь к файлу

            response = f"*{dish_name}*\n_{description}_\n💰 Цена: {price} ₽"

            if os.path.exists(image_path):  # Проверяем, есть ли файл
                with open(image_path, "rb") as photo:
                    bot.send_photo(message.chat.id, photo, caption=response, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, f"❌ Ошибка: нет картинки для {dish_name}")

            btn1 = telebot.types.KeyboardButton(f"{dish_name} - 1 шт")
            btn2 = telebot.types.KeyboardButton(f"{dish_name} - 2 шт")
            btn3 = telebot.types.KeyboardButton(f"{dish_name} - 3 шт")
            keyboard.add(btn1, btn2, btn3)

        keyboard.add("🔙 Назад")
        bot.send_message(message.chat.id, "Выберите блюдо и количество:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "В этой категории пока нет блюд.")


# 📌 Обработчик кнопки "🔙 Назад"
@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def go_back(message):
    show_categories(message)  # Возвращаем пользователя к выбору категории


# 📌 Проверка, существует ли категория
def check_category_exists(category):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM menu WHERE category = ?", (category,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# 📌 Запуск бота
bot.polling(none_stop=True)
