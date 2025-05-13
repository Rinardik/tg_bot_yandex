from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import ProductForm, RedactForm, DeleteForm, CategoryForm, SubcategoryForm
import keyboard as kb
import db
from const import MANAGER_ID
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "Менеджер-панель")
async def admin_panel(message: Message):
    """
    Отображает меню менеджера.
    Если пользователь не в списке → запрещает доступ.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ У вас нет доступа к панели менеджера.")
        return
    await message.answer("Вы вошли как менеджер:", reply_markup=kb.mened)


@router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления товара.
    Запрашивает категорию товара.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ Только менеджеры могут добавлять товары.")
        await callback.answer()
        return
    await callback.message.answer("Введите категорию товара:")
    await state.set_state(ProductForm.category)
    await callback.answer()


@router.message(ProductForm.category)
async def product_set_category(message: Message, state: FSMContext):
    """
    Сохраняет категорию и запрашивает подкатегорию.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ Только менеджеры могут продолжить.")
        await state.clear()
        return
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
    """
    Сохраняет название и запрашивает фото.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ Только менеджеры могут продолжить.")
        await state.clear()
        return
    await state.update_data(name=message.text)
    await message.answer("Загрузите фото товара:")
    await state.set_state(ProductForm.photo)


@router.message(ProductForm.photo, F.photo)
async def product_set_photo(message: Message, state: FSMContext):
    """
    Сохраняет фото и запрашивает описание.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ Только менеджеры могут продолжить.")
        await state.clear()
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Введите описание товара:")
    await state.set_state(ProductForm.description)


@router.message(ProductForm.description)
async def product_set_description(message: Message, state: FSMContext):
    """
    Сохраняет описание и запрашивает цену.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ Только менеджеры могут продолжить.")
        await state.clear()
        return
    await state.update_data(description=message.text)
    await message.answer("Введите цену товара:")
    await state.set_state(ProductForm.price)


@router.message(ProductForm.price)
async def product_set_price(message: Message, state: FSMContext):
    """
    Сохраняет цену и завершает добавление товара.
    """
    if message.from_user.id not in MANAGER_ID:
        await message.answer("❌ Только менеджеры могут продолжить.")
        await state.clear()
        return
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
                             f"Сначала создайте её через менеджер-панель.")
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


@router.callback_query(F.data == "admin_delete_product")
async def delete_product_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает ID товара для удаления.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ У вас нет прав на удаление товаров.")
        await callback.answer()
        return
    await callback.message.answer("Введите ID товара, который хотите удалить:")
    await callback.message.answer("Для отмены нажмите /cancel")
    await state.set_state(DeleteForm.id)
    await callback.answer()


@router.message(DeleteForm.id, F.text.isdigit())
async def delete_product_by_id(message: Message, state: FSMContext):
    """
    Удаляет товар по ID из базы данных.
    """
    try:
        product_id = int(message.text.strip())
        conn, cur = db.init_products()
        cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        if cur.rowcount > 0:
            await message.answer(f"✅ Товар с ID {product_id} удален.")
        else:
            await message.answer(f"❌ Товар с ID {product_id} не найден.")
    except Exception as e:
        logger.error(f"[delete_product_by_id] Ошибка при удалении товара: {e}", exc_info=True)
        await message.answer("⚠ Произошла ошибка при удалении товара.")
    await state.clear()


@router.callback_query(F.data == "admin_edit_product")
async def edit_product_prompt(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает ID товара для редактирования.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ Только менеджеры могут редактировать товары.")
        await callback.answer()
        return
    await callback.message.answer("Введите ID товара для редактирования:")
    await state.set_state(RedactForm.product_id)
    await callback.answer()


@router.message(RedactForm.product_id, F.text.isdigit())
async def edit_product_get_id(message: Message, state: FSMContext):
    """
    Выводит карточку товара для редактирования.
    """
    try:
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
            f"Цена: {price} руб.\n"
            f"Категория: {category_name}\n"
            f"Подкатегория: {subcategory_name}\n"
            f"Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}"
        )
        if photo and isinstance(photo, str):
            await message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb.edit_product_keyboard(pid)
            )
        else:
            await message.answer(
                caption + "\n\n📷 Фото: отсутствует",
                parse_mode="HTML",
                reply_markup=kb.edit_product_keyboard(pid)
            )
        await state.update_data(product_id=pid)
        await state.set_state(RedactForm.product_id)
    except Exception as e:
        logger.error(f"[edit_product_get_id] Ошибка при получении товара: {e}", exc_info=True)
        await message.answer("Ошибка при загрузке товара.")


@router.callback_query(F.data.startswith("edit_product_"))
async def start_editing(callback: CallbackQuery, state: FSMContext):
    """
    Переводит бота в нужное состояние редактирования (название, цена и т.д.)
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ У вас нет прав на редактирование.")
        await callback.answer()
        return
    parts = callback.data.split("_")
    if len(parts) < 4 or not parts[3].isdigit():
        await callback.message.answer("❌ Неверный формат данных.")
        await callback.answer()
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
        await callback.message.answer("Введите 0 или 1 для статуса наличия:")
        await state.set_state(RedactForm.available)
    else:
        await callback.answer("❌ Неизвестное действие")
        return
    await state.update_data(product_id=product_id)
    await callback.answer()


@router.message(RedactForm.name)
async def edit_product_set_name(message: Message, state: FSMContext):
    """
    Обработчик изменения названия товара.
    После сохранения показывает обновлённую карточку.
    """
    try:
        data = await state.get_data()
        product_id = data["product_id"]
        new_name = message.text.strip()
        db.update_product_name(product_id, new_name)
        await message.answer(f"✅ Название товара #{product_id} изменено на '{new_name}'")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_name] Ошибка при изменении названия: {e}", exc_info=True)
        await message.answer("Не удалось изменить название.")


@router.message(RedactForm.description)
async def edit_product_set_description(message: Message, state: FSMContext):
    """
    Обработчик изменения описания товара.
    """
    try:
        data = await state.get_data()
        product_id = data["product_id"]
        new_description = message.text.strip()
        db.update_product_description(product_id, new_description)
        await message.answer(f"✅ Описание товара #{product_id} обновлено.")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_description] Ошибка при изменении описания: {e}", exc_info=True)
        await message.answer("Не удалось изменить описание.")


@router.message(RedactForm.price, F.text.isdigit())
async def edit_product_set_price(message: Message, state: FSMContext):
    """
    Обработчик изменения цены товара.
    """
    try:
        data = await state.get_data()
        product_id = data["product_id"]
        new_price = int(message.text.strip())
        db.update_product_price(product_id, new_price)
        await message.answer(f"✅ Цена товара #{product_id} изменена на {new_price} руб.")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_price] Ошибка при изменении цены: {e}", exc_info=True)
        await message.answer("Не удалось изменить цену.")


@router.message(RedactForm.category)
async def edit_product_set_category(message: Message, state: FSMContext):
    """
    Обработчик изменения категории товара.
    Если такой категории нет → создаёт её.
    """
    try:
        data = await state.get_data()
        product_id = data["product_id"]
        new_category_name = message.text.strip()
        category_id = db.get_category_id_by_name(new_category_name)
        if not category_id:
            db.add_category(new_category_name)
            category_id = db.get_category_id_by_name(new_category_name)
        db.update_product_category(product_id, category_id)
        await message.answer(f"🗂 Категория товара #{product_id} изменена на '{new_category_name}'")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_category] Ошибка при изменении категории: {e}", exc_info=True)
        await message.answer("Не удалось изменить категорию.")


@router.message(RedactForm.subcategory)
async def edit_product_set_subcategory(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_subcategory_name = message.text.strip()
    category_id = data.get("category_id") or db.get_product_by_id(product_id)[5]
    subcategory_id = db.get_subcategory_id_by_name(new_subcategory_name, category_id)
    if not subcategory_id:
        subcategory_id = db.add_subcategory(new_subcategory_name, category_id)
    db.update_product_subcategory(product_id, subcategory_id)
    await message.answer(f"🧩 Подкатегория товара #{product_id} изменена на '{new_subcategory_name}'")
    await show_edit_menu(message, state, product_id)


@router.message(RedactForm.photo, F.photo)
async def edit_product_set_photo(message: Message, state: FSMContext):
    """
    Обработчик изменения фото товара.
    """
    try:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        product_id = data["product_id"]
        db.update_product_photo(product_id, photo_id)
        await message.answer("✅ Фото успешно обновлено.")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_photo] Ошибка при обновлении фото: {e}", exc_info=True)
        await message.answer("⚠ Не удалось загрузить новое фото.")


@router.message(RedactForm.available)
async def edit_product_set_availability(message: Message, state: FSMContext):
    """
    Обработчик изменения статуса наличия товара (0 или 1).
    """
    try:
        data = await state.get_data()
        product_id = data["product_id"]
        is_available = message.text.strip()
        if is_available not in ("0", "1"):
            await message.answer("❌ Введите только 0 (нет в наличии) или 1 (в наличии).")
            return
        db.update_product_availability(product_id, int(is_available))
        status_text = "в наличии" if is_available == "1" else "не в наличии"
        await message.answer(f"📦 Статус товара #{product_id} изменён на '{status_text}'")
        await show_edit_menu(message, state, product_id)
    except Exception as e:
        logger.error(f"[edit_product_set_availability] Ошибка при изменении статуса: {e}", exc_info=True)
        await message.answer("⚠ Не удалось изменить статус наличия.")


async def show_edit_menu(message: Message, state: FSMContext, product_id: int):
    """
    Показывает карточку товара с inline-клавиатурой для редактирования.
    """
    try:
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
    except Exception as e:
        logger.error(f"[show_edit_menu] Ошибка при выводе меню редактирования: {e}", exc_info=True)
        await message.answer("Ошибка при загрузке карточки товара.")


@router.callback_query(F.data == "admin_add_category")
async def add_category_handler(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления новой категории.
    Запрашивает название категории.
    """
    if callback.from_user.id not in MANAGER_ID:
        await callback.message.answer("❌ Только менеджеры могут добавлять категории.")
        await callback.answer()
        return
    await callback.message.answer("Введите название категории:")
    await state.set_state(CategoryForm.name)
    await callback.answer()


@router.message(CategoryForm.name, F.text)
async def save_new_category(message: Message, state: FSMContext):
    """
    Сохраняет новую категорию в БД.
    Если категория уже существует → выводит сообщение об этом.
    """
    try:
        name = message.text.strip()
        success = db.add_category(name)
        if success:
            await message.answer(f"✅ Категория '{name}' добавлена.")
        else:
            await message.answer("❌ Такая категория уже существует.")
        await state.clear()
    except Exception as e:
        logger.error(f"[save_new_category] Ошибка при добавлении категории: {e}", exc_info=True)
        await message.answer("Произошла ошибка при добавлении категории.")
        await state.clear()


@router.callback_query(F.data == "admin_add_subcategory")
async def get_category_for_subcategory(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления подкатегории.
    Сначала запрашивает имя категории.
    """
    await callback.message.answer("Введите название категории, к которой хотите добавить подкатегорию:")
    await state.set_state(SubcategoryForm.category_name)
    await callback.answer()


@router.message(SubcategoryForm.category_name, F.text)
async def get_category_for_subcategory(message: Message, state: FSMContext):
    """
    Проверяет, существует ли категория.
    Если да → просит ввести название подкатегории.
    """
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
    """
    Добавляет подкатегорию в выбранную ранее категорию.
    """
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


@router.callback_query(F.data == "admin_list_products")
async def list_products_handler(callback: CallbackQuery):
    """
    Выводит список всех товаров с кнопками для просмотра.
    """
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
    """
    Отображает подробную информацию о товаре.
    Используется как менеджером, так и клиентом.
    """
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
    caption = (
        f"<b>{name}</b>\n\n{description}\n\n"
        f"💰 Цена: {price} руб."
        f"{category_info}\n\n"
        f"📦 Статус: {'✅ В наличии' if available else '❌ Нет в наличии'}\n"
        f"ID: {pid}"
    )
    if photo and isinstance(photo, str):
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb.edit_product_keyboard(pid)
        )
    else:
        await callback.message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=kb.edit_product_keyboard(pid)
        )
    await callback.answer()