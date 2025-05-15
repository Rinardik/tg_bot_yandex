from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup
import keyboard as kb
import db
from handlers.orders import notify_manager_about_order
import logging

logger = logging.getLogger(__name__)
router = Router()


async def show_basket_after_edit(callback: CallbackQuery):
    """
    Показывает содержимое корзины после добавления/удаления товаров.
    Формирует сообщение с фото (если есть), описанием, ценой и количеством.
    """
    user_id = callback.from_user.id
    basket = db.get_user_basket(user_id)
    if not basket:
        await callback.message.answer("🛒 Ваша корзина пуста.")
        return
    total_price = 0
    for product_id_str, quantity in basket.items():
        try:
            product_id = int(product_id_str)
        except ValueError:
            logger.error(f"[show_basket_after_edit] Неверный формат ID товара: {product_id_str}")
            continue
        product = db.get_product_by_id(product_id)
        if not product:
            logger.warning(f"[show_basket_after_edit] Товар #{product_id} не найден в БД")
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
                reply_markup=kb.get_basket_item_keyboard(pid)
            )
        else:
            await callback.message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=kb.get_basket_item_keyboard(pid)
            )
    await callback.message.answer(f"🧮 Общая сумма: <b>{total_price} руб.</b>", parse_mode="HTML")


@router.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: CallbackQuery):
    """
    Обработчик кнопки 'Добавить в корзину'.
    Увеличивает количество товара в корзине.
    """
    try:
        if callback.data.startswith("add_category_") or callback.data.startswith("add_subcategory_"):
            await callback.answer("⚠ Это не товар для корзины.")
            return
        parts = callback.data.split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            await callback.message.answer("❌ Неверный формат данных.")
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
    except Exception as e:
        logger.error(f"[add_to_cart] Ошибка при добавлении товара: {e}", exc_info=True)


@router.callback_query(F.data.startswith("remove_one_"))
async def remove_one_from_cart(callback: CallbackQuery):
    """
    Обработчик кнопки 'Убрать один'.
    Уменьшает количество товара в корзине на 1, а если количество становится 0 - удаляет товар.
    """
    try:
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[2].isdigit():
            await callback.message.answer("❌ Неверный формат данных.")
            return
        product_id = int(parts[2])
        user_id = callback.from_user.id
        basket = db.get_user_basket(user_id)
        key = str(product_id)
        if key in basket:
            if basket[key] > 1:
                basket[key] -= 1
                message_text = f"➖ Товар #{product_id} уменьшен до {basket[key]} шт."
            else:
                del basket[key]
                message_text = f"🗑 Товар #{product_id} удалён из корзины." 
            db.update_user_basket(user_id, basket)
            await callback.message.answer(message_text)
            await show_basket_after_edit(callback)
        else:
            await callback.answer("❌ Этот товар отсутствует в корзине.")
            
        await callback.answer()
    except Exception as e:
        logger.error(f"[remove_one_from_cart] Ошибка при уменьшении товара: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при обработке запроса.")

    
@router.callback_query(F.data == "view_basket")
async def view_basket(callback: CallbackQuery):
    """
    Отображает текущее состояние корзины пользователя.
    """
    try:
        await show_basket_after_edit(callback)
        await callback.answer()
    except Exception as e:
        logger.error(f"[view_basket] Ошибка при выводе корзины: {e}", exc_info=True)


@router.callback_query(F.data.startswith("remove_all_"))
async def remove_all_from_cart(callback: CallbackQuery):
    """
    Полностью удаляет товар из корзины по его ID.
    """
    try:
        product_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный формат данных.")
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


@router.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery):
    """
    Обработка оформления заказа.
    Сохраняет заказ в БД и очищает корзину.
    """
    try:
        user_id = callback.from_user.id
        basket = db.get_user_basket(user_id)
        if not basket:
            await callback.message.answer("🛒 Ваша корзина пуста.")
            return
        product_ids = list(map(int, basket.keys()))
        products = db.get_products_by_ids(product_ids)
        if not products:
            await callback.message.answer("❌ Товаров в базе данных не найдено.")
            return
        total_price = sum(db.get_product_by_id(pid)[4] * qty for pid, qty in basket.items())
        db.save_order(user_id, basket, total_price)
        db.update_user_basket(user_id, {})
        caption = (
            f"✅ Заказ оформлен!\n\n"
            f"🧮 Итого: {total_price} руб.\n"
            f"Спасибо за покупку!"
        )
        await callback.message.answer(caption)
        await notify_manager_about_order(
            bot=callback.bot,
            user_id=user_id,
            basket=basket,
            total_price=total_price
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"[checkout_handler] Ошибка при оформлении заказа: {e}", exc_info=True)