from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Contact
from aiogram.filters import CommandStart, Command, StateFilter
from other_funch import was_inactive_for_24_hours
import db
import keyboard as kb
from other_funch import user_exists, is_correct_mobile_phone_number_ru, format_phone, is_password_strong
from const import MANAGER_ID

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


class ProductForm(StatesGroup):
    name = State()             # Название товара
    description = State()      # Описание
    price = State()            # Цена
    category = State()         # Категория
    subcategory = State()      # Подкатегория
    photo = State()            # Фото


class CategoryForm(StatesGroup):
    name = State()  # Ввод названия категории


class SubcategoryForm(StatesGroup):
    category_name = State()        # Ввод названия категории
    subcategory_name = State()     # Ввод названия подкатегории


class RedactForm(StatesGroup):
    product_id = State()
    name = State()
    description = State()
    price = State()
    category = State()
    subcategory = State()
    photo = State()

class DeleteForm(StatesGroup):
    id = State()

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
        await message.answer("✅ Вы успешно вошли в аккаунт!")
        await cmd_profile(message)
        await state.clear()
    else:
        await message.answer("❌ Неверный пароль. Попробуйте снова.")

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
    await cmd_profile(message)
    await state.clear()
  
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
    await message.answer("✅ Вы успешно зарегистрированы!")
    await cmd_profile(message)
    await state.clear()

# ПРОФИЛЬ

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
                          f"Телефон: {phone}", reply_markup=kb.start_kb)
    
# ВЫХОД

@router.callback_query(F.data == "logout")
async def process_logout(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn, cur = db.init_users()
    cur.execute("UPDATE users SET is_logged_in = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await callback.message.answer("Вы вышли из аккаунта.", reply_markup=kb.start_kb)
    await callback.answer()

# ОТМЕНА (регистрации, входа)

@router.callback_query(F.data == "cancel_registration")
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Регистрация/вход отменён.", reply_markup=kb.start_kb)
    await callback.answer()

# КАТАЛОГ

# @router.message(F.text == "Каталог")
# async def show_catalog(message: Message):
#     registered = await user_exists(message.from_user.id)
#     if not registered:
#         await message.answer("Вы должны зарегистрироваться, чтобы получить доступ к каталогу.")
#         return
#     await message.answer("Выберите категорию:", reply_markup=kb.catalog_kb)


# @router.callback_query(F.data.startswith("cat_"))
# async def show_category(callback: CallbackQuery):
#     category = callback.data.split("_")[1]
#     products = db.get_products_by_category(category)
#     if not products:
#         await callback.message.answer(f"Категория '{category}' пуста.")
#         return
#     for product_id, photo_url, description, price in products:
#         markup = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text=f"Добавить в корзину {product_id}", callback_data=f"add_{product_id}")]
#         ])
#         await callback.message.send_photo(photo=photo_url, caption=f"{description}\nЦена: {price} руб.", reply_markup=markup)
#     await callback.answer()

# ДОБАВЛЕНИЕ ТОВАРОВ В КОРЗИНУ 

# @router.callback_query(F.data.startswith("add_"))
# async def add_to_cart(callback: CallbackQuery):
#     product_id = int(callback.data.split("_")[1])
#     conn, cur = db.init_products()
#     cur.execute("SELECT description, price FROM products WHERE id=?", (product_id,))
#     product = cur.fetchone()
#     if not product:
#         await callback.answer("Товар не найден.")
#         return
#     basket = db.get_user_basket(callback.from_user.id)
#     basket.append(product_id)
#     db.update_user_basket(callback.from_user.id, basket)
#     await callback.answer(f"Товар {product_id} добавлен в корзину.")

# КОРЗИНА 

# @router.message(F.text == "Корзина")
# async def view_cart(message: Message):
#     basket = db.get_user_basket(message.from_user.id)
#     if not basket:
#         await message.answer("Корзина пуста.")
#         return
#     conn, cur = db.init_products()
#     for product_id in basket:
#         cur.execute("SELECT photo, description, price FROM products WHERE id=?", (product_id,))
#         photo_url, description, price = cur.fetchone()
#         await message.send_photo(photo=photo_url, caption=f"{description}\nЦена: {price} руб.")
#     conn.close()

# МЕНЕДЖЕР 

@router.message(F.text == "Менеджер-панель")
async def admin_panel(message: Message):
    if message.from_user.id in MANAGER_ID:
        await message.answer("Вы вошли как менеджер:", reply_markup=kb.mened)
    else:
        await message.answer("❌ У вас нет доступа к панели менеджера.")

# ДОБАВЛЕНИЕ ТОВАРА МЕНЕДЖЕРОМ

@router.callback_query(F.data == "add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Введите категорию товара:")
    await state.set_state(ProductForm.category)


@router.message(ProductForm.category)
async def product_set_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Введите подкатегорию:")
    await state.set_state(ProductForm.subcategory)


@router.message(ProductForm.subcategory)
async def product_set_subcategory(message: Message, state: FSMContext):
    await state.update_data(subcategory=message.text)
    await message.answer("Введите название товара:")
    await state.set_state(ProductForm.name)

    
@router.message(ProductForm.name, F.text)
async def product_set_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Загрузите фото товара")
    await state.set_state(ProductForm.photo)


@router.message(ProductForm.photo, F.photo)
async def product_set_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Введите описание товара:")
    await state.set_state(ProductForm.description)


@router.message(ProductForm.description)
async def product_set_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену товара:")
    await state.set_state(ProductForm.price)


@router.message(ProductForm.price)
async def product_set_price(message: Message, state: FSMContext):
    price_text = message.text.strip()
    if not price_text.isdigit():
        await message.answer("❌ Цена должна быть числом.")
        return
    await state.update_data(price=int(price_text))
    data = await state.get_data()
    category_name = data.get("category")
    category_id = db.get_category_id_by_name(category_name)
    if not category_id:
        await message.answer(f"❌ Категория '{category_name}' не найдена.\n"
                             f"Сначала создайте категорию через менеджер-панель.")
        return
    subcategory_name = data.get("subcategory")
    subcategory_id = None
    if category_id and subcategory_name:
        subcategory_id = db.get_subcategory_id_by_name(subcategory_name, category_id)
        if not subcategory_id:
            subcategory_id = db.add_subcategory(subcategory_name, category_id)
    db.add_product(
        name=data.get("name", "Без имени"),
        description=data.get("description", "Нет описания"),
        price=data["price"],
        category_id=category_id,
        subcategory_id=subcategory_id,
        photo=data.get("photo")
    )
    await message.answer("✅ Товар успешно добавлен в каталог!", reply_markup=kb.mened)
    await state.clear()

# УДАЛЕНИЕ ТОВАРА МЕНЕДЖЕРОМ

@router.callback_query(F.data == "delete_product")
async def delete_product_prompt(message: Message, state: FSMContext):
    await message.answer("Введите ID товара, который хотите удалить:")
    await message.answer("Для отмены нажмите /cancel")
    await state.set_state(DeleteForm.id)


@router.message(DeleteForm.id)
async def delete_product_by_id(message: Message, state: FSMContext):
    product_id = int(message.text.strip())
    conn, cur = db.init_products()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    if cur.rowcount > 0:
        await message.answer(f"✅ Товар с ID {product_id} удален.")
    else:
        await message.answer(f"❌ Товар с ID {product_id} не найден.")
    await state.clear()

# РЕДАКТИРОВАНИЕ ТОВАРА МЕНЕДЖЕРОМ

@router.callback_query(F.data == "edit_product")
async def edit_product_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID товара для редактирования:")
    await state.set_state(RedactForm.product_id)
    await callback.answer()
@router.message(RedactForm.product_id, F.text.isdigit())
async def edit_product_get_id(message: Message, state: FSMContext):
    product_id = int(message.text.strip())
    product = db.get_product_by_id(product_id)
    if not product:
        await message.answer(f"❌ Товар с ID {product_id} не найден.")
        return
    pid, name, photo, description, price, category_id, subcategory_id = product
    category_name = db.get_category_name_by_id(category_id) if category_id else "Не указана"
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else "Не указана"
    caption = (
        f"<b>Редактирование товара #{pid}</b>\n\n"
        f"Название: {name}\n"
        f"Описание: {description}\n"
        f"Цена: {price} руб.\n"
        f"Категория: {category_name}\n"
        f"Подкатегория: {subcategory_name}"
    )
    if photo and isinstance(photo, str):
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            caption + "\n\n📷 Фото: отсутствует",
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML"
        )
    await state.update_data(product_id=pid)
    await state.set_state(RedactForm.product_id)

@router.callback_query(F.data.startswith("edit_product_"))
async def start_editing(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    if len(parts) < 4 or not parts[3].isdigit():
        await callback.answer("❌ Неверный формат данных.")
        return
    action = parts[2]
    product_id = int(parts[3])
    if action == "name":
        await callback.message.answer("Введите новое название:")
        await state.set_state(RedactForm.name)
    elif action == "description":
        await callback.message.answer("Введите новое описание:")
        await state.set_state(RedactForm.description)
    elif action == "price":
        await callback.message.answer("Введите новую цену:")
        await state.set_state(RedactForm.price)
    elif action == "category":
        await callback.message.answer("Введите новую категорию:")
        await state.set_state(RedactForm.category)
    elif action == "subcategory":
        await callback.message.answer("Введите новую подкатегорию:")
        await state.set_state(RedactForm.subcategory)
    elif action == "photo":
        await callback.message.answer("Загрузите новое фото:")
        await state.set_state(RedactForm.photo)
    else:
        await callback.answer("❌ Неизвестное действие")
        return
    await state.update_data(product_id=product_id)
    await callback.answer()


async def show_edit_menu(message: Message, state: FSMContext, product_id: int):
    product = db.get_product_by_id(product_id)
    if not product:
        await message.answer("❌ Товар не найден.")
        return
    pid, name, photo, description, price, category_id, subcategory_id = product
    category_name = db.get_category_name_by_id(category_id) if category_id else "Не указана"
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else "Не указана"
    caption = (
        f"<b>Редактирование товара #{pid}</b>\n\n"
        f"Название: {name}\n"
        f"Описание: {description}\n"
        f"Цена: {price} руб.\n"
        f"Категория: {category_name}\n"
        f"Подкатегория: {subcategory_name}"
    )
    if photo and isinstance(photo, str):
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            caption + "\n\n📷 Фото: отсутствует",
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML"
        )
    await state.update_data(product_id=pid)
    await state.set_state(RedactForm.product_id)


@router.message(RedactForm.name)
async def edit_product_set_name(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_name = message.text.strip()
    db.update_product_name(product_id, new_name)
    await message.answer(f"✅ Название товара #{product_id} изменено на '{new_name}'")
    await show_edit_menu(message, state, product_id)
    await state.set_state(RedactForm.product_id)


@router.message(RedactForm.description)
async def edit_product_set_description(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_description = message.text.strip()
    db.update_product_description(product_id, new_description)
    await message.answer(f"✅ Описание товара #{product_id} обновлено.")
    await show_edit_menu(message, state, product_id)


@router.message(RedactForm.price, F.text.isdigit())
async def edit_product_set_price(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_price = int(message.text.strip())
    db.update_product_price(product_id, new_price)
    await message.answer(f"✅ Цена товара #{product_id} изменена на {new_price} руб.")
    await show_edit_menu(message, state, product_id)


@router.message(RedactForm.category)
async def edit_product_set_category(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_category_name = message.text.strip()
    category_id = db.get_category_id_by_name(new_category_name)
    if not category_id:
        db.add_category(new_category_name)
        category_id = db.get_category_id_by_name(new_category_name)
    db.update_product_category(product_id, category_id)
    await message.answer(f"✅ Категория товара #{product_id} изменена на '{new_category_name}'")
    await show_edit_menu(message, state, product_id)


@router.message(RedactForm.photo, F.photo)
async def edit_product_set_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    product_id = data["product_id"]
    db.update_product_photo(product_id, photo_id)
    await message.answer("✅ Фото успешно обновлено.")
    await show_edit_menu(message, state, product_id)


@router.message(ProductForm.category)
async def edit_product_set_category(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_category_name = message.text.strip()
    category_id = db.get_category_id_by_name(new_category_name)
    if not category_id:
        db.add_category(new_category_name)
        category_id = db.get_category_id_by_name(new_category_name)
    db.update_product_category(product_id, category_id)
    await message.answer(f"✅ Категория товара #{product_id} изменена на '{new_category_name}'")
    await state.clear()


@router.callback_query(F.data == "add_category")
async def add_category_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название категории:")
    await state.set_state(CategoryForm.name)
    await callback.answer()


@router.message(CategoryForm.name, F.text)
async def save_new_category(message: Message, state: FSMContext):
    name = message.text.strip()
    success = db.add_category(name)
    if success:
        await message.answer(f"✅ Категория '{name}' добавлена.")
    else:
        await message.answer("❌ Такая категория уже существует.")
    await state.clear()


@router.callback_query(F.data == "add_subcategory")
async def add_subcategory_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название категории, к которой хотите добавить подкатегорию:")
    await state.set_state(SubcategoryForm.category_name)
    await callback.answer()


@router.message(SubcategoryForm.category_name, F.text)
async def get_category_for_subcategory(message: Message, state: FSMContext):
    category_name = message.text.strip()
    conn, cur = db.init_products()
    cur.execute("SELECT id FROM categories WHERE name=?", (category_name,))
    category = cur.fetchone()
    conn.close()
    if not category:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать новую категорию", callback_data="add_category")],
            [InlineKeyboardButton(text="🔄 Повторить ввод", callback_data="retry_add_subcategory")]
        ])
        await message.answer(f"❌ Категория '{category_name}' не найдена.", reply_markup=keyboard)
        return
    await state.update_data(category_id=category[0])
    await message.answer("Введите название подкатегории:")
    await state.set_state(SubcategoryForm.subcategory_name)


@router.message(SubcategoryForm.subcategory_name, F.text)
async def save_new_subcategory(message: Message, state: FSMContext):
    data = await state.get_data()
    category_id = data["category_id"]
    subcategory_name = message.text.strip()
    conn, cur = db.init_products()
    try:
        cur.execute("INSERT INTO subcategories (name, category_id) VALUES (?, ?)",
                    (subcategory_name, category_id))
        conn.commit()
        await message.answer(f"✅ Подкатегория '{subcategory_name}' успешно добавлена в категорию #{category_id}")
    except Exception as e:
        await message.answer(f"❌ Не удалось добавить подкатегорию: {e}")
    finally:
        conn.close()
        await state.clear()

# ПРОСМОТР ТОВАРА МЕНЕДЖЕРОМ

@router.callback_query(F.data == "list_products")
async def list_products_handler(callback: CallbackQuery):
    products = db.get_all_products()
    if not products:
        await callback.message.answer("🛒 В каталоге пока нет товаров.")
        await callback.answer()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p[1]}", callback_data=f"view_product_{p[0]}")] 
        for p in products
    ])
    await callback.message.answer("🛍 Список товаров:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("view_product_"))
async def view_product_handler(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Неверный формат ID")
        return
    product = db.get_product_by_id(product_id)
    if not product:
        await callback.message.answer("❌ Товар не найден.")
        await callback.answer()
        return
    pid, name, photo, description, price, category_id, subcategory_id = product
    category_name = db.get_category_name_by_id(category_id) if category_id else None
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else None
    category_info = ""
    if category_name:
        category_info += f"\n🗂 Категория: {category_name}"
    if subcategory_name:
        category_info += f"\n🧩 Подкатегория: {subcategory_name}"
    caption = f"<b>{name}</b>\n\n{description}\n\n💰 Цена: {price} руб.{category_info}\n\nID: {pid}"
    if photo and isinstance(photo, str):
        await callback.message.answer_photo(photo, caption=caption, parse_mode="HTML")
    else:
        await callback.message.answer(caption, parse_mode="HTML")   
    await callback.answer()

# /CANCEL

@router.message(Command("cancel"), ~StateFilter(default_state))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Регистрация/вход отменён.", reply_markup=kb.start_kb)

# ОСТАЛЬНЫЕ ЗАПРОСЫ

@router.message(F.text)
async def handle_unknown_message(message: Message):
    await message.answer(
        "❌ Я не понимаю это сообщение.\n"
        "Пожалуйста, воспользуйтесь меню или командами:\n"
        "/start — начать\n"
        "/profile — посмотреть профиль\n"
        "/help — помощь",
        reply_markup=kb.start_kb
    )