from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Contact
from aiogram.filters import CommandStart, Command, StateFilter
from other_funch import was_inactive_for_24_hours
import db
import keyboard as kb
from other_funch import user_exists, is_correct_mobile_phone_number_ru, format_phone, is_password_strong


router = Router()

# состояния для регистрации
class RegistrationForm(StatesGroup):
    name = State()
    phone = State()
    password = State()
    password_confirm = State()


# состояния для входа
class LoginStates(StatesGroup):
    phone = State()
    password = State()


class RecoveryForm(StatesGroup):
    phone = State()
    code = State()
    new_password = State()
    confirm_new_password = State()

# РЕГИСТРАЦИЯ

@router.callback_query(F.data == "registration")
async def process_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ваше имя:")
    await state.set_state(RegistrationForm.name)
    await callback.answer()


@router.message(StateFilter(RegistrationForm.name), F.text)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:", reply_markup=kb.zam_parol)
    await state.set_state(RegistrationForm.phone)

@router.message(StateFilter(RegistrationForm.phone), F.contact)
async def process_phone(message: Message, state: FSMContext):
    contact: Contact = message.contact
    phone = await format_phone(contact.phone_number)
    correct, answer = await is_correct_mobile_phone_number_ru(phone)
    if not correct:
        await message.answer(answer)
        return
    conn, cur = db.init_users()
    try:
        cur.execute("SELECT 1 FROM users WHERE phone = ?", (phone,))
        user_exists = cur.fetchone() is not None
    finally:
        conn.close()
    if user_exists:
        await message.answer(
            "❌ Пользователь с этим телефоном уже зарегистрирован.\n"
            "Если вы забыли пароль — нажмите на кнопку ниже.",
            reply_markup=kb.zam_parol
        )
        await state.clear()
        return
    await state.update_data(phone=phone)
    await message.answer("Придумайте пароль:", reply_markup=kb.get_cancel_kb())
    await state.set_state(RegistrationForm.password)

    
@router.message(StateFilter(RegistrationForm.password), F.text)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")
    is_strong, msg = is_password_strong(password, name, phone)
    if not is_strong:
        await message.answer(msg)
        return
    await state.update_data(password=password)
    await message.answer("Повторите пароль:", reply_markup=kb.get_cancel_kb())
    await state.set_state(RegistrationForm.password_confirm)


@router.message(StateFilter(RegistrationForm.password_confirm), F.text)
async def process_password_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    password = data["password"]
    confirm_password = message.text.strip()
    if password != confirm_password:
        await message.answer("Пароли не совпадают. Попробуйте снова.")
        await message.answer("Введите пароль:", reply_markup=kb.get_cancel_kb())
        await state.set_state(RegistrationForm.password)
        return
    name = data["name"]
    phone = data["phone"]
    user_id = message.from_user.id
    db.update_or_create_user(user_id, name, phone, password)
    await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=kb.start_kb)
    await state.clear()

# ВХОД

@router.callback_query(F.data == "entr")
async def process_login(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:", reply_markup=kb.zam_parol)
    await state.set_state(LoginStates.phone)
    await callback.answer()


@router.message(StateFilter(LoginStates.phone), F.contact)
async def login_enter_phone(message: Message, state: FSMContext):
    contact: Contact = message.contact
    phone = await format_phone(contact.phone_number.strip())
    conn, cur = db.init_users()
    try:
        result = db.check_phon(phone)
    finally:
        conn.close()
    if not result:
        await message.answer("❌ Пользователь с таким телефоном не найден.")
        return
    await state.update_data(phone=phone)
    await message.answer("Введите пароль:")
    await state.set_state(LoginStates.password)


@router.message(StateFilter(LoginStates.password), F.text)
async def login_enter_password(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data["phone"]
    password = message.text.strip()
    conn, cur = db.init_users()
    try:
        cur.execute("SELECT password FROM users WHERE phone = ?", (phone,))
        result = cur.fetchone()
    finally:
        conn.close()
    if result and result[0] == password:
        conn, cur = db.init_users()
        try:
            cur.execute("UPDATE users SET is_logged_in = 1, last_active = strftime('%s','now') WHERE phone = ?",
                        (phone,))
            conn.commit()
        finally:
            conn.close()
        await message.answer("✅ Вы успешно вошли в аккаунт!", reply_markup=kb.start_kb)
        await state.clear()
    else:
        await message.answer("❌ Неверный пароль. Попробуйте снова.")

# /START

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать в магазин Rinard Shop!\nВыбирайте товары из каталога.", reply_markup=kb.start_kb)
    conn, cur = db.init_users()
    cur.execute("SELECT is_logged_in, last_active FROM users WHERE user_id = ?", (message.from_user.id,))
    result = cur.fetchone()
    if result:
        is_logged_in, last_active = result
        if is_logged_in and not await was_inactive_for_24_hours(last_active):
            await message.answer("Вы уже вошли в аккаунт.", reply_markup=kb.get_logout_kb())
            conn.close()
            return
        else:
            cur.execute("UPDATE users SET is_logged_in = 0 WHERE user_id = ?", (message.from_user.id,))
            conn.commit()
    exists = await user_exists(message.from_user.id)
    conn.close()
    if exists:
        entr = kb.get_login_kb()
        await message.answer("Хотите войти в аккаунт?", reply_markup=entr)
    else:
        registration = kb.get_registration_kb()
        await message.answer("Хотите зарегистрироваться?", reply_markup=registration)

# ВОССТАНОВЛЕНИЕ ПАРОЛЯ

@router.callback_query(F.data == "forgot_password")
async def start_recovery(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Нажмите на кнопку ниже, чтобы отправить ваш номер телефона:", reply_markup=kb.zam_parol)
    await state.set_state(RecoveryForm.phone)
    await callback.answer()


@router.message(StateFilter(RecoveryForm.phone), F.contact)
async def recovery_enter_phone(message: Message, state: FSMContext):
    contact: Contact = message.contact
    phone = await format_phone(contact.phone_number.strip())
    correct, answer = await is_correct_mobile_phone_number_ru(phone)
    if not correct:
        await message.answer(answer)
        return
    conn, cur = db.init_users()
    cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cur.fetchone()
    conn.close()
    if not user:
        await message.answer("Пользователь с таким телефоном не найден.")
        await state.clear()
        return
    await state.update_data(phone=phone)
    await message.answer("Введите новый пароль:")
    await state.set_state(RecoveryForm.new_password)


@router.message(StateFilter(RecoveryForm.new_password), F.text)
async def recovery_set_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")
    is_strong, msg = is_password_strong(password, name, phone)
    if not is_strong:
        await message.answer(msg)
        return
    await state.update_data(new_password=password)
    await message.answer("Повторите пароль:")
    await state.set_state(RecoveryForm.confirm_new_password)


@router.message(StateFilter(RecoveryForm.confirm_new_password), F.text)
async def recovery_confirm_password(message: Message, state: FSMContext):
    data = await state.get_data()
    new_password = data["new_password"]
    confirm_password = message.text.strip()
    if new_password != confirm_password:
        await message.answer("Пароли не совпадают. Попробуйте снова:")
        return
    phone = data["phone"]
    conn, cur = db.init_users()
    try:
        cur.execute("UPDATE users SET password = ? WHERE phone = ?", (new_password, phone))
        conn.commit()
    finally:
        conn.close()
    await message.answer("✅ Пароль успешно изменён!")
    await state.clear()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    conn, cur = db.init_users()
    cur.execute("SELECT name, phone FROM users WHERE user_id = ?", (message.from_user.id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        await message.answer("Вы не зарегистрированы.")
        return
    name, phone = result
    await message.answer(f"Ваш профиль:\n"
                          f"Имя: {name}\n"
                          f"Телефон: {phone}")
    

@router.callback_query(F.data == "logout")
async def process_logout(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn, cur = db.init_users()
    cur.execute("UPDATE users SET is_logged_in = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await callback.message.answer("Вы вышли из аккаунта.", reply_markup=kb.start_kb)
    await callback.answer()

# /START — КНОПКИ

@router.callback_query(F.data == "cancel_registration")
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Регистрация/вход отменён.", reply_markup=kb.start_kb)
    await callback.answer()

# КАТАЛОГ

@router.message(F.text == "Каталог")
async def show_catalog(message: Message):
    registered = await user_exists(message.from_user.id)
    if not registered:
        await message.answer("Вы должны зарегистрироваться, чтобы получить доступ к каталогу.")
        return
    await message.answer("Выберите категорию:", reply_markup=kb.catalog_kb)


@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    products = db.get_products_by_category(category)
    if not products:
        await callback.message.answer(f"Категория '{category}' пуста.")
        return
    for product_id, photo_url, description, price in products:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Добавить в корзину {product_id}", callback_data=f"add_{product_id}")]
        ])
        await callback.message.send_photo(photo=photo_url, caption=f"{description}\nЦена: {price} руб.", reply_markup=markup)
    await callback.answer()

# ДОБАВЛЕНИЕ ТОВАРОВ В КОРЗИНУ 

@router.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    conn, cur = db.init_products()
    cur.execute("SELECT description, price FROM products WHERE id=?", (product_id,))
    product = cur.fetchone()
    if not product:
        await callback.answer("Товар не найден.")
        return
    basket = db.get_user_basket(callback.from_user.id)
    basket.append(product_id)
    db.update_user_basket(callback.from_user.id, basket)
    await callback.answer(f"Товар {product_id} добавлен в корзину.")

# КОРЗИНА 

@router.message(F.text == "Корзина")
async def view_cart(message: Message):
    basket = db.get_user_basket(message.from_user.id)
    if not basket:
        await message.answer("Корзина пуста.")
        return
    conn, cur = db.init_products()
    for product_id in basket:
        cur.execute("SELECT photo, description, price FROM products WHERE id=?", (product_id,))
        photo_url, description, price = cur.fetchone()
        await message.send_photo(photo=photo_url, caption=f"{description}\nЦена: {price} руб.")
    conn.close()

# АДМИНКА 

@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    from const import ID

    if message.from_user.id == ID:
        await message.answer("Вы вошли в админ-панель:", reply_markup=kb.admin_panel_kb)
    else:
        await message.answer("Доступ запрещён.")


@router.callback_query(F.data == "help_add")
async def help_add(callback: CallbackQuery):
    await callback.message.answer(
        "Чтобы добавить товар:\n"
        "Формат: категория###url###описание###цена\n"
        "Пример:\n"
        "Футболки###https://example.com/photo.jpg    ###Описание###1000"
    )
    await callback.answer()


@router.message(F.text.contains("###"))
async def handle_add_product(message: Message):
    from const import ID
    if message.from_user.id != ID:
        return
    parts = message.text.split("###")
    if len(parts) != 4:
        await message.answer("Неправильный формат. Используйте: категория###url###описание###цена")
        return
    category, photo, description, price = parts
    try:
        price = int(price)
    except ValueError:
        await message.answer("Цена должна быть числом.")
        return
    db.add_product(category, photo, description, price)
    await message.answer("Товар успешно добавлен!")


@router.callback_query(F.data == "help_delete")
async def help_delete(callback: CallbackQuery):
    await callback.message.answer(
        "Чтобы удалить товар:\n"
        "Формат: Удалить товар [1,2,3]\n"
        "Пример:\n"
        "Удалить товар [1,2]"
    )
    await callback.answer()


@router.message(F.text.startswith("Удалить товар ["))
async def handle_delete_product(message: Message):
    from const import ID
    if message.from_user.id != ID:
        return
    try:
        raw_ids = message.text.replace("Удалить товар [", "").replace("]", "")
        ids = [int(x.strip()) for x in raw_ids.split(",")]
        db.delete_products_by_ids(ids)
        await message.answer(f"Товар(ы) с ID {ids} удалены.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# /CANCEL

@router.message(Command("cancel"), ~StateFilter(default_state))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация/вход отменён.", reply_markup=kb.start_kb)