from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Каталог", callback_data="catalog")]
])

catalog_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Футболки", callback_data="cat_футболки")],
    [InlineKeyboardButton(text="Шорты", callback_data="cat_шорты")],
    [InlineKeyboardButton(text="Обувь", callback_data="cat_обувь")]
])

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

mened = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")],
    [InlineKeyboardButton(text="🗂 Добавить категорию", callback_data="add_category")],
    [InlineKeyboardButton(text="🧩 Добавить подкатегорию", callback_data="add_subcategory")],
    [InlineKeyboardButton(text="❌ Удалить товар", callback_data="delete_product")],
    [InlineKeyboardButton(text="✏️ Редактировать товар", callback_data="edit_product")],
    [InlineKeyboardButton(text="📦 Список товаров", callback_data="list_products")],
])

zam_parol = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Отправить мой номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_logout_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выход", callback_data="logout")]
    ])


def get_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_registration")]
    ])

def get_registration_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Регистрация", callback_data="registration")]
    ])

def get_login_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вход", callback_data="entr")],
        [InlineKeyboardButton(text="Забыли пароль?", callback_data="forgot_password")]
    ])


def edit_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"edit_product_name_{product_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_product_description_{product_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"edit_product_price_{product_id}")],
        [InlineKeyboardButton(text="🗂 Изменить категорию", callback_data=f"edit_product_category_{product_id}")],
        [InlineKeyboardButton(text="🧩 Изменить подкатегорию", callback_data=f"edit_product_subcategory_{product_id}")],
        [InlineKeyboardButton(text="📷 Изменить фото", callback_data=f"edit_product_photo_{product_id}")]
    ])