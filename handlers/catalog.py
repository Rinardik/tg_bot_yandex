from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import keyboard as kb
import db
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    """
    Показывает список категорий.
    Если пользователь не зарегистрирован → запрещает доступ.
    """
    try:
        registered = await db.user_exists(callback.from_user.id)
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
    except Exception as e:
        logger.error(f"[show_catalog] Ошибка при выводе каталога: {e}", exc_info=True)


@router.callback_query(F.data.startswith("category_"))
async def show_subcategories(callback: CallbackQuery):
    """
    Обрабатывает выбор категории.
    Если есть подкатегории → показывает их.
    Если нет → показывает товары этой категории.
    """
    try:
        category_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        await callback.answer()
        return
    try:
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
    except Exception as e:
        logger.error(f"[show_subcategories] Ошибка при выводе подкатегорий: {e}", exc_info=True)


@router.callback_query(F.data.startswith("subcategory_"))
async def show_products_by_subcategory(callback: CallbackQuery):
    """
    Обрабатывает выбор подкатегории.
    Выводит товары или сообщение о том, что товаров нет.
    """
    try:
        subcategory_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
        await callback.answer()
        return
    try:
        products = db.get_products_by_subcategory(subcategory_id)
        if not products:
            await callback.message.answer("❌ В этой подкатегории пока нет товаров.")
            return
        keyboard = kb.get_products_keyboard(products)
        await callback.message.answer("🛍 Товары подкатегории:", reply_markup=kb.get_products_keyboard(products))
        await callback.answer()
    except Exception as e:
        logger.error(f"[show_products_by_subcategory] Ошибка при выводе товаров: {e}", exc_info=True)


@router.callback_query(F.data.startswith("product_"))
async def view_product(callback: CallbackQuery):
    """
    Отображает карточку товара.
    Если фото недоступно → выводит текстовое сообщение.
    """
    try:
        product_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный ID товара")
        await callback.answer()
        return
    try:
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
            f"ID: {pid}"
        )
        if photo and isinstance(photo, str):
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb.get_product_detail_keyboard(pid)
            )
        else:
            await callback.message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=kb.get_product_detail_keyboard(pid)
            )
        await callback.answer()
    except Exception as e:
        logger.error(f"[view_product] Ошибка при просмотре товара #{product_id}: {e}", exc_info=True)