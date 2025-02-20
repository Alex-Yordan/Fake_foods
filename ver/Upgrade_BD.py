import sqlite3

# Подключаемся к базе
conn = sqlite3.connect("../database.db")
cursor = conn.cursor()

# Добавляем блюда в категорию "Супы"
soups = [
    ("Супы", "Борщ", "Классический украинский борщ с говядиной, свеклой, капустой и сметаной.", 250, "https://cdn.lifehacker.ru/wp-content/uploads/2020/09/1_1600193281-scaled-e1600193382307-1280x640.jpg"),
    ("Супы", "Том Ям", "Острый тайский суп с креветками, кокосовым молоком, грибами и лаймом.", 350, "https://static.tildacdn.com/tild3937-6632-4531-b833-613333333239/IMG_8994.jpg"),
    ("Супы", "Грибной крем-суп", "Нежный суп-пюре из шампиньонов и сливок, подается с сухариками.", 300, "https://static.1000.menu/res/640/img/content-v2/20/87/21211/gribnoi-krem-sup-iz-shampinonov_1600761169_16_max.jpg"),
    ("Супы", "Харчо", "Грузинский острый суп с говядиной, томатами, рисом и пряностями.", 280, "https://img.iamcook.ru/2023/upl/recipes/cat/u-19c4d374e0e15218477a98cba0e6ccaf.jpg"),
    ("Супы", "Солянка", "Наваристый суп с копченостями, оливками, лимоном и сметаной.", 320, "https://www.gastronom.ru/binfiles/images/20180226/bf9ab5e1.jpg")
]

cursor.executemany("INSERT INTO menu (category, name, description, price, image_url) VALUES (?, ?, ?, ?, ?)", soups)
conn.commit()
conn.close()

print("✅ Данные добавлены в базу!")
