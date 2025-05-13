from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Каталог", callback_data="catalog")]
])

mened = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
    [InlineKeyboardButton(text="🗂 Добавить категорию", callback_data="admin_add_category")],
    [InlineKeyboardButton(text="🧩 Добавить подкатегорию", callback_data="admin_add_subcategory")],
    [InlineKeyboardButton(text="❌ Удалить товар", callback_data="admin_delete_product")],
    [InlineKeyboardButton(text="✏️ Редактировать товар", callback_data="admin_edit_product")],
    [InlineKeyboardButton(text="📦 Список товаров", callback_data="admin_list_products")],
    [InlineKeyboardButton(text="📦 Список заказов", callback_data="view_orders")],
])

zam_parol = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Отправить мой номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_order_actions(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}")]
    ])

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
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_product_name_{product_id}")],
        [InlineKeyboardButton(text="🧮 Цена", callback_data=f"edit_product_price_{product_id}")],
        [InlineKeyboardButton(text="🗂 Категория", callback_data=f"edit_product_category_{product_id}")],
        [InlineKeyboardButton(text="📷 Фото", callback_data=f"edit_product_photo_{product_id}")],
        [InlineKeyboardButton(text="🔄 Статус наличия", callback_data=f"edit_product_available_{product_id}")]
    ])


def get_catalog_keyboard(categories):
    if not categories:
        return None
    keyboard = [
        [InlineKeyboardButton(text=cat[1], callback_data=f"category_{cat[0]}")] 
        for cat in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_subcategories_keyboard(subcategories):
    if not subcategories:
        return None
    keyboard = [
        [InlineKeyboardButton(text=sub[1], callback_data=f"subcategory_{sub[0]}")] 
        for sub in subcategories
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_products_keyboard(products):
    if not products:
        return None
    keyboard = [
        [InlineKeyboardButton(text=f"{p[1]} — {p[4]} руб.", callback_data=f"product_{p[0]}")] 
        for p in products
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_product_detail_keyboard(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data=f"add_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к каталогу", callback_data="catalog")]
    ])

def get_basket_item_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data=f"add_{product_id}")],
        [InlineKeyboardButton(text="➖ Убрать один", callback_data=f"remove_one_{product_id}")],
        [InlineKeyboardButton(text="🗑 Удалить всё", callback_data=f"remove_all_{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к каталогу", callback_data="catalog")],
        [InlineKeyboardButton(text="📦 Посмотреть корзину", callback_data="view_basket")],
        [InlineKeyboardButton(text="📦 Оформить заказ", callback_data="checkout")]
    ])


def get_subcategories() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать новую категорию", callback_data="admin_add_category")]
    ])

def client_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="view_basket")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")]
    ])