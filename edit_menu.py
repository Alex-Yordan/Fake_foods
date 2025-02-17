import sqlite3
import os

DB_PATH = "database.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def show_menu():
    """Выводит список всех блюд в меню."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, name, description, price, image_url FROM menu")
    dishes = cursor.fetchall()
    conn.close()

    if not dishes:
        print("📭 Меню пустое!")
        return

    print("\n📜 Список блюд:")
    for dish in dishes:
        print(f"ID: {dish[0]}, Категория: {dish[1]}, Название: {dish[2]}, Цена: {dish[4]}₽")
        print(f"   📝 {dish[3]}")
        print(f"   🖼 {dish[5]}")
        print("-" * 40)


def add_dish():
    """Добавляет новое блюдо в меню."""
    category = input("Введите категорию блюда: ")
    name = input("Введите название блюда: ")
    description = input("Введите описание: ")
    price = input("Введите цену: ")
    image_url = input("Введите название файла картинки (например, soup1.jpg): ")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menu (category, name, description, price, image_url) VALUES (?, ?, ?, ?, ?)",
                   (category, name, description, price, image_url))
    conn.commit()
    conn.close()
    print(f"✅ Блюдо '{name}' добавлено!")


def edit_dish():
    """Редактирует блюдо по ID."""
    show_menu()
    dish_id = input("\nВведите ID блюда, которое хотите изменить: ")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE id=?", (dish_id,))
    dish = cursor.fetchone()

    if not dish:
        print("❌ Блюдо не найдено!")
        return

    print("\nРедактируем блюдо:")
    new_name = input(f"Новое название ({dish[2]}): ") or dish[2]
    new_desc = input(f"Новое описание ({dish[3]}): ") or dish[3]
    new_price = input(f"Новая цена ({dish[4]}₽): ") or dish[4]
    new_image = input(f"Новый файл картинки ({dish[5]}): ") or dish[5]

    cursor.execute("UPDATE menu SET name=?, description=?, price=?, image_url=? WHERE id=?",
                   (new_name, new_desc, new_price, new_image, dish_id))
    conn.commit()
    conn.close()
    print(f"✅ Блюдо '{new_name}' обновлено!")


def delete_dish():
    """Удаляет блюдо по ID."""
    show_menu()
    dish_id = input("\nВведите ID блюда, которое хотите удалить: ")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu WHERE id=?", (dish_id,))
    conn.commit()
    conn.close()
    print(f"🗑 Блюдо с ID {dish_id} удалено!")


def main():
    while True:
        print("\n🍽 Управление меню ресторана")
        print("1️⃣ Показать меню")
        print("2️⃣ Добавить блюдо")
        print("3️⃣ Редактировать блюдо")
        print("4️⃣ Удалить блюдо")
        print("0️⃣ Выйти")

        choice = input("Выберите действие: ")

        if choice == "1":
            show_menu()
        elif choice == "2":
            add_dish()
        elif choice == "3":
            edit_dish()
        elif choice == "4":
            delete_dish()
        elif choice == "0":
            print("🚪 Выход.")
            break
        else:
            print("❌ Неверный ввод! Попробуйте снова.")


if __name__ == "__main__":
    main()

