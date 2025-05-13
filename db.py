import sqlite3
import json
import time
from typing import Optional, List, Dict, Tuple


# ====== Работа с пользователями ======
def init_users():
    """
    Подключается к базе данных пользователей.
    Создаёт таблицу, если её нет.
    """
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        phone TEXT UNIQUE,
        password TEXT,
        basket TEXT,
        is_logged_in INTEGER DEFAULT 0,
        last_active INTEGER DEFAULT 0
    )""")
    conn.commit()
    return conn, cur


# ====== Работа с товарами ======
def init_products():
    """
    Подключение к базе с товарами.
    Создаёт структуру категорий → подкатегорий → товаров
    """
    conn = sqlite3.connect("products.db")
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS categories (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL
              )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS subcategories (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  category_id INTEGER,
                  FOREIGN KEY (category_id) REFERENCES categories(id)
              )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        photo TEXT,
        description TEXT,
        price INTEGER,
        category_id INTEGER,
        subcategory_id INTEGER,
        available INTEGER DEFAULT 1,  -- 1 = в наличии, 0 = нет в наличии
        FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
    )""")
    conn.commit()
    return conn, cur


# ====== Работа с заказами ======
def init_orders():
    """
    Подключение к базе данных заказов.
    Создаёт таблицу, если её нет.
    """
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        basket TEXT,
        total_price INTEGER,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn, cur


# ====== Функции работы с корзиной ======
def get_user_basket(user_id):
    """
    Получает содержимое корзины пользователя.
    """
    conn, cur = init_users()
    cur.execute("SELECT basket FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    try:
        return json.loads(result[0]) if result and result[0] else {}
    except Exception as e:
        print(f"[get_user_basket] Ошибка при загрузке корзины: {e}")
        return {}


def update_user_basket(user_id, basket_dict):
    """
    Обновляет корзину пользователя.
    """
    conn, cur = init_users()
    cur.execute("UPDATE users SET basket=? WHERE user_id=?", (json.dumps(basket_dict), user_id))
    conn.commit()
    conn.close()


# ====== Функции работы с товарами ======
def get_product_by_id(product_id: int):
    """
    Возвращает товар по его ID.
    """
    conn, cur = init_products()
    cur.execute("""
        SELECT id, name, photo, description, price, category_id, subcategory_id, available 
        FROM products 
        WHERE id=?
    """, (product_id,))
    result = cur.fetchone()
    conn.close()
    return result


def get_products_by_ids(product_ids: list[int]):
    """
    Возвращает список товаров по списку ID.
    """
    if not product_ids:
        return []
    conn, cur = init_products()
    placeholders = ', '.join('?' * len(product_ids))
    cur.execute(f"""
        SELECT id, name, photo, description, price, category_id, subcategory_id, available
        FROM products
        WHERE id IN ({placeholders})
    """, product_ids)
    result = cur.fetchall()
    conn.close()
    return result


def get_all_categories():
    """
    Возвращает все категории из БД.
    """
    conn, cur = init_products()
    cur.execute("SELECT name FROM categories")
    result = [row[0] for row in cur.fetchall()]
    conn.close()
    return result


def get_subcategories_by_category(category_id: int):
    """
    Возвращает подкатегории для заданной категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM subcategories WHERE category_id=?", (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def get_products_by_category(category_id: int):
    """
    Возвращает товары указанной категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name, photo, description, price FROM products WHERE category_id=?", (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def get_products_by_subcategory(subcategory_id: int):
    """
    Возвращает товары указанной подкатегории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name, photo, description, price FROM products WHERE subcategory_id=?", (subcategory_id,))
    result = cur.fetchall()
    conn.close()
    return result


def get_category_id_by_name(name: str) -> int | None:
    """
    Находит ID категории по имени.
    """
    conn, cur = init_products()
    cur.execute("SELECT id FROM categories WHERE name=?", (name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def add_category(name: str) -> int | None:
    """
    Добавляет новую категорию.
    """
    conn, cur = init_products()
    cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    cat_id = cur.lastrowid
    conn.close()
    return cat_id


def get_subcategory_id_by_name(name: str, category_id: int) -> int | None:
    """
    Находит ID подкатегории по имени и категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id FROM subcategories WHERE name=? AND category_id=?", (name, category_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def add_subcategory(name: str, category_id: int) -> int | None:
    """
    Добавляет новую подкатегорию.
    """
    conn, cur = init_products()
    cur.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (name, category_id))
    conn.commit()
    subcat_id = cur.lastrowid
    conn.close()
    return subcat_id


def get_category_name_by_id(category_id: int) -> str | None:
    """
    Возвращает имя категории по ID.
    """
    conn, cur = init_products()
    cur.execute("SELECT name FROM categories WHERE id=?", (category_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_subcategory_name_by_id(subcategory_id: int) -> str | None:
    """
    Возвращает имя подкатегории по ID.
    """
    conn, cur = init_products()
    cur.execute("SELECT name FROM subcategories WHERE id=?", (subcategory_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


# ====== Работа с заказами ======
def save_order(user_id, basket_dict, total_price):
    """
    Сохраняет заказ пользователя в БД.
    """
    conn, cur = init_orders()
    cur.execute("INSERT INTO orders (user_id, basket, total_price) VALUES (?, ?, ?)",
                (user_id, json.dumps(basket_dict), total_price))
    conn.commit()
    conn.close()


def get_new_orders():
    """
    Возвращает список новых заказов.
    """
    conn, cur = init_orders()
    cur.execute("SELECT id, user_id, basket, total_price, status FROM orders WHERE status='new'")
    result = cur.fetchall()
    conn.close()
    return result


def get_order_by_id(order_id):
    """
    Возвращает заказ по ID.
    """
    conn, cur = init_orders()
    cur.execute("SELECT id, user_id, basket, total_price, status FROM orders WHERE id=?", (order_id,))
    result = cur.fetchone()
    conn.close()
    return result


def update_order_status(order_id, new_status):
    """
    Меняет статус заказа.
    """
    conn, cur = init_orders()
    cur.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()


def get_user_info(user_id):
    """
    Возвращает информацию о пользователе.
    """
    conn, cur = init_users()
    cur.execute("SELECT name, phone FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result


async def user_exists(user_id: int) -> bool:
    """
    Проверяет, зарегистрирован ли пользователь.
    """
    conn, cur = init_users()
    cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None

def get_all_categories():
    """
    Получает список всех доступных категорий из базы данных.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM categories")
    result = cur.fetchall()
    conn.close()
    return result


def add_category(name: str) -> bool:
    """
    Добавляет новую категорию в БД.
    Если такая уже есть → возникает ошибка уникальности.
    """
    conn, cur = init_products()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Такое имя уже используется
        return False
    finally:
        conn.close()


def delete_category(category_id: int) -> bool:
    """
    Удаляет категорию и все связанные подкатегории/товары.
    Используется транзакция на случай ошибок.
    """
    conn, cur = init_products()
    try:
        conn.execute("BEGIN")  # Начинаем транзакцию
        cur.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[delete_category] Ошибка при удалении категории {category_id}: {e}")
        return False
    finally:
        conn.close()


def get_subcategories_by_category(category_id: int) -> list[tuple]:
    """
    Возвращает список подкатегорий по ID родительской категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM subcategories WHERE category_id = ?", (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def add_subcategory(name: str, category_id: int) -> None:
    """
    Добавляет новую подкатегорию в указанную категорию.
    """
    conn, cur = init_products()
    cur.execute(
        "INSERT INTO subcategories (name, category_id) VALUES (?, ?)",
        (name, category_id)
    )
    conn.commit()
    conn.close()


def get_all_products():
    """
    Возвращает все товары с данными
    """
    conn, cur = init_products()
    cur.execute("""
        SELECT p.id, p.name, p.photo, p.description, p.price, c.name, s.name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN subcategories s ON p.subcategory_id = s.id
    """)
    result = cur.fetchall()
    conn.close()
    return result


def add_product(name: str, photo: str, description: str, price: int, category_id: int, subcategory_id: int | None = None):
    """
    Добавляет новый товар в базу данных.
    """
    conn, cur = init_products()
    cur.execute(
        "INSERT INTO products (name, photo, description, price, category_id, subcategory_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, photo, description, price, category_id, subcategory_id)
    )
    conn.commit()
    conn.close()


def delete_product(product_id: int) -> bool:
    """
    Удаляет товар по ID.
    """
    conn, cur = init_products()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ====== Работа с категориями ======
def get_category_id_by_name(name: str) -> Optional[int]:
    """
    Возвращает ID категории по её имени.
    """
    conn, cur = init_products()
    cur.execute("SELECT id FROM categories WHERE name=?", (name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_category_name_by_id(category_id: int) -> Optional[str]:
    """
    Возвращает имя категории по ID.
    """
    if not category_id:
        return None

    conn, cur = init_products()
    cur.execute("SELECT name FROM categories WHERE id=?", (category_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_all_categories() -> List[Tuple[int, str]]:
    """
    Возвращает список всех категорий.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM categories ORDER BY name ASC")
    result = cur.fetchall()
    conn.close()
    return result


def add_category(name: str) -> bool:
    """
    Добавляет новую категорию в БД.
    """
    conn, cur = init_products()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Такая категория уже существует
        return False
    finally:
        conn.close()


def delete_category(category_id: int) -> bool:
    """
    Удаляет категорию и все связанные подкатегории/товары.
    """
    conn, cur = init_products()
    try:
        conn.execute("BEGIN")  # Начинаем транзакцию
        cur.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cur.execute("DELETE FROM products WHERE category_id = ?", (category_id,))
        cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[delete_category] Ошибка при удалении категории {category_id}: {e}")
        return False
    finally:
        conn.close()


# ====== Работа с подкатегориями ======
def get_subcategory_id_by_name(name: str, category_id: int) -> Optional[int]:
    """
    Возвращает ID подкатегории по имени и категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id FROM subcategories WHERE name=? AND category_id=?", (name, category_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_subcategories_by_category(category_id: int) -> List[Tuple[int, str]]:
    """
    Возвращает список подкатегорий по ID категории.
    """
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM subcategories WHERE category_id = ?", (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def add_subcategory(name: str, category_id: int):
    """
    Добавляет новую подкатегорию в указанную категорию.
    """
    conn, cur = init_products()
    cur.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (name, category_id))
    conn.commit()
    conn.close()


# ====== Работа с товарами ======
def get_product_by_id(product_id: int) -> Optional[Tuple]:
    """
    Возвращает товар по его ID.
    """
    conn, cur = init_products()
    cur.execute("""
        SELECT id, name, photo, description, price, category_id, subcategory_id, available 
        FROM products WHERE id=?
    """, (product_id,))
    result = cur.fetchone()
    conn.close()
    return result


def get_products_by_ids(product_ids: List[int]) -> List[Tuple]:
    """
    Возвращает список товаров по списку ID.
    """
    if not product_ids:
        return []

    conn, cur = init_products()
    placeholders = ', '.join('?' * len(product_ids))
    cur.execute(f"""
        SELECT id, name, photo, description, price 
        FROM products 
        WHERE id IN ({placeholders})
    """, [int(pid) for pid in product_ids])

    result = cur.fetchall()
    conn.close()
    return result


def get_products_by_category(category_id: int) -> List[Tuple]:
    """
    Возвращает товары указанной категории.
    """
    conn, cur = init_products()
    cur.execute("""
        SELECT id, name, photo, description, price 
        FROM products WHERE category_id=?
    """, (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def get_products_by_subcategory(subcategory_id: int) -> List[Tuple]:
    """
    Возвращает товары указанной подкатегории.
    """
    conn, cur = init_products()
    cur.execute("""
        SELECT id, name, photo, description, price 
        FROM products WHERE subcategory_id=?
    """, (subcategory_id,))
    result = cur.fetchall()
    conn.close()
    return result


def update_product_name(product_id: int, new_name: str):
    """
    Обновляет название товара.
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET name=? WHERE id=?", (new_name, product_id))
    conn.commit()
    conn.close()


def update_product_description(product_id: int, new_description: str):
    """
    Обновляет описание товара.
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET description=? WHERE id=?", (new_description, product_id))
    conn.commit()
    conn.close()


def update_product_price(product_id: int, new_price: int):
    """
    Обновляет цену товара.
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET price=? WHERE id=?", (new_price, product_id))
    conn.commit()
    conn.close()


def update_product_category(product_id: int, new_category_id: int):
    """
    Обновляет категорию товара.
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET category_id=? WHERE id=?", (new_category_id, product_id))
    conn.commit()
    conn.close()


def update_product_photo(product_id: int, new_photo_id: str):
    """
    Обновляет фото товара.
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET photo=? WHERE id=?", (new_photo_id, product_id))
    conn.commit()
    conn.close()


def update_product_availability(product_id: int, new_stat: int):
    """
    Обновляет статус наличия товара (в наличии / нет).
    """
    conn, cur = init_products()
    cur.execute("UPDATE products SET available=? WHERE id=?", (new_stat, product_id))
    conn.commit()
    conn.close()


def add_product(
    name: str,
    photo: str,
    description: str,
    price: int,
    category_id: int,
    subcategory_id: Optional[int] = None
):
    """
    Добавляет новый товар в базу данных.
    """
    conn, cur = init_products()
    cur.execute(
        "INSERT INTO products (name, photo, description, price, category_id, subcategory_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, photo, description, price, category_id, subcategory_id)
    )
    conn.commit()
    conn.close()


def delete_product(product_id: int) -> bool:
    """
    Удаляет товар по ID.
    """
    conn, cur = init_products()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ====== Работа с пользователями ======
def check_phon(phone: str) -> bool:
    """
    Проверяет, зарегистрирован ли пользователь с таким телефоном.
    """
    conn, cur = init_users()
    cur.execute("SELECT 1 FROM users WHERE phone = ?", (phone,))
    result = cur.fetchone()
    conn.close()
    return bool(result)


def get_user_info(user_id: int) -> Optional[Tuple[str, str]]:
    """
    Возвращает имя и телефон пользователя.
    """
    conn, cur = init_users()
    cur.execute("SELECT name, phone FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result


def update_or_create_user(user_id: int, name: str, phone: str, password: str, is_logged_in: int = 1):
    """
    Создаёт или обновляет данные пользователя.
    """
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (user_id, name, phone, password, basket, is_logged_in, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            phone = excluded.phone,
            password = excluded.password,
            is_logged_in = excluded.is_logged_in,
            last_active = excluded.last_active
        """, (
            user_id,
            name,
            phone,
            password,
            json.dumps({}),  # Теперь корзина — это dict
            is_logged_in,
            int(time.time())
        ))
        conn.commit()
    finally:
        conn.close()


# ====== Работа с корзиной ======
def get_user_basket(user_id: int) -> Dict[str, int]:
    """
    Получает корзину пользователя.
    Если она сохранена как list → преобразует в dict
    """
    conn, cur = init_users()
    cur.execute("SELECT basket FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    conn.close()
    if not result or not result[0]:
        return {}
    try:
        data = json.loads(result[0])
        if isinstance(data, list):
            return {str(pid): 1 for pid in data}
        elif isinstance(data, dict):
            return data
        else:
            return {}
    except json.JSONDecodeError:
        return {}


def update_user_basket(user_id: int, basket_dict: dict):
    """
    Обновляет корзину пользователя.
    """
    conn, cur = init_users()
    cur.execute("UPDATE users SET basket=? WHERE user_id=?", (json.dumps(basket_dict), user_id))
    conn.commit()
    conn.close()