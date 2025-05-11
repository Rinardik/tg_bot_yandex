import sqlite3
import json
import time


def init_users():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            password TEXT,
            basket TEXT,
            is_logged_in INTEGER DEFAULT 0,
            last_active INTEGER DEFAULT 0
)""")
    conn.commit()
    return conn, cur


def init_products():
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
                  FOREIGN KEY (category_id) REFERENCES categories(id),
                  FOREIGN KEY (subcategory_id) REFERENCES subcategories(id)
                  )""")
    conn.commit()
    return conn, cur


# --- Работа с категориями ---
def get_all_categories():
    """Получить все категории"""
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM categories")
    result = cur.fetchall()
    conn.close()
    return result


def add_category(name):
    """Добавить новую категорию"""
    conn, cur = init_products()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Такая категория уже существует
    finally:
        conn.close()


def delete_category(category_id):
    """Удалить категорию и связанные подкатегории/товары"""
    conn, cur = init_products()
    try:
        conn.execute("BEGIN")  # Начать транзакцию
        cur.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
        cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("Ошибка при удалении категории:", e)
        return False
    finally:
        conn.close()


# --- Работа с подкатегориями ---
def get_subcategories_by_category(category_id):
    """Получить подкатегории по ID категории"""
    conn, cur = init_products()
    cur.execute("SELECT id, name FROM subcategories WHERE category_id = ?", (category_id,))
    result = cur.fetchall()
    conn.close()
    return result


def add_subcategory(name, category_id):
    """Добавить подкатегорию"""
    conn, cur = init_products()
    cur.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)", (name, category_id))
    conn.commit()
    conn.close()


# --- Работа с товарами ---
def get_all_products():
    """Получить все товары с описанием и фото"""
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


def add_product(name, photo, description, price, category_id, subcategory_id=None):
    """Добавить товар"""
    conn, cur = init_products()
    cur.execute(
        "INSERT INTO products (name, photo, description, price, category_id, subcategory_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, photo, description, price, category_id, subcategory_id)
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    """Удалить товар по ID"""
    conn, cur = init_products()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def get_category_id_by_name(name):
    conn, cur = init_products()
    cur.execute("SELECT id FROM categories WHERE name=?", (name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_subcategory_id_by_name(name, category_id):
    conn, cur = init_products()
    cur.execute("SELECT id FROM subcategories WHERE name=? AND category_id=?", (name, category_id))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_all_products():
    conn, cur = init_products()
    cur.execute("SELECT id, name, price, photo, description FROM products")
    result = cur.fetchall()
    conn.close()
    return result


def get_product_by_id(product_id):
    conn, cur = init_products()
    cur.execute("""
        SELECT id, name, description, price, photo, category_id, subcategory_id 
        FROM products WHERE id=?
    """, (product_id,))
    product = cur.fetchone()
    conn.close()
    return product


def update_or_create_user(user_id, name, phone, password=None, is_logged_in=1):
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
        """, (user_id, name, phone, password, json.dumps([]), is_logged_in, int(time.time())))
        conn.commit()
    finally:
        conn.close()


def check_phon(phone):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE phone = ?", (phone,))
    result = cur.fetchone()
    return result


def get_product_by_id(product_id):
    conn, cur = init_products()
    cur.execute("""
        SELECT * FROM products WHERE id=?
    """, (product_id,))
    result = cur.fetchone()
    conn.close()
    return result


def get_category_name_by_id(category_id):
    if not category_id:
        return None
    conn, cur = init_products()
    cur.execute("SELECT name FROM categories WHERE id=?", (category_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_subcategory_name_by_id(subcategory_id):
    if not subcategory_id:
        return None
    conn, cur = init_products()
    cur.execute("SELECT name FROM subcategories WHERE id=?", (subcategory_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def update_product_name(product_id, new_name):
    conn, cur = init_products()
    cur.execute("UPDATE products SET name=? WHERE id=?", (new_name, product_id))
    conn.commit()
    conn.close()


def update_product_description(product_id, new_description):
    conn, cur = init_products()
    cur.execute("UPDATE products SET description=? WHERE id=?", (new_description, product_id))
    conn.commit()
    conn.close()


def update_product_price(product_id, new_price):
    conn, cur = init_products()
    cur.execute("UPDATE products SET price=? WHERE id=?", (new_price, product_id))
    conn.commit()
    conn.close()


def update_product_category(product_id, new_category_id):
    conn, cur = init_products()
    cur.execute("UPDATE products SET category_id=? WHERE id=?", (new_category_id, product_id))
    conn.commit()
    conn.close()


def update_product_photo(product_id, new_photo_id):
    conn, cur = init_products()
    cur.execute("UPDATE products SET photo=? WHERE id=?", (new_photo_id, product_id))
    conn.commit()
    conn.close()