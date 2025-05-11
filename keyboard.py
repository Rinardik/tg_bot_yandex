from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Каталог", callback_data="catalog")]
])

catalog_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Футболки", callback_data="cat_футболки")],
    [InlineKeyboardButton(text="Шорты", callback_data="cat_шорты")],
    [InlineKeyboardButton(text="Обувь", callback_data="cat_обувь")]
])

admin_panel_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить товар", callback_data="add_product")],
    [InlineKeyboardButton(text="Удалить товар", callback_data="delete_product")],
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