import telebot
import sqlite3

TOKEN = "8018209670:AAFVu7-VD5Mh9JeLnsq6HLzcMX2NP9DhiRQ"  # Замените на свой токен
bot = telebot.TeleBot(TOKEN)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📜 Меню", "✍ Отзывы")
    bot.send_message(message.chat.id, "Добро пожаловать в наш ресторан!", reply_markup=keyboard)


# Обработчик команды /menu
@bot.message_handler(func=lambda message: message.text == "📜 Меню")
def show_categories(message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Получаем уникальные категории
    cursor.execute("SELECT DISTINCT category FROM menu")
    categories = cursor.fetchall()

    conn.close()

    if categories:
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in categories:
            keyboard.add(category[0])
        keyboard.add("🔙 Назад")
        bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Меню пока пустое.")


# Запуск бота
bot.polling(none_stop=True)
