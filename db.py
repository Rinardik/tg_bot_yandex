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
    cur.execute("""CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    photo TEXT,
                    description TEXT,
                    price INTEGER
    )""")
    conn.commit()
    return conn, cur


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


def get_user_basket(user_id):
    conn, cur = init_users()
    cur.execute("SELECT basket FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    return json.loads(result[0]) if result and result[0] else []


def update_user_basket(user_id, basket):
    conn, cur = init_users()
    cur.execute("UPDATE users SET basket=? WHERE user_id=?", (json.dumps(basket), user_id))
    conn.commit()


def add_product(category, photo, description, price):
    conn, cur = init_products()
    cur.execute("INSERT INTO products (category, photo, description, price) VALUES (?, ?, ?, ?)",
                (category, photo, description, price))
    conn.commit()


def delete_products_by_ids(ids):
    conn, cur = init_products()
    placeholders = ', '.join('?' * len(ids))
    cur.execute(f"DELETE FROM products WHERE id IN ({placeholders})", ids)
    conn.commit()


def get_all_products():
    conn, cur = init_products()
    cur.execute("SELECT id, photo, description, price FROM products")
    return cur.fetchall()


def get_products_by_category(category):
    conn, cur = init_products()
    cur.execute("SELECT id, photo, description, price FROM products WHERE category=?", (category,))
    return cur.fetchall()