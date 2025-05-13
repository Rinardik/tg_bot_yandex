from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Contact
from aiogram.filters import CommandStart, Command, StateFilter
from other_funch import was_inactive_for_24_hours
import db
import keyboard as kb
from other_funch import user_exists, is_correct_mobile_phone_number_ru, format_phone, is_password_strong
from const import MANAGER_ID
from states import RegistrationForm, LoginStates, RecoveryForm, ProductForm, CategoryForm, SubcategoryForm, RedactForm, DeleteForm
import json

router = Router()

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
            reply_markup=kb.zam_parol)
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

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    registered = await user_exists(callback.from_user.id)
    if not registered:
        await callback.message.answer("Вы должны зарегистрироваться, чтобы получить доступ к каталогу.")
        await callback.answer()
        return
    categories = db.get_all_categories()
    keyboard = kb.get_catalog_keyboard(categories)
    if not keyboard:
        await callback.message.answer("❌ Категории пока отсутствуют.")
        return
    await callback.message.answer("🛍 Выберите категорию:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("category_"))
async def show_subcategories(callback: CallbackQuery):
    try:
        category_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        await callback.answer()
        return
    subcategories = db.get_subcategories_by_category(category_id)
    if not subcategories:
        products = db.get_products_by_category(category_id)
        if not products:
            await callback.message.answer("❌ Товаров в этой категории пока нет.")
            return
        keyboard = kb.get_products_keyboard(products)
        await callback.message.answer("🛍 Товары категории:", reply_markup=keyboard)
        return
    keyboard = kb.get_subcategories_keyboard(subcategories)
    await callback.message.answer("🧩 Выберите подкатегорию:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("subcategory_"))
async def show_products_by_subcategory(callback: CallbackQuery):
    try:
        subcategory_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        await callback.answer()
        return
    products = db.get_products_by_subcategory(subcategory_id)
    if not products:
        await callback.message.answer("❌ В этой подкатегории пока нет товаров.")
        return
    keyboard = kb.get_products_keyboard(products)
    await callback.message.answer("🛍 Товары подкатегории:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("product_"))
async def view_product(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный ID товара")
        await callback.answer()
        return
    product = db.get_product_by_id(product_id)
    if not product:
        await callback.message.answer("❌ Товар не найден.")
        return
    pid, name, photo, description, price, category_id, subcategory_id, available = product
    caption = (
        f"<b>{name}</b>\n\n"
        f"{description}\n\n"
        f"💰 Цена: {price} руб.\n"
        f"📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n"
        f"ID: {pid}")
    if photo and isinstance(photo, str):
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb.get_product_detail_keyboard(pid))
    else:
        await callback.message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=kb.get_product_detail_keyboard(pid))
    await callback.answer()

# КОРЗИНА 

async def show_basket_after_edit(callback: CallbackQuery):
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    if not basket:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        return
    total_price = 0
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for product_id_str, quantity in basket.items():
        product_id = int(product_id_str)
        product = db.get_product_by_id(product_id)
        if not product:
            continue
        pid, name, photo, description, price, category_id, subcategory_id, available = product
        item_total = price * quantity
        total_price += item_total
        caption = (
            f"<b>{name}</b>\n\n"
            f"{description}\n\n"
            f"📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n"
            f"💰 Цена: {price} руб.\n"
            f"🔢 Количество: {quantity}\n"
            f"🧮 Итого: {item_total} руб."
        )
        if photo and isinstance(photo, str):
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb.get_basket_item_keyboard(pid))
        else:
            await callback.message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=kb.get_basket_item_keyboard(pid))
    await callback.message.answer(f"🧮 Общая сумма: <b>{total_price} руб.</b>", parse_mode="HTML")


@router.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: CallbackQuery):
    if callback.data.startswith("add_category_") or callback.data.startswith("add_subcategory_"):
        await callback.answer("Это не товар для корзины.")
        return
    parts = callback.data.split("_")
    if len(parts) < 2:
        await callback.message.answer("❌ Неверный формат данных.")
        return
    if not parts[1].isdigit():
        await callback.message.answer(f"❌ ID товара должен быть числом. Получено: {parts[1]}")
        return
    product_id = int(parts[1])
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    key = str(product_id)
    basket[key] = basket.get(key, 0) + 1
    db.update_user_basket(user_id, basket)
    await callback.message.answer(f"✅ Товар #{product_id} добавлен в корзину.")
    await show_basket_after_edit(callback)
    await callback.answer()


@router.callback_query(F.data == "view_basket")
async def view_basket(callback: CallbackQuery):
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    if not basket:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        return
    basket_ids = list(map(int, basket.keys()))
    if not basket_ids:
        await callback.message.answer("❌ В корзине нет товаров.")
        return
    products = db.get_products_by_ids(basket_ids)
    if not products:
        await callback.message.answer("❌ Товаров в базе данных не найдено.")
        return
    total_price = 0
    for p in products:
        pid, name, photo, description, price = p
        quantity = basket.get(str(pid), 1)
        item_total = price * quantity
        total_price += item_total
        caption = (
            f"<b>{name}</b>\n\n"
            f"{description}\n\n"
            f"💰 Цена: {price} руб.\n"
            f"🔢 Количество: {quantity}\n"
            f"🧮 Итого: {item_total} руб.")
        if photo and isinstance(photo, str):
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb.get_basket_item_keyboard(pid))
        else:
            await callback.message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=kb.get_basket_item_keyboard(pid))
    await callback.message.answer(f"🧮 Общая сумма: <b>{total_price} руб.</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("remove_all_"))
async def remove_all_from_cart(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Неверный формат данных.")
        return
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    key = str(product_id)
    if key in basket:
        del basket[key]
        db.update_user_basket(user_id, basket)
        await callback.message.answer(f"🗑 Удалён товар #{product_id}")
    await show_basket_after_edit(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("remove_one_"))
async def remove_one_from_cart(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Неверный формат данных.")
        return
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    key = str(product_id)
    if key in basket:
        basket[key] -= 1
        if basket[key] <= 0:
            del basket[key]
        db.update_user_basket(user_id, basket)
        await callback.message.answer(f"🗑 Уменьшили количество товара #{product_id}")
    await show_basket_after_edit(callback)
    await callback.answer()
    

@router.callback_query(F.data == "view_basket")
async def view_basket(callback: CallbackQuery):
    await show_basket_after_edit(callback)
    await callback.answer()


@router.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    if not basket:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        return
    product_ids = list(map(int, basket.keys()))
    products = db.get_products_by_ids(product_ids)
    if not products:
        await callback.message.answer("❌ Товары не найдены в базе данных.")
        return
    total_price = sum(db.get_product_by_id(pid)[4] * qty for pid, qty in basket.items())
    db.save_order(user_id, basket, total_price)
    db.update_user_basket(user_id, {})
    caption = f"✅ Заказ оформлен!\n\n🧮 Итого: {total_price} руб.\nСпасибо за покупку!"
    await callback.message.answer(caption)
    await notify_manager_about_order(
        bot=callback.bot,
        user_id=user_id,
        basket=basket,
        total_price=total_price
    )
    await callback.answer()

# МЕНЕДЖЕР 

@router.message(F.text == "Менеджер-панель")
async def admin_panel(message: Message):
    if message.from_user.id in MANAGER_ID:
        await message.answer("Вы вошли как менеджер:", reply_markup=kb.mened)
    else:
        await message.answer("❌ У вас нет доступа к панели менеджера.")

# ДОБАВЛЕНИЕ ТОВАРА МЕНЕДЖЕРОМ

@router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите категорию товара:")
    await state.set_state(ProductForm.category)
    await callback.answer()


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

@router.callback_query(F.data == "admin_delete_product")
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

@router.callback_query(F.data == "admin_edit_product")
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
    pid, name, photo, description, price, category_id, subcategory_id, available = product
    category_name = db.get_category_name_by_id(category_id) if category_id else "Не указана"
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else "Не указана"
    caption = (
        f"<b>Редактирование товара #{pid}</b>\n\n"
        f"Название: {name}\n"
        f"Описание: {description}\n"
        f"📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n"
        f"Цена: {price} руб.\n"
        f"Категория: {category_name}\n"
        f"Подкатегория: {subcategory_name}")
    if photo and isinstance(photo, str):
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML")
    else:
        await message.answer(
            caption + "\n\n📷 Фото: отсутствует",
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML")
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
    elif action == "available":
        await callback.message.answer("Введите 0, 1 если товар не в наличии, в наличии соответсвенно")
        await state.set_state(RedactForm.available)
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
    pid, name, photo, description, price, category_id, subcategory_id, available = product
    category_name = db.get_category_name_by_id(category_id) if category_id else "Не указана"
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else "Не указана"
    caption = (
        f"<b>Редактирование товара #{pid}</b>\n\n"
        f"Название: {name}\n"
        f"Описание: {description}\n"
        f"📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n"
        f"Цена: {price} руб.\n"
        f"Категория: {category_name}\n"
        f"Подкатегория: {subcategory_name}")
    if photo and isinstance(photo, str):
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML")
    else:
        await message.answer(
            caption + "\n\n📷 Фото: отсутствует",
            reply_markup=kb.edit_product_keyboard(pid),
            parse_mode="HTML")
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

@router.message(RedactForm.available)
async def edit_product_set_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_name = message.text.strip()
    db.update_product_available(product_id, new_name)
    await message.answer(f"Cтатус товара изменен на {'В наличии' if message.text.strip() else 'Нет в наличии'}")
    await show_edit_menu(message, state, product_id)
    await state.set_state(RedactForm.product_id)


@router.callback_query(F.data == "admin_add_category")
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


@router.callback_query(F.data == "admin_add_subcategory")
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
        await message.answer(
            f"❌ Категория '{category_name}' не найдена.",
            reply_markup=kb.get_subcategories())        
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

@router.callback_query(F.data == "admin_list_products")
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
    pid, name, photo, description, price, category_id, subcategory_id, available = product
    category_name = db.get_category_name_by_id(category_id) if category_id else None
    subcategory_name = db.get_subcategory_name_by_id(subcategory_id) if subcategory_id else None
    category_info = ""
    if category_name:
        category_info += f"\n🗂 Категория: {category_name}"
    if subcategory_name:
        category_info += f"\n🧩 Подкатегория: {subcategory_name}"
    caption = f"<b>{name}</b>\n\n{description}\n\n💰 Цена: {price} руб.{category_info}\n\n📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n\nID: {pid}"
    if photo and isinstance(photo, str):
        await callback.message.answer_photo(photo, caption=caption, parse_mode="HTML")
    else:
        await callback.message.answer(caption, parse_mode="HTML")   
    await callback.answer()


async def notify_manager_about_order(bot: Bot, user_id: int, basket: dict, total_price: int):
    basket_text = "\n".join([
        f"{db.get_product_by_id(int(pid))[1]} x {qty} шт. = {db.get_product_by_id(int(pid))[4] * qty} руб."
        for pid, qty in basket.items()
    ])
    message_text = (
        f"📦 Новый заказ от пользователя {user_id}\n\n"
        f"Товары:\n{basket_text}\n\n"
        f"🧮 Общая сумма: {total_price} руб."
    )
    for manager_id in MANAGER_ID:
        try:
            await bot.send_message(manager_id, message_text, reply_markup=kb.mened)
        except Exception as e:
            print(f"[notify_manager] Ошибка при отправке менеджеру {manager_id}: {e}")


def format_basket(basket):
    lines = []
    for pid, quantity in basket.items():
        product = db.get_product_by_id(int(pid))
        if product:
            _, name, _, _, price, *_ = product
            lines.append(f"{name} x {quantity} шт. = {price * quantity} руб.")
    return "\n".join(lines)


@router.callback_query(F.data == "view_orders")
async def view_orders(callback: CallbackQuery):
    orders = db.get_new_orders()
    if not orders:
        await callback.message.answer("📋 Нет новых заказов.")
        return
    for order in orders:
        order_id, user_id, basket_json, total_price, created_at = order
        basket = json.loads(basket_json)
        user_info = db.get_user_info(user_id)
        if user_info:
            name, phone = user_info
            caption = (
                f"📦 Заказ #{order_id}\n"
                f"👤 Пользователь: {user_id} --- {name}\n"
                f"📞 Телефон: {phone}\n")
        caption += f"Дата: {created_at}\n\n"
        caption += f"Товары:\n{format_basket(basket)}\n\n"
        caption += f"🧮 Итого: {total_price} руб."
        await callback.message.answer(caption, reply_markup=kb.get_order_actions(order_id))
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        return
    db.update_order_status(order_id, "confirmed")
    order = db.get_order_by_id(order_id)
    if not order:
        await callback.message.answer("❌ Заказ не найден.")
        return
    _, user_id, _, _, _ = order
    await callback.bot.send_message(user_id, f"✅ Ваш заказ #{order_id} подтверждён!")
    await callback.message.edit_text(f"Заказ #{order_id} подтверждён.", reply_markup=None)
    await callback.answer()

# ОСТАЛЬНЫЕ ЗАПРОСЫ

@router.message(F.text)
async def handle_unknown_message(message: Message):
    await message.answer(
        "❌ Я не понимаю это сообщение.\n"
        "Пожалуйста, воспользуйтесь меню или командами:\n"
        "/start — начать\n"
        "/profile — посмотреть профиль\n"
        "/help — помощь",
        reply_markup=kb.start_kb)